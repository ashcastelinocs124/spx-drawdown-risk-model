"""Export dashboard files from work/annual.csv and work/results.json. Usage: python3 -I export.py <data_dir>"""
import json, sys
from pathlib import Path
import pandas as pd
D = Path(sys.argv[1]) / "work"
a = pd.read_csv(D / "annual.csv")
cols = ["year", "vote_gap", "econ_gap", "business_gap", "immig_gap", "foreign_gap", "vote_gap_z", "econ_gap_z",
        "business_gap_z", "immig_gap_z", "foreign_gap_z", "platform_z", "gap_index", "gap_change", "gap_change_rt",
        "sp_tr", "bond_tr", "rvol", "vix_avg"]
a[cols].round(5).to_csv(D / "gap_annual.csv", index=False)
r = json.load(open(D / "results.json"))
OUT = {"sp_tr": "S&P 500 total return", "bond_tr": "10-yr Treasury return",
       "rvol": "S&P 500 realized volatility", "vix_avg": "VIX (annual average)"}
SPEC = {"level_full": "Gap level, 1921–2022", "level_post1950": "Gap level, 1950–2022",
        "level_ex_depression": "Gap level, excl. 1929–40", "level_next_year": "Gap level → next year",
        "change_full": "Gap change, 1923–2022", "change_post1950": "Gap change, 1950–2022"}
rows = []
for o, lab in OUT.items():
    for s, sl in SPEC.items():
        b = r["reg"][o][s]
        if o == "vix_avg":
            sl = {"level_full": "Gap level, 1990–2024", "level_next_year": "Gap level → next year",
                  "change_full": "Gap change, 1990–2024"}.get(s, sl)
        rows.append({"outcome": o, "outcome_label": lab, "spec": s, "spec_label": sl,
                     "beta": b["beta"], "se": b["beta"] / b["t"], "t": b["t"], "p": b["p"], "n": b["n"]})
reg = pd.DataFrame(rows)
reg = reg[~((reg.outcome == "vix_avg") & reg.spec.isin(["level_post1950", "level_ex_depression", "change_post1950"]))]
reg.round(6).to_csv(D / "gap_regressions.csv", index=False)
COMP = {"vote_gap_z": "Congress voting gap", "econ_gap_z": "Economy platform gap",
        "business_gap_z": "Business/regulation platform gap", "immig_gap_z": "Immigration/identity platform gap", "foreign_gap_z": "Foreign policy platform gap"}
crow = []
for c, cl in COMP.items():
    for o in ["sp_tr", "bond_tr", "rvol"]:
        b = r["reg"]["comp_" + c][o]
        crow.append({"component": c, "component_label": cl, "outcome": o, "outcome_label": OUT[o],
                     "beta": b["beta"], "t": b["t"], "p": b["p"], "n": b["n"]})
pd.DataFrame(crow).round(6).to_csv(D / "gap_components.csv", index=False)
print(reg.to_string()); print(pd.DataFrame(crow).to_string())

vrows = []
for ver, path in [("4 topics (with foreign policy)", D / "results.json"), ("3 topics (original)", D / "three_topic/results.json")]:
    rr = json.load(open(path))
    for o, lab in OUT.items():
        v = rr["value"][o]; c = rr["reg"][o]["change_full"]
        vrows.append({"version": ver, "outcome": o, "outcome_label": lab, "n": v["n"],
                      "chg_p": c["p"], "ctrl_beta": v["chg"]["beta"], "ctrl_p": v["chg"]["p"],
                      "rt_p": v["chg_rt"]["p"], "perm_p": v["perm_p"],
                      "oos_r2": v["oos"]["r2_vs_controls"], "oos_from": v["oos"]["from"]})
pd.DataFrame(vrows).round(6).to_csv(D / "gap_value.csv", index=False)
print(pd.DataFrame(vrows).round(3).to_string())
