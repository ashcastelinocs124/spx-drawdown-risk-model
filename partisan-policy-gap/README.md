# Partisan Policy Gap & the Markets

Do markets care how far apart Democrats and Republicans are on policy? This study builds a **Partisan Policy Gap index** from a century of congressional votes and party platforms, then tests it against stocks, Treasuries, volatility and the VIX (1921–2024). It also tests it against who controls government and against what Congress actually passes.

**Bottom line:** the gap is a good gauge of polarization (2023–24 is the widest point on record, +2.44 SD), but it is **not a market signal**. Who holds power has mattered more than what the parties believe.

## Key findings

| Finding | Evidence (all in `outputs/`) |
|---|---|
| The belief gap doesn't move markets | Correlation with S&P 500 total return +0.04 (1921–2022), +0.01 since 1950 (`correlations.csv`) |
| It doesn't help forecasting | Added to a controls-only model, out-of-sample R² for stocks fell 8.4% (`gap_value.csv`) |
| Recent-decade signals were trend coincidences | Since 1980, 3 of 11 period tests had p < 0.05; none survive a time trend (`recent_windows.csv`) |
| Elections don't change the picture | 0 of 84 post-election tests (1, 3, 6 months) significant (`post_election_tests.csv`) |
| VIX: weak, not significant | Monthly VIX vs gap: corr −0.12, p = 0.38; trend removed p = 0.08 (`vix_tests.csv`) |
| Power beats beliefs | 10-yr Treasuries returned 8.3%/yr under split government vs 2.5% under one-party control, p < 0.001 (`gap_control_cells.csv`, `gap_control_tests.csv`) |
| Best mix of president and Congress | Stocks: Dem president with Rep House and Senate, 16.0%/yr over 10 years (up 9 of 10), vs 12.3% average; not statistically reliable. Bonds: Rep president with Dem House and Rep Senate, 14.5%/yr vs 5.2% average, p = 0.002 (`combo_returns.csv`) |
| Words and votes diverge | Platform gap vs actual voting gap: correlation +0.05 across 52 Congresses (`legislative_tests.csv`) |

## How the index is built

1. **Voting gap:** Republican minus Democratic mean on DW-NOMINATE dimension 1, averaged over House and Senate, per Congress (Voteview).
2. **Platform gaps:** Manifesto Project coding of each presidential platform since 1920. For four topics (economy, business regulation, immigration/identity, foreign policy), a log-ratio position score per party (Lowe et al. 2011). The gap is Republican minus Democratic, applied to the four years after each election.
3. **Composite:** each component is standardized over 1921–2024. Index = ½ voting gap + ½ mean of the four platform topics, then re-standardized.

The market outcomes are:
- S&P 500 calendar-year total return and realized volatility (Shiller monthly data)
- 10-yr Treasury return (constant-maturity par bond priced from Shiller's long rate)
- VIX (Cboe, 1990 on)

Tests use Newey-West standard errors throughout. Robustness checks include:
- era splits and excluding the Depression
- time-trend controls
- block permutation tests
- expanding-window out-of-sample forecasts
- a real-time version that uses only information known on January 1

## Run it

```bash
pip install -r ../requirements.txt
./fetch_data.sh            # ~700 MB into ./data (git-ignored)
./run_all.sh               # rebuilds everything into ./outputs
```

| Script | What it does |
|---|---|
| `scripts/build.py` | Builds the index and market outcomes; level/change regressions; usefulness tests (controls, real-time, out-of-sample, permutation). `--no-foreign` gives the original 3-topic index |
| `scripts/export.py` | Summary tables of regressions, components and usefulness tests |
| `scripts/control.py` | Divided vs unified government × gap |
| `scripts/postelection.py` | Market moves 1, 3 and 6 months after each November election |
| `scripts/vix_test.py` | Monthly VIX against the gap and its parts |
| `scripts/legislative.py` | Platform gap vs party-unity votes, bipartisan votes and laws enacted per Congress |
| `scripts/extras.py` | Recent-decade windows, split-government detail, correlations |
| `scripts/combos.py` | Returns for every president / House / Senate party combination |
| `dashboard/index.html` | Source of the interactive dashboard page. It runs inside Claude's dashboard runtime, so it does not open as a standalone file |

## Data sources

- [Voteview](https://voteview.com): DW-NOMINATE party means, members and member votes (Lewis, Poole, Rosenthal et al.)
- [Manifesto Project](https://manifesto-project.wzb.eu): MPDS2024a. The official download needs a free account; `fetch_data.sh` uses a public mirror
- [Shiller market data](https://github.com/datasets/s-and-p-500) and [Cboe VIX](https://github.com/datasets/finance-vix). These files keep updating, so a fresh download can shift results slightly
- [Libgober (2024), *Scientific Data*](https://doi.org/10.1038/s41597-023-02758-z): comprehensive dataset of U.S. federal laws
- [Party divisions of United States Congresses](https://en.wikipedia.org/wiki/Party_divisions_of_United_States_Congresses): party control (hard-coded in `control.py`)

## Next steps

1. **Measure the say–do gap.** Quantify the difference between what parties and candidates run on and how they vote, at three levels:
   - party (platform position vs voting position, by topic)
   - pledge (share of platform promises enacted)
   - member (campaign-side ideology, e.g. Bonica's DIME CFscores, vs DW-NOMINATE)
2. **Measure policy output.** Build a Policy Output variable from what Congress actually enacts:
   - volume (laws and pages)
   - bipartisanship (minority-party support on final passage)
   - direction (where enacted bills sit on the left–right scale)

   Then test it against market moves around enactment dates.
3. **Predict AI data-center policy.** Use these measures to forecast the policies that drive AI data-center build-out:
   - power-grid and permitting rules
   - energy tax credits
   - chip subsidies and export controls
   - AI regulation

   Test those forecasts against data-center build-out and the market segments that depend on it: chipmakers, utilities and data-center operators.

## Caveats

- **Small effective samples.** The gap moves slowly, so there are only about 50 Congresses.
- **Chance results.** With well over 100 tests, a few p < 0.05 results are expected by chance alone.
- **Repeated platforms.** The 2020 Republican platform repeated 2016's, so their topic scores are identical. 2024 platforms are not yet coded.
- **Return data ends in 2022.** Shiller dividends stop in mid-2023, so total-return tests end in 2022.
- **Law counts end in 2020.** 2021–24 counts are excluded because that source is incomplete there.
- **Correlation, not causation.** Educational research using public data, not investment advice.
