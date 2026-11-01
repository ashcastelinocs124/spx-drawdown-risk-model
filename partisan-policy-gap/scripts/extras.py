"""Remaining findings as data files for the dashboard.
Usage: python3 -I extras.py <data_dir>
Outputs (work/): recent_windows.csv, vix_tests.csv, vix_monthly_slim.csv,
control_detail.csv, correlations.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

D = Path(sys.argv[1]); W = D / "work"
a = pd.read_csv(W / "annual.csv", index_col="year")
a["t"] = a.index
ctrl = pd.read_csv(W / "control_by_year.csv", index_col="year")
LAB = {"sp_tr": "S&P 500 total return", "bond_tr": "10-yr Treasury return",
       "rvol": "S&P 500 realized volatility", "vix_avg": "VIX (annual average)"}


def hac(y, xs, d, lags=2):
    d = d[[y] + xs].dropna()
    return sm.OLS(d[y], sm.add_constant(d[xs])).fit(cov_type="HAC", cov_kwds={"maxlags": lags})


# 1. recent-decades windows: does the belief gap matter in later periods?
rows = []
for lo in [1921, 1950, 1980, 1990, 2000]:
    for o in LAB:
        st = max(lo, 1990) if o == "vix_avg" else lo
        hi = 2024 if o == "vix_avg" else 2022
        if o == "vix_avg" and lo < 1990:
            continue
        d = a.loc[st:hi]
        m1 = hac(o, ["gap_index"], d)
        m2 = hac(o, ["gap_index", "t"], d)
        rows.append({"window": f"{st}–{hi}", "start": st, "outcome": o, "outcome_label": LAB[o],
                     "n": int(m1.nobs), "corr": d[[o, "gap_index"]].dropna().corr().iloc[0, 1],
                     "beta": m1.params["gap_index"], "p": m1.pvalues["gap_index"],
                     "beta_trend": m2.params["gap_index"], "p_trend": m2.pvalues["gap_index"]})
pd.DataFrame(rows).round(6).to_csv(W / "recent_windows.csv", index=False)

# 2. monthly VIX tests
m = pd.read_csv(W / "vix_monthly.csv", index_col=0, parse_dates=True)
ev = pd.read_csv(W / "vix_congress.csv")
vt = []
for name, xs, note in [("Gap level", ["gap_index"], "Monthly VIX on the gap index"),
                       ("Gap level, trend removed", ["gap_index", "t"], "Adds a linear time trend"),
                       ("Voting gap only", ["vote_gap_z"], "Congress half of the index"),
                       ("Platform gap only", ["platform_z"], "Platform half of the index"),
                       ("Gap widening", ["gap_change"], "Change at each new Congress")]:
    r = hac("vix", xs, m, lags=24)
    vt.append({"test": name, "note": note, "n": int(r.nobs), "corr": m[["vix", xs[0]]].dropna().corr().iloc[0, 1],
               "beta": r.params[xs[0]], "p": r.pvalues[xs[0]]})
r = sm.OLS(ev.dvix, sm.add_constant(ev.gap_change)).fit(cov_type="HC1")
vt.append({"test": "New Congress seated", "note": "VIX Feb–Apr vs Oct–Dec before, vs gap change",
           "n": len(ev), "corr": ev.dvix.corr(ev.gap_change), "beta": r.params.gap_change, "p": r.pvalues.gap_change})
pd.DataFrame(vt).round(6).to_csv(W / "vix_tests.csv", index=False)
slim = m[["vix", "gap_index"]].copy()
slim.index = slim.index.strftime("%Y-%m")
slim.index.name = "month"
slim.round(4).to_csv(W / "vix_monthly_slim.csv")

# 3. split-government detail (6 combinations)
b = a.loc[1921:2022].join(ctrl[["president", "control_detail"]])
names = {("D", "Unified Democratic"): "Unified Democratic",
         ("R", "Unified Republican"): "Unified Republican",
         ("D", "Opposite party controls Congress"): "Dem president, Republican Congress",
         ("D", "Split Congress"): "Dem president, split Congress",
         ("R", "Opposite party controls Congress"): "Rep president, Democratic Congress",
         ("R", "Split Congress"): "Rep president, split Congress"}
cd = []
for (p, c), lab in names.items():
    s = b[(b.president == p) & (b.control_detail == c)]
    cd.append({"setup": lab, "government": "Unified" if c.startswith("Unified") else "Split",
               "sp_tr": s.sp_tr.mean(), "bond_tr": s.bond_tr.mean(), "n": int(s.sp_tr.count()),
               "years": ", ".join(str(y) for y in s.index)})
pd.DataFrame(cd).round(6).to_csv(W / "control_detail.csv", index=False)

# 4. headline correlations of the gap with markets
cr = []
for lo, hi, lab in [(1921, 2022, "1921–2022"), (1950, 2022, "1950–2022")]:
    d = a.loc[lo:hi]
    for o in ["sp_tr", "bond_tr", "rvol"]:
        cr.append({"period": lab, "outcome": o, "outcome_label": LAB[o], "corr": d.gap_index.corr(d[o])})
    cr.append({"period": lab, "outcome": "sp_next", "outcome_label": "S&P 500 return, next year",
               "corr": d.gap_index.corr(a.sp_tr.shift(-1).loc[lo:hi])})
d = a.loc[1990:2024]
cr.append({"period": "1990–2024", "outcome": "vix_avg", "outcome_label": LAB["vix_avg"], "corr": d.gap_index.corr(d.vix_avg)})
pd.DataFrame(cr).round(6).to_csv(W / "correlations.csv", index=False)

for f in ["recent_windows", "vix_tests", "control_detail", "correlations"]:
    print(f); print(pd.read_csv(W / f"{f}.csv").drop(columns=["years"], errors="ignore").round(3).to_string())
