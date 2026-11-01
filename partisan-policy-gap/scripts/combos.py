"""Market returns by every president/House/Senate party combination, 1921-2022.
Usage: python3 -I combos.py <data_dir>
"""
import json, sys
import pandas as pd, statsmodels.api as sm
W = sys.argv[1] + "/work"
a = pd.read_csv(f"{W}/annual.csv", index_col="year").join(pd.read_csv(f"{W}/control_by_year.csv", index_col="year")[["president", "house", "senate"]]).loc[1921:2022]
P = {"D": "Dem", "R": "Rep"}
a["combo"] = a.apply(lambda r: f"{P[r.president]} president, {P[r.house]} House, {P[r.senate]} Senate", axis=1)
rows = []
for c, d in a.groupby("combo"):
    x = (a.combo == c).astype(float)
    ms = sm.OLS(a.sp_tr, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    mb = sm.OLS(a.bond_tr, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    r = d.iloc[0]
    rows.append({"combo": c, "president": r.president, "house": r.house, "senate": r.senate,
                 "government": "Unified" if r.president == r.house == r.senate else "Split",
                 "sp_tr": d.sp_tr.mean(), "bond_tr": d.bond_tr.mean(), "n": len(d), "sp_up": (d.sp_tr > 0).mean(),
                 "sp_p": ms.pvalues.combo if hasattr(ms.pvalues, "combo") else ms.pvalues.iloc[1],
                 "bond_p": mb.pvalues.iloc[1], "years": ", ".join(map(str, d.index))})
rows.append({"combo": "All years (average)", "president": "", "house": "", "senate": "", "government": "All",
             "sp_tr": a.sp_tr.mean(), "bond_tr": a.bond_tr.mean(), "n": len(a), "sp_up": (a.sp_tr > 0).mean(),
             "sp_p": None, "bond_p": None, "years": "1921–2022"})
df = pd.DataFrame(rows).sort_values("sp_tr", ascending=False)
df.round(6).to_csv(f"{W}/combo_returns.csv", index=False)
df = df.astype(object).where(df.notna(), None)
json.dump([{k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()} for r in df.to_dict("records")], open(f"{W}/combo_returns.json", "w"))
print(pd.read_csv(f"{W}/combo_returns.csv").drop(columns="years").round(3).to_string())
