"""Gap index vs VIX: monthly levels, terciles, around new Congresses. Usage: python3 -I vix_test.py <data_dir>"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm
D = Path(sys.argv[1]); W = D / "work"
a = pd.read_csv(W / "annual.csv", index_col="year")
vix = pd.read_csv(D / "raw_mkt/vix.csv", parse_dates=["DATE"]).set_index("DATE").CLOSE
m = vix.resample("MS").mean().to_frame("vix").loc["1990-01":"2024-12"]
m["year"] = m.index.year
for c in ["gap_index", "vote_gap_z", "platform_z", "gap_change"]:
    m[c] = m.year.map(a[c])
m["t"] = np.arange(len(m))
m["dvix"] = m.vix.diff()
def hac(y, xs, d, lags=24):
    d = d[[y] + xs].dropna()
    r = sm.OLS(d[y], sm.add_constant(d[xs])).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return r.params[xs[0]], r.pvalues[xs[0]], int(r.nobs), r.rsquared
out = {}
print("months", len(m))
for c in ["gap_index", "vote_gap_z", "platform_z"]:
    print(f"corr VIX vs {c}: {m.vix.corr(m[c]):+.3f}")
for name, xs in [("level", ["gap_index"]), ("level+trend", ["gap_index", "t"]),
                 ("votes only", ["vote_gap_z"]), ("platforms only", ["platform_z"]),
                 ("change", ["gap_change"])]:
    b, p, n, r2 = hac("vix", xs, m)
    out[name] = (b, p, n, r2); print(f"{name:15s} beta={b:+.2f} VIX pts per SD  p={p:.3f}  n={n}  R2={r2:.3f}")
q = m.gap_index.quantile([1/3, 2/3]).values
m["ter"] = np.where(m.gap_index <= q[0], "Narrow", np.where(m.gap_index <= q[1], "Middle", "Wide"))
print(m.groupby("ter").vix.agg(["mean", "median", "count"]).round(2))
print("years by tercile:", {k: sorted(set(v)) for k, v in m.groupby("ter").year})
# around each new Congress: avg VIX Feb-Apr vs Oct-Dec before
ev = []
for y in range(1991, 2024, 2):
    pre = m.loc[f"{y-1}-10":f"{y-1}-12", "vix"].mean(); post = m.loc[f"{y}-02":f"{y}-04", "vix"].mean()
    ev.append({"year": y, "gap_change": a.gap_change.get(y), "dvix": post - pre})
ev = pd.DataFrame(ev).dropna()
r = sm.OLS(ev.dvix, sm.add_constant(ev.gap_change)).fit(cov_type="HC1")
print(f"new-Congress VIX change vs gap change: corr={ev.dvix.corr(ev.gap_change):+.3f} beta={r.params.gap_change:+.2f} p={r.pvalues.gap_change:.3f} n={len(ev)}")
print(ev.round(2).to_string())
# monthly VIX change vs gap (does VIX drift up/down more in wide-gap periods)
b, p, n, r2 = hac("dvix", ["gap_index"], m, 12); print(f"monthly VIX change vs gap: beta={b:+.3f} p={p:.3f}")
ann = m.groupby("year").agg(vix=("vix", "mean"), gap=("gap_index", "first"))
print("annual corr", round(ann.vix.corr(ann.gap), 3), "| spearman", round(ann.vix.corr(ann.gap, method="spearman"), 3))
m.to_csv(W / "vix_monthly.csv"); ev.to_csv(W / "vix_congress.csv", index=False)
