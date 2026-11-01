"""Party control by year x Partisan Policy Gap: compare market outcomes.

Control table: majorities per Congress from Wikipedia "Party divisions of United States
Congresses" (fetched 2026-10-31), cross-checked with Voteview membership counts.
Usage: python3 -I control.py <data_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

D = Path(sys.argv[1]) / "work"

# congress: (president, senate, house). 72nd House: Democrats organized it (Speaker Garner);
# 107th Senate: Democratic from May 2001 (Jeffords switch), so D for the Congress;
# 117th: Biden from Jan 20 2021 and Democratic Senate via VP tie-break.
CTRL = {
    67: "RRR", 68: "RRR", 69: "RRR", 70: "RRR", 71: "RRR", 72: "RRD",
    73: "DDD", 74: "DDD", 75: "DDD", 76: "DDD", 77: "DDD", 78: "DDD", 79: "DDD",
    80: "DRR", 81: "DDD", 82: "DDD", 83: "RRR", 84: "RDD", 85: "RDD", 86: "RDD",
    87: "DDD", 88: "DDD", 89: "DDD", 90: "DDD", 91: "RDD", 92: "RDD", 93: "RDD",
    94: "RDD", 95: "DDD", 96: "DDD", 97: "RRD", 98: "RRD", 99: "RRD", 100: "RDD",
    101: "RDD", 102: "RDD", 103: "DDD", 104: "DRR", 105: "DRR", 106: "DRR",
    107: "RDR", 108: "RRR", 109: "RRR", 110: "RDD", 111: "DDD", 112: "DDR",
    113: "DDR", 114: "DRR", 115: "RRR", 116: "RRD", 117: "DDD", 118: "DDR",
}
rows = []
for c, (p, s, h) in CTRL.items():
    for y in (1787 + 2 * c, 1788 + 2 * c):
        unified = p == s == h
        if unified:
            cat = "Unified " + ("Democratic" if p == "D" else "Republican")
        elif s == h:
            cat = "Opposite party controls Congress"
        else:
            cat = "Split Congress"
        rows.append({"year": y, "congress": c, "president": p, "senate": s, "house": h,
                     "government": "Unified" if unified else "Divided", "control_detail": cat})
ctrl = pd.DataFrame(rows).set_index("year")

a = pd.read_csv(D / "annual.csv", index_col="year").join(ctrl, how="left")
a = a.loc[1921:2024]
med = a.loc[:2022, "gap_index"].median()
a["beliefs"] = np.where(a.gap_index > med, "Far apart", "Close together")
a["divided"] = (a.government == "Divided").astype(float)
a["far"] = (a.beliefs == "Far apart").astype(float)
a["div_x_far"] = a.divided * a.far
a["div_x_gap"] = a.divided * a.gap_index

OUTS = {"sp_tr": "S&P 500 total return", "bond_tr": "10-yr Treasury return",
        "rvol": "S&P 500 realized volatility", "vix_avg": "VIX (annual average)"}


def fit(y, xs, d):
    d = d[[y] + xs].dropna()
    return sm.OLS(d[y], sm.add_constant(d[xs])).fit(cov_type="HAC", cov_kwds={"maxlags": 2})


cells, tests = [], []
for o, lab in OUTS.items():
    d = a.dropna(subset=[o])
    for g in ["Unified", "Divided"]:
        for b in ["Close together", "Far apart", "All"]:
            s = d[(d.government == g) & ((d.beliefs == b) | (b == "All"))][o]
            cells.append({"outcome": o, "outcome_label": lab, "government": g, "beliefs": b,
                          "mean": s.mean(), "median": s.median(), "n": int(s.count()),
                          "years": ", ".join(str(x) for x in s.index) if b != "All" else ""})
    for b in ["Close together", "Far apart"]:
        s = d[d.beliefs == b][o]
        cells.append({"outcome": o, "outcome_label": lab, "government": "All", "beliefs": b,
                      "mean": s.mean(), "median": s.median(), "n": int(s.count()), "years": ""})
    m1 = fit(o, ["divided"], d)
    m2 = fit(o, ["divided", "far", "div_x_far"], d)
    m3 = fit(o, ["divided", "gap_index", "div_x_gap"], d)
    for name, m, x in [("Divided vs unified", m1, "divided"),
                       ("Far apart vs close (under unified)", m2, "far"),
                       ("Extra effect of far apart under divided", m2, "div_x_far"),
                       ("Gap slope under unified (per 1 SD)", m3, "gap_index"),
                       ("Extra gap slope under divided (per 1 SD)", m3, "div_x_gap")]:
        tests.append({"outcome": o, "outcome_label": lab, "test": name, "beta": m.params[x],
                      "p": m.pvalues[x], "n": int(m.nobs)})

cells = pd.DataFrame(cells)
tests = pd.DataFrame(tests)
cells.round(6).to_csv(D / "gap_control_cells.csv", index=False)
tests.round(6).to_csv(D / "gap_control_tests.csv", index=False)
a[["congress", "president", "senate", "house", "government", "control_detail", "beliefs"]].to_csv(D / "control_by_year.csv")
json.dump({"median_gap": med}, open(D / "control_meta.json", "w"))
pd.set_option("display.width", 220)
print("median gap", round(med, 3))
print(cells.drop(columns="years").round(3).to_string())
print(tests.round(3).to_string())
print(cells[(cells.outcome == "sp_tr") & (cells.beliefs != "All") & (cells.government != "All")][["government", "beliefs", "years"]].to_string())
