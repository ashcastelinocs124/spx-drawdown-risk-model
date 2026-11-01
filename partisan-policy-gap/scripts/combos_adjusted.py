"""Sample-size-adjusted returns by party combination (empirical-Bayes shrinkage),
plus an era-adjusted version (return minus that decade's average).
Usage: python3 -I combos_adjusted.py <data_dir>
"""
import sys
import numpy as np
import pandas as pd

W = sys.argv[1] + "/work"
a = pd.read_csv(f"{W}/annual.csv", index_col="year").join(
    pd.read_csv(f"{W}/control_by_year.csv", index_col="year")[["president", "house", "senate", "government"]]).loc[1921:2022]
P = {"D": "Dem", "R": "Rep"}
a["combo"] = a.apply(lambda r: f"{P[r.president]} president, {P[r.house]} House, {P[r.senate]} Senate", axis=1)
a["pres"] = a.president.map({"D": "Democratic president", "R": "Republican president"})
cong = lambda r: "Congress same party" if r.house == r.senate == r.president else ("Congress opposite party" if r.house == r.senate else "Split Congress")
a["pres_cong"] = a.pres + ", " + a.apply(cong, axis=1).str.lower()
a["decade"] = (a.index // 10) * 10
for o in ["sp_tr", "bond_tr"]:
    a[o + "_era"] = a[o] - a.groupby("decade")[o].transform("mean")

rng = np.random.default_rng(11)


def shrink(df, group, y):
    """Random-intercept model fitted by REML: each group's mean is pulled toward the
    overall mean by tau2 / (tau2 + sigma2 / n), so small groups move most."""
    import statsmodels.formula.api as smf
    d = df[[group, y]].dropna().rename(columns={group: "grp", y: "yy"})
    fit = smf.mixedlm("yy ~ 1", d, groups=d["grp"]).fit(reml=True)
    grand = float(fit.fe_params.iloc[0])
    s2 = float(fit.scale)                                  # within-group variance
    tau2 = max(float(fit.cov_re.iloc[0, 0]), 1e-8)         # between-group variance
    g = d.groupby("grp")["yy"].agg(["mean", "count"])
    w = tau2 / (tau2 + s2 / g["count"])
    g["shrunk"] = grand + w * (g["mean"] - grand)
    g["post_sd"] = np.sqrt(w * s2 / g["count"])
    g["se"] = np.sqrt(s2 / g["count"])
    g["weight"] = w
    draws = rng.normal(g["shrunk"].values, g["post_sd"].values, size=(20000, len(g)))
    g["p_best"] = np.bincount(draws.argmax(axis=1), minlength=len(g)) / len(draws)
    g["grand"] = grand
    return g


rows = []
for group, label in [("combo", "President, House, Senate"), ("pres_cong", "President and Congress")]:
    for o, ol in [("sp_tr", "S&P 500"), ("bond_tr", "10-yr Treasury")]:
        g = shrink(a, group, o)
        ge = shrink(a, group, o + "_era")
        for k in g.index:
            rows.append({"grouping": label, "group": k, "outcome": o, "outcome_label": ol, "n": int(g.loc[k, "count"]),
                         "raw": g.loc[k, "mean"], "ci_lo": g.loc[k, "mean"] - 1.96 * g.loc[k, "se"],
                         "ci_hi": g.loc[k, "mean"] + 1.96 * g.loc[k, "se"], "weight": g.loc[k, "weight"],
                         "adjusted": g.loc[k, "shrunk"], "p_best": g.loc[k, "p_best"], "grand": g.loc[k, "grand"],
                         "era_adjusted": ge.loc[k, "shrunk"] + g.loc[k, "grand"], "p_best_era": ge.loc[k, "p_best"]})
r = pd.DataFrame(rows)
r.round(6).to_csv(f"{W}/combo_adjusted.csv", index=False)
pd.set_option("display.width", 250)
for (gr, o), d in r.groupby(["grouping", "outcome"], sort=False):
    print(f"\n== {gr} | {o}")
    print(d.sort_values("adjusted", ascending=False)[["group", "n", "raw", "ci_lo", "ci_hi", "weight", "adjusted", "p_best", "era_adjusted", "p_best_era"]].round(3).to_string(index=False))
# two-group comparisons (groups are similar in size, so compare directly)
import statsmodels.api as sm
two = []
for col, g1, g0, label in [("president", "D", "R", "President's party"), ("government", "Divided", "Unified", "Government type")]:
    names = {"D": "Democratic president", "R": "Republican president", "Divided": "Split government", "Unified": "One-party government"}
    x = (a[col] == g1).astype(float)
    for o, ol in [("sp_tr", "S&P 500"), ("bond_tr", "10-yr Treasury")]:
        m = sm.OLS(a[o], sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
        me = sm.OLS(a[o + "_era"], sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
        grand = a[o].mean()
        for k in (g1, g0):
            sel = a[col] == k
            two.append({"grouping": label, "group": names[k], "outcome": o, "outcome_label": ol, "n": int(sel.sum()),
                        "raw": a.loc[sel, o].mean(), "era_adjusted": grand + a.loc[sel, o + "_era"].mean(),
                        "diff": m.params.iloc[1], "p": m.pvalues.iloc[1],
                        "diff_era": me.params.iloc[1], "p_era": me.pvalues.iloc[1], "diff_of": f"{names[g1]} minus {names[g0]}"})
t = pd.DataFrame(two)
t.round(6).to_csv(f"{W}/party_compare.csv", index=False)
print(t.round(3).to_string(index=False))
