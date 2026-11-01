"""Year-by-year returns for the standout mix: Republican president, Democratic House,
Republican Senate (1931-32, 1981-86, 2019-20).
Usage: python3 -I closeup.py <data_dir>
"""
import json, sys
import pandas as pd
D = sys.argv[1]; W = D + "/work"
a = pd.read_csv(f"{W}/annual.csv", index_col="year")
sh = pd.read_csv(f"{D}/raw_mkt/shiller.csv", parse_dates=["Date"]).set_index("Date")
d = sh.SP500[sh.index.month == 12]; d.index = d.index.year
px = d / d.shift(1) - 1
who = {1931: "Hoover", 1932: "Hoover", **{y: "Reagan" for y in range(1981, 1987)}, 2019: "Trump", 2020: "Trump"}
stretch = {1931: "1931–32 (Great Depression)", 1932: "1931–32 (Great Depression)",
           **{y: "1981–86" for y in range(1981, 1987)}, 2019: "2019–20", 2020: "2019–20"}
rows = [{"year": y, "president": who[y], "stretch": stretch[y], "depression": y < 1933,
         "sp_px": round(float(px[y]), 6), "bond_tr": round(float(a.loc[y, "bond_tr"]), 6)} for y in sorted(who)]
pd.DataFrame(rows).to_csv(f"{W}/mix_closeup.csv", index=False)
json.dump(rows, open(f"{W}/mix_closeup.json", "w"), ensure_ascii=False)
print(pd.DataFrame(rows).to_string(index=False))
