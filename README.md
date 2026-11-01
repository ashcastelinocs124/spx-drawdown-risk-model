# SPX 5% Drawdown Risk Model

ARC Capital's model of the probability that the S&P 500 closes at least 5% below today's close within the next 20 trading days.

- **Final model:** random forest on 7 VIX and trend variables, trained on all history since 1990 and refit yearly.
- **Out-of-sample skill:** AUC 0.68 walk-forward 2000-2026 (0.5 = coin flip), Brier skill +8% over the base rate.
- **Use it as** a risk-regime thermometer for sizing and hedging, not as a timing signal.

| Path | What it is |
|---|---|
| `SKILL.md` | Instructions for an agent: how to run, read, and extend the model, and the rules for testing new variables |
| `scripts/spx_risk_model.py` | `fetch`, `evaluate`, `score` commands |
| `reference/findings.md` | Full research log: every variable and model tested, with numbers |
| `requirements.txt` | Python dependencies |
| `partisan-policy-gap/` | Separate study: does the Democrat–Republican policy gap move stocks, bonds or the VIX? (see its README) |

```bash
pip install -r requirements.txt
python3 scripts/spx_risk_model.py fetch
python3 scripts/spx_risk_model.py evaluate
python3 scripts/spx_risk_model.py score
```

Latest reading in the public data (22 Sep 2026): P = 8.6% (RF), 8.7% (LPM) vs a 15.5% base rate, 34th percentile of history: NORMAL/LOW.
