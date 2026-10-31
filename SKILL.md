---
name: spx-drawdown-risk-model
description: Run, update or extend ARC Capital's S&P 500 5%-drawdown risk model (random forest on 7 VIX and trend variables). Use to score current 20-day crash risk, re-run the out-of-sample tests, or test a new predictor against the final model.
---

# SPX 5% Drawdown Risk Model

## What the model answers
For each trading day t:

    Y_t = 1  if the S&P 500 closes >= 5% below today's close on any of the next 20 trading days, else 0

The model outputs P(Y_t = 1). Closing prices only; intraday dips that recover by the close do not count.
The unconditional rate is about 15-17% of days (1990-2026).

## The final model (do not change without re-running the evaluation)
- **Algorithm:** Random forest, 400 trees, max_depth=5, min_samples_leaf=200, random_state=0. No hyperparameter tuning on test data.
- **Inputs (7, all known at today's close):**
  | Variable | Definition |
  |---|---|
  | vix | CBOE VIX close |
  | vix_chg_5d | % change in VIX over 5 days |
  | vrp | VIX minus 20-day realised vol of the S&P 500 (annualised %) |
  | ret_20d | S&P 500 % change over 20 days |
  | dist_ma200 | Close / 200-day MA - 1 |
  | drawdown_252d | Close / 252-day high - 1 |
  | rsi_14 | 14-day RSI |
- **Training:** expanding window from 1990, refit every January. Never use a short rolling window (5-10 yr windows scored below 0.5 AUC).
- **Benchmark to always report alongside:** linear probability model (OLS on standardised inputs, clipped to 0-1). It ties the RF on single test periods and is interpretable.

## How to run
```bash
pip install -r requirements.txt
python3 scripts/spx_risk_model.py fetch            # downloads ~240 MB (SPY parquet) + small CSVs into data/
python3 scripts/spx_risk_model.py evaluate          # out-of-sample tests -> results/evaluation_0.05.json (~5 min)
python3 scripts/spx_risk_model.py score             # fit on all history, score the most recent days -> results/latest_score_0.05.json
```
`--drop 0.025` (or any value) changes the threshold. 5% is the validated target; 2.5% is harder (AUC ~0.58).

### Fresher data
The public VIX file can lag. To score up to today, drop `data/vix_override.csv` and/or `data/spx_override.csv`
(columns: `Date,Close`) into `data/`; they are spliced onto the end of each series by return-chaining.
Only use data from a checkable source (CBOE, FRED VIXCLS/SP500, Yahoo) and say which one in your output.

## Expected results (reproduce these before trusting any change)
| Model | AUC test 2010-19 | AUC test 2020-Sep 2026 | AUC walk-forward 2000-2026 | Brier skill (walk-fwd) |
|---|---|---|---|---|
| Random forest (final) | 0.622 | 0.662 | **0.682** | **+0.083** |
| Linear (LPM) | 0.618 | 0.665 | 0.637 | +0.050 |
| Logistic | 0.626 | 0.658 | 0.611 | +0.020 |

If `evaluate` does not reproduce these within about +/-0.01 on the same data, stop and find out why before going further.

## How to read the output
- `score` prints the RF and LPM probability, the base rate, and where today's RF reading sits versus its own history
  (percentile). Regime label: HIGH (>= 80th percentile), ELEVATED (60-80th), NORMAL/LOW (< 60th).
- **It is a risk thermometer, not a timing signal.** It separates stressed regimes (2008, 2020, March 2026) from calm ones and
  stays low in steady rallies. It does NOT warn before falls that start from low VIX (Feb 2020, Aug 2024), and its peak
  readings usually come after the sell-off has started. Say this whenever you report a reading.
- AUC: 0.5 = coin flip, 1.0 = perfect ranking. Brier skill: improvement in probability accuracy over always predicting the base rate.

## Extending the model: rules
1. Any new predictor must be tested as **technical-7 + new variable** against technical-7 alone, on the same sample, using all
   three tests (2010-19 fixed split, 2020+ fixed split, walk-forward). Report all three; a gain in one test only is not a gain.
2. Point-in-time only: lag fundamentals by their publication delay (earnings 3 months, CPI/yields 1 month); compute rolling
   averages with `.shift(1)`; standardise with training-period statistics only; leave a 1-month gap between train and test.
3. Use Newey-West (HAC, 20 lags) standard errors for any t-stat: consecutive days share 19 of 20 forward days.
   Slow-moving predictors (CAPE, concentration) need even more caution: years of near-identical readings are one observation.
4. Do not remove crisis periods (2008-09, 2020) as "outliers". They are the events being predicted; removing them made every
   model worse.
5. Use real, verifiable data only. Never interpolate or invent figures. Cite sources in any write-up.

## What has already been tested and rejected (see reference/findings.md for numbers)
- Fundamentals (CAPE, EPS growth, 10y yield, equity risk premium): strong in-sample, AUC <= 0.5 out of sample (fit the dot-com era).
- P/E vs its own 1-30 yr average: short windows duplicate momentum; long windows add at most ~+0.02.
- Market concentration (cap-weight vs equal-weight) and breadth (% above 200d MA): no gain once VIX is in.
- Sector concentration (incl. boom-only version): small, inconsistent gains.
- Gradient boosting, SVM, neural net, k-NN: no better than the RF; SVM and boosting overfit.

## Most promising next steps (not yet tested)
Credit spreads (ICE BofA HY OAS, FRED BAMLH0A0HYM2), VIX term structure (VIX/VIX3M), yield-curve slope (10y-3m),
and a longer target (>= 10% drawdown within 6-12 months) where valuation and concentration may matter.
