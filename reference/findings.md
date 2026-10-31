# Research log: what was tested (Oct 2026)

Target throughout: >= 5% S&P 500 close-to-close fall within 20 trading days unless stated.
AUC = out-of-sample ranking skill (0.5 = coin flip). "Walk-forward" = expanding window refit each January.

## 1. Linear vs logistic, technical vs fundamental (train 1990-2009, test 2010-19)
| Model | Features | AUC train | AUC 2010-19 | AUC 2020-Sep 26* | Walk-fwd 2000-19 |
|---|---|---|---|---|---|
| LPM | Technical (7) | 0.755 | 0.618 | 0.665 | 0.642 |
| Logit | Technical (7) | 0.750 | 0.626 | 0.658 | 0.581 |
| LPM | Fundamental (CAPE, 10y, ERP, EPS g) | 0.751 | 0.398 | 0.384 | - |
| Logit | Fundamental | 0.761 | 0.407 | 0.381 | - |
| LPM | Combined | 0.811 | 0.514 | 0.643 | 0.642 |
| Logit | Combined | 0.808 | 0.498 | 0.639 | 0.581 |
*2020+ tests trained through 2019; fundamental/combined tests end Sep 2023 (earnings data).

Strongest single predictor out of sample: VIX level (AUC 0.64). Days with VIX < 12 were followed by a 5% fall 4% of the time;
VIX > 40, 52%.

## 2. Why CAPE looked important
61% of 1990-2009 event days were in 1997-2003 and every CAPE > 30 day was in 1997-2002. CAPE's top quartile had a 27.7% event
rate vs 10.6% bottom quartile in training; after 2010, CAPE > 30 days had 17.6% vs 15.3% for CAPE 20-25. CAPE was ~uncorrelated
with VIX (0.05), so in the combined model it took credit for the dot-com bear market.

## 3. ML comparison (7 technical features, same tests)
| Model | AUC 2010-19 | AUC 2020-Sep 26 | Walk-fwd 2000-26 | Brier skill wf |
|---|---|---|---|---|
| Random forest | 0.622 | 0.660 | 0.682 | +0.082 |
| k-NN (k=250) | 0.615 | 0.624 | 0.673 | +0.071 |
| Gradient boosting | 0.604 | 0.651 | 0.666 | +0.048 |
| Lasso logit | 0.625 | 0.661 | 0.655 | +0.056 |
| LPM | 0.618 | 0.665 | 0.637 | +0.050 |
| Neural net (MLP) | 0.611 | 0.658 | 0.614 | +0.030 |
| Logistic | 0.626 | 0.658 | 0.611 | +0.020 |
| SVM (RBF) | 0.560 | 0.507 | 0.560 | -0.054 |
RF importance (13-feature run): VIX 20%, drawdown 20%, dist from 200d MA 19%, realised vol 13%, 60d return 10%.

## 4. 2026 out of sample (technical logit trained 1990-2025)
AUC 0.86. One episode: days 20 Feb - 17 Mar 2026 were followed by >= 5% falls. Probability rose from ~13% to 24% during the fall
and peaked at 28.5% in the week of 27 Mar (the bottom). First top-20% flag 6 Mar; 2 of 16 event days flagged.

## 5. Threshold 2.5% vs 5%
2.5%: AUC 0.59 (2010-19), 0.58 (2020-26), 0.59 walk-forward. 5% is more predictable.

## 6. Training window
Walk-forward 2020-26: all history 0.64, last 10 years 0.46-0.49, last 5 years 0.42-0.44.

## 7. P/E vs its own N-year average (added to technical logit, walk-forward 2000-23; baseline 0.609)
P/E rel: 1y 0.597, 2y 0.585, 3y 0.603, 5y 0.620, 7y 0.623, 10y 0.612, 15y 0.606, 20y 0.618, 30y 0.634.
CAPE rel: 1y 0.600, 3y 0.575, 5y 0.558, 10y 0.590, 20y 0.621, 30y 0.638. CAPE level: 0.651.
Trailing P/E breaks in recessions (2009 P/E ~94, flagged "expensive" at the bottom).

## 8. Market concentration and breadth (2003-26 walk-forward, baseline 0.610)
Cap-weight minus equal-weight 12m: 0.603; 36m: 0.606; breadth (% members above 200d MA): 0.609; "narrow high" (index within 5%
of 1y high, breadth < 50%): 0.612. Narrow high is rare (2.8% of days) but followed by falls 33% of the time vs 18%.
Equal-weight index built from point-in-time constituents (corr 0.99 with RSP).

## 9. Sector concentration (sector ETF / SPY relative strength vs own 3-5y average; walk-forward 2010-26, baseline LPM 0.616)
Top sector vs 3y avg: 0.620; tech vs 5y: 0.633; imbalance 3y: 0.637 (but 2020-26 test drops 0.66 -> 0.58).
Heavy (> 20% above 3y norm): 1,428 days 2003-26, 1,267 boom-driven (sector's own price above its average; 20% fall rate)
and 161 collapse-driven (defensives in 2008-09; 52%). Boom-only version: 2010-19 0.64, 2020-26 0.65, walk-forward 0.62 (t = 1.0).
Removing GFC/COVID as outliers lowered every model (technical walk-forward 0.62 -> 0.56-0.58).

## Data sources
- S&P 500 daily to 2019-12-23: https://github.com/fja05680/dow-sp500-100-years
- SPY, sector ETFs, S&P 500 point-in-time members: https://github.com/Johnbrick123/sp500-data (Yahoo source)
- CBOE VIX daily: https://github.com/datasets/finance-vix
- Shiller monthly earnings, dividends, CPI, 10y yield: https://github.com/datasets/s-and-p-500
