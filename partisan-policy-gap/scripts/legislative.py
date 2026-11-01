"""Does the platform (belief) gap show up in how Congress actually behaves?

Outcomes per Congress, 67th-118th (1921-2024):
  - Voting polarization: DW-NOMINATE party distance (Voteview)
  - Party-unity votes: share of roll calls where a majority of Democrats opposed a
    majority of Republicans (Voteview member votes); bipartisan = majorities agree
  - Laws enacted and pages of law (Libgober 2024, Sci Data, comprehensive database of laws)
Explanatory: platform gap (z) from the Manifesto Project, set by the preceding
presidential election; controls: divided government, time trend.
Usage: python3 -I legislative.py <data_dir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

D = Path(sys.argv[1]); W = D / "work"; L = D / "raw_leg"
a = pd.read_csv(W / "annual.csv", index_col="year")
ctrl = pd.read_csv(W / "control_by_year.csv", index_col="year")

# ---- party-unity and bipartisan roll calls
mem = pd.read_csv(L / "HSall_members.csv", usecols=["congress", "chamber", "icpsr", "party_code"])
mem = mem[(mem.congress >= 67) & mem.chamber.isin(["House", "Senate"])].drop_duplicates(["congress", "chamber", "icpsr"])
rows = []
for chunk in pd.read_csv(L / "HSall_votes.csv", usecols=["congress", "chamber", "rollnumber", "icpsr", "cast_code"],
                         dtype={"congress": "int16", "rollnumber": "int32", "icpsr": "int32", "cast_code": "int8"},
                         chunksize=4_000_000):
    c = chunk[(chunk.congress >= 67) & chunk.chamber.isin(["House", "Senate"]) & chunk.cast_code.between(1, 6)]
    c = c.merge(mem, on=["congress", "chamber", "icpsr"], how="left")
    c = c[c.party_code.isin([100, 200])]
    c["yea"] = (c.cast_code <= 3).astype("int8")
    rows.append(c.groupby(["congress", "chamber", "rollnumber", "party_code"]).yea.agg(["sum", "count"]))
v = pd.concat(rows).groupby(level=[0, 1, 2, 3]).sum().unstack("party_code")
v = v.dropna()
shareD = v[("sum", 100)] / v[("count", 100)]
shareR = v[("sum", 200)] / v[("count", 200)]
rc = pd.DataFrame({"D": shareD, "R": shareR})
rc = rc[(v[("count", 100)] >= 5) & (v[("count", 200)] >= 5)]
rc["unity"] = ((rc.D - 0.5) * (rc.R - 0.5) < 0).astype(float)          # majorities opposed
rc["bipartisan"] = ((rc.D - 0.5) * (rc.R - 0.5) > 0).astype(float)     # majorities agree
rc["consensus"] = ((rc.D >= 0.9) & (rc.R >= 0.9) | (rc.D <= 0.1) & (rc.R <= 0.1)).astype(float)
per = rc.groupby(["congress", "chamber"])[["unity", "bipartisan", "consensus"]].mean().unstack("chamber")
cong = pd.DataFrame({
    "unity_house": per[("unity", "House")], "unity_senate": per[("unity", "Senate")],
    "bipartisan_house": per[("bipartisan", "House")], "bipartisan_senate": per[("bipartisan", "Senate")],
    "consensus": per["consensus"].mean(axis=1),
})
cong["unity"] = cong[["unity_house", "unity_senate"]].mean(axis=1)
cong["bipartisan"] = cong[["bipartisan_house", "bipartisan_senate"]].mean(axis=1)
cong["rollcalls"] = rc.groupby("congress").size()

# ---- laws enacted (public laws) and pages
laws = pd.read_csv(D / "raw_dbl/repo/Releases/master_update_v20250904.csv", low_memory=False)
laws = laws[laws.congress_number.between(67, 118)]
pub = laws[laws.pl_no.notna()].copy()
pub["sal_volume"] = pd.to_numeric(pub.sal_volume, errors="coerce")
pub["sal_page_start"] = pd.to_numeric(pub.sal_page_start, errors="coerce")
pub = pub.sort_values(["sal_volume", "sal_page_start"])
nxt = pub.groupby("sal_volume").sal_page_start.shift(-1)
pub["pages"] = (nxt - pub.sal_page_start).clip(lower=1)
cong["public_laws"] = pub.groupby("congress_number").size()
cong["law_pages"] = pub.groupby("congress_number").pages.sum(min_count=1)
cong.loc[cong.index >= 117, ["law_pages", "public_laws"]] = np.nan  # NARA-sourced 2022-24 rows incomplete/duplicated

# ---- explanatory variables per Congress (first year of the Congress)
cong["year"] = 1787 + 2 * cong.index
for c in ["platform_z", "vote_gap", "vote_gap_z", "gap_index"] + [c for c in a.columns if c.endswith("_gap_z") and c != "vote_gap_z"]:
    cong[c] = cong.year.map(a[c])
cong["divided"] = cong.year.map(ctrl.government).eq("Divided").astype(float)
cong["t"] = cong.index - 67
cong = cong.loc[67:118]
cong.index.name = "congress"
cong.round(5).to_csv(W / "legislative_by_congress.csv")


def fit(y, xs, d=cong):
    d = d[[y] + xs].dropna()
    m = sm.OLS(d[y], sm.add_constant(d[xs])).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    return m


OUT = {"vote_gap": "Voting gap (DW-NOMINATE)", "unity": "Party-unity votes (share)",
       "bipartisan": "Bipartisan votes (share)", "consensus": "Near-unanimous votes (share)",
       "public_laws": "Public laws enacted", "law_pages": "Pages of law enacted"}
res = []
for o, lab in OUT.items():
    sd_y = cong[o].std()
    for spec, xs in [("Simple", ["platform_z"]), ("+ divided gov", ["platform_z", "divided"]),
                     ("+ divided gov + trend", ["platform_z", "divided", "t"]),
                     ("Since 1953", ["platform_z"])]:
        d = cong.loc[83:] if spec == "Since 1953" else cong
        m = fit(o, xs, d)
        res.append({"outcome": o, "outcome_label": lab, "spec": spec, "beta": m.params["platform_z"],
                    "beta_sd": m.params["platform_z"] / sd_y, "p": m.pvalues["platform_z"], "n": int(m.nobs),
                    "corr": d[[o, "platform_z"]].dropna().corr().iloc[0, 1] if spec in ("Simple", "Since 1953") else np.nan,
                    "divided_beta": m.params.get("divided", np.nan), "divided_p": m.pvalues.get("divided", np.nan)})
res = pd.DataFrame(res)
res.round(6).to_csv(W / "legislative_tests.csv", index=False)
# topic-by-topic correlation with outcomes
topics = [c for c in cong.columns if c.endswith("_gap_z") and c != "vote_gap_z"]
tc = []
for t in topics:
    for o in OUT:
        m = fit(o, [t])
        tc.append({"topic": t, "outcome": o, "corr": cong[[o, t]].dropna().corr().iloc[0, 1], "p": m.pvalues[t]})
tc = pd.DataFrame(tc)
tc.round(6).to_csv(W / "legislative_topics.csv", index=False)
pd.set_option("display.width", 220)
print(cong[["year", "platform_z", "vote_gap", "unity", "bipartisan", "consensus", "public_laws", "law_pages", "divided", "rollcalls"]].round(3).to_string())
print(res.round(3).to_string())
print(tc.round(3).pivot(index="topic", columns="outcome", values="corr").to_string())
print(tc.round(3).pivot(index="topic", columns="outcome", values="p").to_string())
