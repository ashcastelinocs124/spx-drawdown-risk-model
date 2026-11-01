"""Is the Dem-vs-Rep president pattern (stocks better under Dems, bonds better under Reps)
long-standing or recent? Eras, rolling 30-year windows, and president-by-president returns.
Usage: python3 -I stability.py <data_dir>
"""
import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm

D = sys.argv[1]; W = D + "/work"
a = pd.read_csv(f"{W}/annual.csv", index_col="year").join(
    pd.read_csv(f"{W}/control_by_year.csv", index_col="year")[["president", "government"]])

# price-only S&P 500 return through the latest full year (Shiller monthly averages, Dec to Dec)
sh = pd.read_csv(f"{D}/raw_mkt/shiller.csv", parse_dates=["Date"]).set_index("Date")
dec = sh.SP500[sh.index.month == 12]
dec.index = dec.index.year
price = (dec / dec.shift(1) - 1).rename("sp_px")
a = a.join(price, how="outer")
# party of president for 2025 (Trump, Republican) from the 119th Congress record
a.loc[2025, "president"] = "R"
a["dem"] = (a.president == "D").astype(float)


def diff(d, y):
    d = d[[y, "dem"]].dropna()
    if d.dem.nunique() < 2 or len(d) < 6:
        return np.nan, np.nan, np.nan, np.nan, 0, 0
    m = sm.OLS(d[y], sm.add_constant(d.dem)).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    return (d[d.dem == 1][y].mean(), d[d.dem == 0][y].mean(), m.params.dem, m.pvalues.dem,
            int((d.dem == 1).sum()), int((d.dem == 0).sum()))


eras = [(1921, 1952, "1921–1952"), (1953, 1980, "1953–1980"), (1981, 2000, "1981–2000"), (2001, 2022, "2001–2022")]
rows = []
for lo, hi, lab in eras + [(1921, 2022, "1921–2022 (all)")]:
    for y, yl in [("sp_tr", "S&P 500 total return"), ("bond_tr", "10-yr Treasury return")]:
        dm, rm, b, p, nd, nr = diff(a.loc[lo:hi], y)
        rows.append({"period": lab, "start": lo, "outcome": y, "outcome_label": yl, "dem": dm, "rep": rm,
                     "diff": b, "p": p, "n_dem": nd, "n_rep": nr})
for lo, hi, lab in [(2001, 2025, "2001–2025 (price only)"), (2013, 2025, "2013–2025 (price only)")]:
    dm, rm, b, p, nd, nr = diff(a.loc[lo:hi], "sp_px")
    rows.append({"period": lab, "start": lo, "outcome": "sp_px", "outcome_label": "S&P 500 price return", "dem": dm, "rep": rm,
                 "diff": b, "p": p, "n_dem": nd, "n_rep": nr})
eras_df = pd.DataFrame(rows)
eras_df.round(6).to_csv(f"{W}/dem_rep_eras.csv", index=False)

# rolling 30-year windows
roll = []
for end in range(1950, 2023):
    d = a.loc[end - 29:end]
    r = {"end_year": end, "window": f"{end-29}–{end}"}
    for y in ["sp_tr", "bond_tr"]:
        dm, rm, b, p, nd, nr = diff(d, y)
        r[y + "_diff"], r[y + "_p"] = b, p
    roll.append(r)
roll = pd.DataFrame(roll)
roll.round(6).to_csv(f"{W}/dem_rep_rolling.csv", index=False)

# president by president (calendar years in office as recorded by party control)
terms = [("Harding/Coolidge", 1921, 1928, "R"), ("Hoover", 1929, 1932, "R"), ("F. Roosevelt", 1933, 1944, "D"),
         ("Truman", 1945, 1952, "D"), ("Eisenhower", 1953, 1960, "R"), ("Kennedy/Johnson", 1961, 1968, "D"),
         ("Nixon/Ford", 1969, 1976, "R"), ("Carter", 1977, 1980, "D"), ("Reagan", 1981, 1988, "R"),
         ("G.H.W. Bush", 1989, 1992, "R"), ("Clinton", 1993, 2000, "D"), ("G.W. Bush", 2001, 2008, "R"),
         ("Obama", 2009, 2016, "D"), ("Trump (1st)", 2017, 2020, "R"), ("Biden", 2021, 2024, "D")]
pr = []
for name, lo, hi, party in terms:
    d = a.loc[lo:hi]
    sp = d.sp_tr.dropna(); bd = d.bond_tr.dropna(); px = d.sp_px.dropna()
    pr.append({"president": name, "years": f"{lo}–{hi}", "start": lo, "party": "Democratic" if party == "D" else "Republican",
               "sp_tr_ann": (1 + sp).prod() ** (1 / len(sp)) - 1 if len(sp) else np.nan,
               "bond_tr_ann": (1 + bd).prod() ** (1 / len(bd)) - 1 if len(bd) else np.nan,
               "sp_px_ann": (1 + px).prod() ** (1 / len(px)) - 1 if len(px) else np.nan,
               "n_tr": len(sp), "n_px": len(px)})
pr = pd.DataFrame(pr)
pr.round(6).to_csv(f"{W}/president_returns.csv", index=False)

pd.set_option("display.width", 220)
print(eras_df.round(3).to_string(index=False))
print(roll.iloc[::5].round(3).to_string(index=False))
print("share of 30y windows Dem>Rep stocks:", round((roll.sp_tr_diff > 0).mean(), 2), " Rep>Dem bonds:", round((roll.bond_tr_diff < 0).mean(), 2))
print(pr.round(3).to_string(index=False))
print(a.loc[2019:2025, ["president", "sp_tr", "sp_px", "bond_tr"]].round(3))
