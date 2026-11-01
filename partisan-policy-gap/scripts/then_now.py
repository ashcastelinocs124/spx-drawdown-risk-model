"""Party-mix rankings before vs since 1991. Stocks use S&P 500 price return (Dec-to-Dec,
Shiller monthly averages) so the recent period can run through 2025; bonds use the
constant-maturity 10-yr return through 2022.
Usage: python3 -I then_now.py <data_dir>
"""
import json, sys
import pandas as pd
D = sys.argv[1]; W = D + "/work"
a = pd.read_csv(f"{W}/annual.csv", index_col="year").join(
    pd.read_csv(f"{W}/control_by_year.csv", index_col="year")[["president", "house", "senate"]], how="outer")
sh = pd.read_csv(f"{D}/raw_mkt/shiller.csv", parse_dates=["Date"]).set_index("Date")
dec = sh.SP500[sh.index.month == 12]; dec.index = dec.index.year
a = a.join((dec / dec.shift(1) - 1).rename("sp_px"), how="outer")
a.loc[2025, ["president", "house", "senate"]] = ["R", "R", "R"]   # 119th Congress (2025-26)
a = a.loc[1921:2025].dropna(subset=["president"])
P = {"D": "Dem", "R": "Rep"}
a["combo"] = a.apply(lambda r: f"{P[r.president]} president, {P[r.house]} House, {P[r.senate]} Senate", axis=1)
rows = []
for col, lab, periods in [("sp_px", "S&P 500 price return", [(1921, 1990, "1921–1990"), (1991, 2025, "1991–2025")]),
                          ("bond_tr", "10-yr Treasury return", [(1921, 1990, "1921–1990"), (1991, 2022, "1991–2022")])]:
    for lo, hi, pl in periods:
        d = a.loc[lo:hi].dropna(subset=[col])
        g = d.groupby("combo")[col].agg(["mean", "count"])
        g["rank"] = g["mean"].rank(ascending=False).astype(int)
        for c, r in g.iterrows():
            rows.append({"outcome": col, "outcome_label": lab, "period": pl, "era": "before" if lo == 1921 else "since",
                         "combo": c, "mean": round(r["mean"], 6), "n": int(r["count"]), "rank": int(r["rank"]),
                         "of": len(g), "years": ", ".join(map(str, d[d.combo == c].index))})
df = pd.DataFrame(rows)
df.to_csv(f"{W}/combo_then_now.csv", index=False)
json.dump(df.to_dict("records"), open(f"{W}/combo_then_now.json", "w"), ensure_ascii=False)
pd.set_option("display.width", 220)
print(df.drop(columns="years").pivot_table(index="combo", columns=["outcome", "era"], values=["mean", "rank", "n"]).round(3).to_string())
