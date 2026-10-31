#!/usr/bin/env python3
"""
SPX 5% Drawdown Risk Model (ARC Capital)

Predicts P(the S&P 500 closes >= DROP below today's close on any of the next 20 trading days).
    Y_t = 1  if  min(Close[t+1 .. t+20]) <= (1 - DROP) * Close[t]   else 0

Final model: Random forest on 7 technical variables, expanding window from 1990, refit yearly.
Benchmarks:  Linear probability model (OLS, clipped to 0-1) and logistic regression.

Commands
  python3 spx_risk_model.py fetch                 # download data into ./data
  python3 spx_risk_model.py evaluate [--drop 0.05] # fixed-split + walk-forward tests -> results/evaluation.json
  python3 spx_risk_model.py score    [--drop 0.05] # fit on all history, score the latest day(s) -> results/latest_score.json

Data (all public, all point-in-time):
  S&P 500 daily close 1927-2019-12-23 : github.com/fja05680/dow-sp500-100-years (SP500.csv)
  SPY daily close (extends the index)  : github.com/Johnbrick123/sp500-data release prices.parquet (Yahoo)
  CBOE VIX daily                        : github.com/datasets/finance-vix (vix-daily.csv)
  Optional overrides (fresher data): put data/spx_override.csv (Date,Close) and/or
  data/vix_override.csv (Date,Close); they are spliced onto the end of the series.
"""
import argparse, json, os, sys, urllib.request, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
DATA, RESULTS = ROOT / "data", ROOT / "results"
H = 20
FEATURES = ["vix", "vix_chg_5d", "vrp", "ret_20d", "dist_ma200", "drawdown_252d", "rsi_14"]
FEATURE_DESC = {
    "vix": "CBOE VIX close",
    "vix_chg_5d": "% change in VIX over 5 trading days",
    "vrp": "VIX minus 20-day realised vol of the S&P 500 (annualised, %)",
    "ret_20d": "S&P 500 % change over 20 trading days",
    "dist_ma200": "Close / 200-day moving average - 1",
    "drawdown_252d": "Close / highest close of last 252 days - 1",
    "rsi_14": "14-day RSI (Wilder smoothing)",
}
URLS = {
    "SP500.csv": "https://raw.githubusercontent.com/fja05680/dow-sp500-100-years/master/SP500.csv",
    "vix-daily.csv": "https://raw.githubusercontent.com/datasets/finance-vix/main/data/vix-daily.csv",
    "prices.parquet": "https://github.com/Johnbrick123/sp500-data/releases/download/data/prices.parquet",
}


# ----------------------------------------------------------------------------- data
def fetch(force=False):
    DATA.mkdir(exist_ok=True)
    for name, url in URLS.items():
        p = DATA / name
        if p.exists() and not force:
            print(f"have {name}"); continue
        print(f"downloading {name} ...", flush=True)
        urllib.request.urlretrieve(url, p)
    spy = DATA / "spy_daily.csv"
    if not spy.exists() or force:
        import pyarrow.parquet as pq
        t = pq.read_table(DATA / "prices.parquet", filters=[("ticker", "==", "SPY")]).to_pandas()
        t.sort_values("date")[["date", "close"]].to_csv(spy, index=False)
        print("wrote spy_daily.csv")
    print("data ready in", DATA)


def _splice(base: pd.Series, override_path: Path) -> pd.Series:
    if not override_path.exists():
        return base
    raw = pd.read_csv(override_path, parse_dates=[0])
    o = raw.set_index(raw.columns[0]).iloc[:, 0].sort_index().astype(float)
    new = o[o.index > base.index[-1]]
    if len(new) and base.index[-1] in o.index:          # chain by returns so levels stay consistent
        new = base.iloc[-1] * (o / o.loc[base.index[-1]])[o.index > base.index[-1]]
    return pd.concat([base, new])


def load_series():
    spx = pd.read_csv(DATA / "SP500.csv", parse_dates=["Date"]).set_index("Date")["Close"].astype(float)
    spy = pd.read_csv(DATA / "spy_daily.csv", parse_dates=["date"]).set_index("date")["close"].astype(float)
    r = spy.pct_change()
    # unadjusted SPY close tracks the price index (SPX/SPY ~ 10.0 throughout 1995-2019)
    ext = spx.iloc[-1] * (1 + r[r.index > spx.index[-1]]).cumprod()
    close = _splice(pd.concat([spx, ext]), DATA / "spx_override.csv")
    vix = pd.read_csv(DATA / "vix-daily.csv", parse_dates=["DATE"]).set_index("DATE")["CLOSE"].astype(float)
    vix = _splice(vix, DATA / "vix_override.csv")
    return close.sort_index(), vix.sort_index()


def build(drop: float):
    close, vix = load_series()
    fwd = pd.concat([close.shift(-k) for k in range(1, H + 1)], axis=1).min(axis=1)
    y = (fwd <= (1 - drop) * close).astype(float)
    y.iloc[-H:] = np.nan                                   # no complete forward window yet
    df = pd.DataFrame({"close": close}).join(vix.rename("vix"), how="inner")
    df = df[df.index >= "1990-01-01"]
    c = df["close"]; lr = np.log(c).diff()
    df["vix_chg_5d"] = df["vix"].pct_change(5)
    df["vrp"] = df["vix"] - lr.rolling(20).std() * np.sqrt(252) * 100
    df["ret_20d"] = c.pct_change(20)
    df["dist_ma200"] = c / c.rolling(200).mean() - 1
    df["drawdown_252d"] = c / c.rolling(252).max() - 1
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / 14).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / 14).mean()
    df["rsi_14"] = 100 - 100 / (1 + up / dn)
    df["Y"] = y.reindex(df.index)
    return df.dropna(subset=FEATURES)


# ----------------------------------------------------------------------------- models
class Standardised:
    """Fit-time standardisation (train mean/sd only) + model; predict_proba returns P(Y=1)."""
    def __init__(self, kind):
        self.kind = kind

    def fit(self, X, y):
        if self.kind == "Random forest":
            from sklearn.ensemble import RandomForestClassifier
            self.m = RandomForestClassifier(n_estimators=400, max_depth=5, min_samples_leaf=200,
                                            n_jobs=-1, random_state=0).fit(X.values, y.values)
            return self
        import statsmodels.api as sm
        self.mu, self.sd = X.mean(), X.std()
        Z = sm.add_constant((X - self.mu) / self.sd)
        self.m = (sm.Logit(y, Z).fit(disp=0) if self.kind == "Logistic" else sm.OLS(y, Z).fit())
        return self

    def proba(self, X):
        if self.kind == "Random forest":
            return self.m.predict_proba(X.values)[:, 1]
        import statsmodels.api as sm
        p = np.asarray(self.m.predict(sm.add_constant((X - self.mu) / self.sd, has_constant="add")))
        return np.clip(p, 0, 1)


MODELS = ["Random forest", "Linear (LPM)", "Logistic"]


# ----------------------------------------------------------------------------- evaluate
def evaluate(drop: float):
    from sklearn.metrics import roc_auc_score, brier_score_loss
    df = build(drop); lab = df.dropna(subset=["Y"])
    out = {"drop": drop, "horizon_days": H, "features": FEATURES,
           "sample": [str(lab.index[0].date()), str(lab.index[-1].date()), len(lab)],
           "base_rate": float(lab.Y.mean()), "models": {}}
    splits = {"test_2010_2019": ("2009-12-31", "2010-02-01", "2019-12-31"),
              "test_2020_on": ("2019-11-30", "2020-01-01", None)}
    for kind in MODELS:
        r = {}
        for name, (tr_end, te_start, te_end) in splits.items():
            tr = lab.loc[:tr_end]; te = lab.loc[te_start:te_end]
            p = Standardised(kind).fit(tr[FEATURES], tr.Y).proba(te[FEATURES])
            r[name] = {"auc": roc_auc_score(te.Y, p),
                       "brier_skill": 1 - brier_score_loss(te.Y, p) / brier_score_loss(te.Y, np.full(len(te), tr.Y.mean())),
                       "period": [str(te.index[0].date()), str(te.index[-1].date())]}
        ps, ys, refs, years = [], [], [], {}
        for yr in range(2000, lab.index[-1].year + 1):
            tr = lab.loc[:f"{yr-1}-11-30"]; te = lab.loc[f"{yr}-01-01":f"{yr}-12-31"]
            if len(te) == 0: continue
            p = pd.Series(Standardised(kind).fit(tr[FEATURES], tr.Y).proba(te[FEATURES]), te.index)
            ps.append(p); ys.append(te.Y); refs.append(pd.Series(tr.Y.mean(), te.index))
            years[yr] = roc_auc_score(te.Y, p) if 0 < te.Y.sum() < len(te) else None
        P, Y, R = pd.concat(ps), pd.concat(ys), pd.concat(refs)
        r["walk_forward"] = {"auc": roc_auc_score(Y, P), "brier_skill": 1 - brier_score_loss(Y, P) / brier_score_loss(Y, R),
                             "period": [str(P.index[0].date()), str(P.index[-1].date())], "auc_by_year": years}
        out["models"][kind] = r
        print(f"{kind:14s} 2010-19 AUC {r['test_2010_2019']['auc']:.3f} | 2020+ AUC {r['test_2020_on']['auc']:.3f} "
              f"| walk-forward AUC {r['walk_forward']['auc']:.3f}, Brier skill {r['walk_forward']['brier_skill']:+.3f}", flush=True)
    RESULTS.mkdir(exist_ok=True)
    json.dump(out, open(RESULTS / f"evaluation_{drop}.json", "w"), indent=1, default=float)
    print("saved", RESULTS / f"evaluation_{drop}.json")
    return out


# ----------------------------------------------------------------------------- score
def score(drop: float, last_n: int = 10):
    df = build(drop); lab = df.dropna(subset=["Y"])
    res = {"drop": drop, "trained_through": str(lab.index[-1].date()), "data_through": str(df.index[-1].date()),
           "base_rate": float(lab.Y.mean())}
    rf = Standardised("Random forest").fit(lab[FEATURES], lab.Y)
    lpm = Standardised("Linear (LPM)").fit(lab[FEATURES], lab.Y)
    hist = pd.Series(rf.proba(lab[FEATURES]), lab.index)
    recent = df.iloc[-last_n:]
    p_rf, p_lpm = rf.proba(recent[FEATURES]), lpm.proba(recent[FEATURES])
    res["recent"] = [{"date": str(i.date()), "p_rf": float(a), "p_lpm": float(b),
                      "rf_percentile_vs_history": float((hist < a).mean()),
                      **{k: float(recent.loc[i, k]) for k in FEATURES}}
                     for i, a, b in zip(recent.index, p_rf, p_lpm)]
    lat = res["recent"][-1]
    res["regime"] = ("HIGH" if lat["rf_percentile_vs_history"] >= 0.8 else
                     "ELEVATED" if lat["rf_percentile_vs_history"] >= 0.6 else "NORMAL/LOW")
    res["feature_importance"] = dict(sorted(zip(FEATURES, map(float, rf.m.feature_importances_)), key=lambda x: -x[1]))
    RESULTS.mkdir(exist_ok=True)
    json.dump(res, open(RESULTS / f"latest_score_{drop}.json", "w"), indent=1)
    print(f"Latest {lat['date']}: P(>= {drop:.0%} fall in {H}d) RF {lat['p_rf']:.1%} | LPM {lat['p_lpm']:.1%} | "
          f"base rate {res['base_rate']:.1%} | RF percentile {lat['rf_percentile_vs_history']:.0%} -> {res['regime']}")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "evaluate", "score"])
    ap.add_argument("--drop", type=float, default=0.05)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.cmd == "fetch": fetch(a.force)
    elif a.cmd == "evaluate": evaluate(a.drop)
    else: score(a.drop)
