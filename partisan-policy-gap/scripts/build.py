"""Partisan Policy Gap study: build a composite D-R gap index and test it against
S&P 500 total returns, 10-year Treasury returns and volatility.

Usage: python3 -I build.py <data_dir>
Inputs (under data_dir):
  raw_vv/HSall_parties.csv   Voteview HSall_parties.csv mirror (DW-NOMINATE party means)
  raw_mp/mpds2024a.csv      Manifesto Project MPDS2024a mirror
  raw_mkt/shiller.csv       Shiller monthly S&P 500 / dividend / long rate (datasets/s-and-p-500)
  raw_mkt/vix.csv           CBOE VIX daily (datasets/finance-vix)
Outputs: work/annual.csv, work/results.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

D = Path(sys.argv[1])
OUT = D / "work"
OUT.mkdir(exist_ok=True)

START, END_INDEX = 1921, 2024        # index coverage (1920 platforms -> 1921)
END_TR = 2022                        # last full year with Shiller dividends

# ---------------------------------------------------------------- 1. voting gap
vv = pd.read_csv(D / "raw_vv/HSall_parties.csv")
ch = vv[vv.chamber.isin(["House", "Senate"]) & vv.party_code.isin([100, 200])]
piv = ch.pivot_table(index=["congress", "chamber"], columns="party_code",
                     values="nominate_dim1_mean")
piv["gap"] = piv[200] - piv[100]
cong_gap = piv["gap"].groupby("congress").mean()          # avg of House & Senate
rows = []
for c, g in cong_gap.items():
    start = 1787 + 2 * c                                   # Congress 1 began 1789
    rows += [(start, g), (start + 1, g)]
vote = pd.Series(dict(rows), name="vote_gap")

# ------------------------------------------------------------- 2. platform gaps
mp = pd.read_csv(D / "raw_mp/mpds2024a.csv", low_memory=False)
us = mp[(mp.country == 61) & mp.party.isin([61320, 61620])].copy()
us["eyear"] = pd.to_datetime(us.edate, dayfirst=True).dt.year
TOPICS = {   # right-side categories vs left-side categories (CMP codebook)
    "econ": (["per414", "per505"], ["per404", "per409", "per413", "per504"]),
    "business": (["per401", "per402"], ["per403", "per412"]),
    "immig": (["per601", "per608"], ["per602", "per607"]),
    "foreign": (["per104", "per109"], ["per105", "per106", "per107"]),
}
if "--no-foreign" in sys.argv:
    TOPICS.pop("foreign")
    OUT = OUT / "three_topic"
    OUT.mkdir(exist_ok=True)
TOPIC_COLS = [t + "_gap" for t in TOPICS]
for t, (r, l) in TOPICS.items():   # Lowe et al. (2011) logit scale
    us[t] = np.log(us[r].sum(axis=1) + 0.5) - np.log(us[l].sum(axis=1) + 0.5)
plat = us.pivot_table(index="eyear", columns="party", values=list(TOPICS))
plat_gap = pd.DataFrame({f"{t}_gap": plat[(t, 61620)] - plat[(t, 61320)]
                         for t in TOPICS})
yrs = []
for e, row in plat_gap.iterrows():          # platform governs the next 4 years
    for y in range(e + 1, e + 5):
        yrs.append(row.rename(y))
plat_annual = pd.DataFrame(yrs)

# ------------------------------------------------------------- 3. composite
idx = pd.concat([vote, plat_annual], axis=1).loc[START:END_INDEX]
z = (idx - idx.mean()) / idx.std()
z["platform_z"] = z[TOPIC_COLS].mean(axis=1)
idx["gap_index"] = 0.5 * z["vote_gap"] + 0.5 * z["platform_z"]
idx["gap_index"] = (idx.gap_index - idx.gap_index.mean()) / idx.gap_index.std()
for c in ["vote_gap"] + TOPIC_COLS:
    idx[c + "_z"] = z[c]
idx["platform_z"] = z["platform_z"]
# real-time version: at the start of year t only the previous Congress's votes are known
vz = z["vote_gap"]
rt = 0.5 * vz.shift(2) + 0.5 * z["platform_z"]
idx["gap_rt"] = (rt - rt.mean()) / rt.std()

# ------------------------------------------------------------- 4. markets
sh = pd.read_csv(D / "raw_mkt/shiller.csv", parse_dates=["Date"]).set_index("Date")
sh = sh.loc[:"2023-06-01"]
p, dv, y = sh["SP500"], sh["Dividend"], sh["Long Interest Rate"] / 100
tr_m = (p + dv / 12) / p.shift(1) - 1
yp = y.shift(1)                      # 10y par bond, held one month
n = 10 * 12 - 1                      # remaining monthly periods
c = yp / 12
price = c * (1 - (1 + y / 12) ** -n) / (y / 12) + (1 + y / 12) ** -n
bond_m = c + price - 1

def ann(r):
    return (1 + r).groupby(r.index.year).prod() - 1

mkt = pd.DataFrame({
    "sp_tr": ann(tr_m),
    "bond_tr": ann(bond_m),
    "rvol": tr_m.groupby(tr_m.index.year).std() * np.sqrt(12),
    "y10_end": y.groupby(y.index.year).last() * 100,
    "y10_start": y.groupby(y.index.year).first() * 100,
    "infl": sh["Consumer Price Index"].groupby(sh.index.year).last().pct_change(),
})
vix = pd.read_csv(D / "raw_mkt/vix.csv", parse_dates=["DATE"]).set_index("DATE")
vix_y = vix.CLOSE.groupby(vix.index.year).mean()
mkt = mkt.reindex(mkt.index.union(vix_y.index))
mkt["vix_avg"] = vix_y
annual = idx.join(mkt, how="left")
annual.loc[annual.index > END_TR, ["sp_tr", "bond_tr", "rvol"]] = np.nan
annual.loc[annual.index > 2023, "y10_end"] = np.nan

# change in the gap at each new Congress (odd year t vs t-2), held for both years
chg = {}
for t in range(START + 2, END_INDEX + 1, 2):
    d = annual.gap_index.get(t, np.nan) - annual.gap_index.get(t - 2, np.nan)
    chg[t] = d
    chg[t + 1] = d
annual["gap_change"] = pd.Series(chg)
chg = {}
for t in range(START + 2, END_INDEX + 1, 2):
    d = annual.gap_rt.get(t, np.nan) - annual.gap_rt.get(t - 2, np.nan)
    chg[t] = d
    chg[t + 1] = d
annual["gap_change_rt"] = pd.Series(chg)
annual.index.name = "year"
annual.to_csv(OUT / "annual.csv")

# ------------------------------------------------------------- 6. tests
def nw(yname, xname, df, lags=2):
    d = df[[yname, xname]].dropna()
    m = sm.OLS(d[yname], sm.add_constant(d[xname])).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags})
    return {"beta": m.params[xname], "t": m.tvalues[xname],
            "p": m.pvalues[xname], "n": int(m.nobs), "r2": m.rsquared}

res = {"tercile": {}, "reg": {}, "meta": {}}
a = annual.copy()
a["tercile"] = pd.qcut(a.gap_index, 3, labels=["Narrow", "Middle", "Wide"])
a["chg_dir"] = np.where(a.gap_change > 0, "Widening", "Narrowing")
a.loc[a.gap_change.isna(), "chg_dir"] = None
v = a.loc[1990:2024].copy()            # VIX era has its own terciles
v["tercile"] = pd.qcut(v.gap_index, 3, labels=["Narrow", "Middle", "Wide"])
res["meta"]["vix_cuts"] = [float(x) for x in v.gap_index.quantile([1/3, 2/3])]
for out in ["sp_tr", "bond_tr", "rvol", "vix_avg"]:
    src = v if out == "vix_avg" else a
    g = src.groupby("tercile", observed=True)[out]
    res["tercile"][out] = {k: {"mean": v.mean(), "median": v.median(),
                              "n": int(v.count()),
                              "pos": float((v > 0).mean()) if out in ("sp_tr", "bond_tr") else None}
                           for k, v in g}
    g2 = a.groupby("chg_dir")[out]
    res["tercile"][out + "_chg"] = {k: {"mean": v.mean(), "n": int(v.count())} for k, v in g2}
    res["reg"][out] = {
        "level_full": nw(out, "gap_index", a),
        "level_post1950": nw(out, "gap_index", a.loc[1950:]),
        "change_full": nw(out, "gap_change", a),
        "level_ex_depression": nw(out, "gap_index", a.drop(range(1929, 1941), errors="ignore")),
        "change_post1950": nw(out, "gap_change", a.loc[1950:]),
    }
    a[out + "_next"] = a[out].shift(-1)
    res["reg"][out]["level_next_year"] = nw(out + "_next", "gap_index", a)
# components vs equity / bonds
for comp in ["vote_gap_z"] + [c + "_z" for c in TOPIC_COLS]:
    res["reg"]["comp_" + comp] = {o: nw(o, comp, a) for o in ["sp_tr", "bond_tr", "rvol"]}
# ------------------------------------------------------------- 7. is it useful?
a["infl_prev"] = a.infl.shift(1)
val = {}
rng = np.random.default_rng(7)
for out in ["sp_tr", "bond_tr", "rvol", "vix_avg"]:
    a[out + "_lag"] = a[out].shift(1)
    ctrl = [out + "_lag", "y10_start", "infl_prev"] if out != "vix_avg" else [out + "_lag", "y10_start"]
    lo = 1990 if out == "vix_avg" else 1923
    d = a.loc[lo:].dropna(subset=[out] + ctrl + ["gap_change", "gap_change_rt"])
    base = sm.OLS(d[out], sm.add_constant(d[ctrl])).fit()
    rec = {"n": int(len(d)), "r2_base": base.rsquared, "adjr2_base": base.rsquared_adj}
    for key, xv in [("chg", "gap_change"), ("chg_rt", "gap_change_rt")]:
        full = sm.OLS(d[out], sm.add_constant(d[ctrl + [xv]])).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
        rec[key] = {"beta": full.params[xv], "t": full.tvalues[xv], "p": full.pvalues[xv],
                    "r2": full.rsquared, "adjr2": full.rsquared_adj}
    # out-of-sample: expanding window, real-time change only (no look-ahead)
    first = 2000 if out == "vix_avg" else 1950
    e_b, e_a, e_m = [], [], []
    for t in d.index[d.index >= first]:
        tr_ = d.loc[:t - 1]
        Xb = sm.add_constant(tr_[ctrl]); Xa = sm.add_constant(tr_[ctrl + ["gap_change_rt"]])
        mb = sm.OLS(tr_[out], Xb).fit(); ma = sm.OLS(tr_[out], Xa).fit()
        xt = d.loc[[t]]
        pb = float(mb.predict(sm.add_constant(xt[ctrl], has_constant="add"))[t])
        pa = float(ma.predict(sm.add_constant(xt[ctrl + ["gap_change_rt"]], has_constant="add"))[t])
        e_b.append((xt[out][t] - pb) ** 2); e_a.append((xt[out][t] - pa) ** 2)
        e_m.append((xt[out][t] - tr_[out].mean()) ** 2)
    rec["oos"] = {"from": first, "n": len(e_b), "r2_vs_controls": 1 - sum(e_a) / sum(e_b),
                  "r2_controls_vs_mean": 1 - sum(e_b) / sum(e_m)}
    # permutation: shuffle Congress-level changes (2-year blocks), keep outcomes fixed
    dd = a.loc[lo:].dropna(subset=[out, "gap_change"])
    obs = abs(nw(out, "gap_change", dd)["t"])
    blocks = sorted(set((yy - 1) // 2 for yy in dd.index))
    bchg = {b: dd.gap_change[[yy for yy in dd.index if (yy - 1) // 2 == b]].iloc[0] for b in blocks}
    cnt = 0
    for _ in range(2000):
        perm = dict(zip(blocks, rng.permutation([bchg[b] for b in blocks])))
        dp = dd.copy(); dp["gap_change"] = [perm[(yy - 1) // 2] for yy in dd.index]
        cnt += abs(nw(out, "gap_change", dp)["t"]) >= obs
    rec["perm_p"] = (cnt + 1) / 2001
    val[out] = rec
res["value"] = val
res["meta"].update({"start": START, "end_index": END_INDEX, "end_tr": END_TR,
               "tercile_cuts": [float(x) for x in a.gap_index.quantile([1/3, 2/3])]})
json.dump(res, open(OUT / "results.json", "w"), indent=1, default=float)
print(annual.round(3).to_string())
print(json.dumps(res, indent=1, default=lambda x: round(float(x), 4)))
