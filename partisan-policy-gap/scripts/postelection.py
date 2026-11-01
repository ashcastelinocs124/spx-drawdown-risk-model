"""Post-election event study: market moves 1, 3 and 6 months after each November election,
compared by the partisan gap the election produced.

Gap for election in year E = gap index for year E+1 (new platforms + incoming Congress).
Gap change = gap(E+1) - gap(E-1), i.e. did this election widen the gap.
Usage: python3 -I postelection.py <data_dir>
"""
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

D = Path(sys.argv[1])
W = D / "work"
a = pd.read_csv(W / "annual.csv", index_col="year")

sh = pd.read_csv(D / "raw_mkt/shiller.csv", parse_dates=["Date"]).set_index("Date").loc[:"2023-06-01"]
p, dv, y = sh["SP500"], sh["Dividend"], sh["Long Interest Rate"] / 100
tr_m = (p + dv / 12) / p.shift(1) - 1
yp, n = y.shift(1), 119
price = (yp / 12) * (1 - (1 + y / 12) ** -n) / (y / 12) + (1 + y / 12) ** -n
bond_m = yp / 12 + price - 1

vix = pd.read_csv(D / "raw_mkt/vix.csv", parse_dates=["DATE"]).set_index("DATE").CLOSE


def election_day(year):
    d = dt.date(year, 11, 2)                       # first Tuesday after first Monday
    while d.weekday() != 1:
        d += dt.timedelta(days=1)
    return pd.Timestamp(d)


def window(r, year, months):
    # from October's level (pre-election) through month Oct+months
    idx = pd.date_range(f"{year}-11-01", periods=months, freq="MS")
    if idx[-1] not in r.index or r.loc[idx].isna().any():
        return np.nan
    return float((1 + r.loc[idx]).prod() - 1)


rows = []
for E in range(1920, 2023, 2):
    if E + 1 not in a.index or E - 1 not in a.index and E != 1920:
        pass
    gap = a.gap_index.get(E + 1, np.nan)
    prev = a.gap_index.get(E - 1, np.nan)
    rec = {"election": E, "type": "Presidential" if E % 4 == 0 else "Midterm",
           "gap_after": gap, "gap_change": gap - prev if not np.isnan(prev) else np.nan}
    for m in (1, 3, 6):
        rec[f"sp_{m}m"] = window(tr_m, E, m)
        rec[f"bond_{m}m"] = window(bond_m, E, m)
    if E >= 1990:
        ed = election_day(E)
        before = vix.loc[:ed - pd.Timedelta(days=1)].iloc[-1]
        after = vix.loc[ed + pd.Timedelta(days=60):].iloc[0]
        rec["vix_chg_60d"] = float(after - before)
    rows.append(rec)
ev = pd.DataFrame(rows).set_index("election")
med = ev.gap_after.median()
ev["beliefs"] = np.where(ev.gap_after > med, "Far apart", "Close together")
ev["far"] = (ev.beliefs == "Far apart").astype(float)
ev["widened"] = np.where(ev.gap_change > 0, "Widened", "Narrowed")
ev.loc[ev.gap_change.isna(), "widened"] = None
ev["t"] = ev.index
ev.round(6).to_csv(W / "post_election.csv")

OUTS = [f"{k}_{m}m" for m in (1, 3, 6) for k in ("sp", "bond")] + ["vix_chg_60d"]
LAB = {"sp": "S&P 500", "bond": "10-yr Treasury"}


def ols(yv, xs, d):
    d = d[[yv] + xs].dropna()
    return sm.OLS(d[yv], sm.add_constant(d[xs])).fit(cov_type="HC1")


tests, cells = [], []
for o in OUTS:
    lab = "VIX change, 60 days" if o == "vix_chg_60d" else f"{LAB[o.split('_')[0]]}, {o.split('_')[1][:-1]} mo"
    for sub, d in [("All elections", ev), ("Presidential", ev[ev.type == "Presidential"]),
                   ("Since 1980", ev.loc[1980:])]:
        for b in ["Close together", "Far apart"]:
            s = d[d.beliefs == b][o].dropna()
            cells.append({"outcome": o, "outcome_label": lab, "sample": sub, "beliefs": b,
                          "mean": s.mean(), "n": int(s.count())})
        dd = d.dropna(subset=[o])
        if dd.far.nunique() < 2 or len(dd) < 6:
            continue
        m1 = ols(o, ["far"], dd)
        m2 = ols(o, ["gap_after"], dd)
        m3 = ols(o, ["gap_after", "t"], dd)
        m4 = ols(o, ["gap_change"], dd)
        tests.append({"outcome": o, "outcome_label": lab, "sample": sub, "n": int(m1.nobs),
                      "far_diff": m1.params["far"], "far_p": m1.pvalues["far"],
                      "gap_beta": m2.params["gap_after"], "gap_p": m2.pvalues["gap_after"],
                      "gap_trend_p": m3.pvalues["gap_after"],
                      "chg_beta": m4.params["gap_change"], "chg_p": m4.pvalues["gap_change"]})
tests, cells = pd.DataFrame(tests), pd.DataFrame(cells)
tests.round(6).to_csv(W / "post_election_tests.csv", index=False)
cells.round(6).to_csv(W / "post_election_cells.csv", index=False)
pd.set_option("display.width", 250)
print("median gap", round(med, 3), "elections", len(ev))
print(cells[cells["sample"] == "All elections"].round(4).to_string())
print(tests.round(3).to_string())
print(ev[["type", "gap_after", "beliefs", "sp_3m", "bond_3m", "vix_chg_60d"]].round(3).to_string())
