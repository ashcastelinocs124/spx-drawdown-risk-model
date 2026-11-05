# AI Data Center Regulatory Index

How hard is it to build and run a large AI data center in each US state? This study scores all 50 states from **0** (fewest rules and costs) to **100** (most restrictive) on six weighted components, using 1,000 sourced indicator rows researched in November 2026. It sits alongside data on the 2026 Senate and governor winners' data center stances, announced company investment by state, and national polling.

**Bottom line (Nov 4, 2026):** Texas (64.0), Kansas (60.3), Minnesota (59.7), California (56.3) and New Jersey (54.6) are the most restrictive; Alaska (8.9), Rhode Island (11.9), Connecticut (12.4), Hawaii (14.4) and Vermont (16.0) the least. The national median is 37.0 (36.95). No state has a statewide moratorium in effect; 10 have one proposed or a partial state pause. Power rules drive most of the restriction: 33 states have an approved large-load tariff and 21 a mandatory rule making data centers bear their own grid costs.

## Method

| Component | Weight | Indicators |
|---|---|---|
| Power | 30% | Large-load tariff · minimum demand / contract terms · deposits & collateral · cost-allocation mandate |
| Permitting | 25% | Moratorium status · siting regime · size thresholds · permit timelines |
| Tax | 15% | Sales-tax treatment · property-tax treatment · incentive conditions |
| Environment | 15% | Water rules · backup-generator emissions · environmental review |
| Operating rules | 10% | On-site generation / curtailment · labor conditions · operating reporting · noise / setback rules |
| Administration | 5% | Legal & policy uncertainty · queue / agency backlog |

1. **Indicators:** each of the 20 indicators takes only the levels defined in [`RUBRIC.md`](RUBRIC.md) (e.g. moratorium 0 none / 25 local / 60 statewide proposed or partial / 100 statewide in effect). Every row records the level, one sentence of evidence, a source URL and date, a confidence rating and any pending change.
2. **Components:** the simple mean of a component's scored indicators.
3. **Composite:** 0.30·Power + 0.25·Permitting + 0.15·Tax + 0.15·Environment + 0.10·Operating + 0.05·Administration.

Worked example, Texas: Power (100, 50, 100, 100 → 87.5) × 0.30 = 26.3; Permitting (60, 0, 100, 100 → 65.0) × 0.25 = 16.3; Tax (30, 0, 50 → 26.7) × 0.15 = 4.0; Environment (50, 0, 100 → 50.0) × 0.15 = 7.5; Operating (100, 50, 50, 0 → 50.0) × 0.10 = 5.0; Administration (100, 100 → 100) × 0.05 = 5.0. Composite = **64.0**.

The weights were set by the author, not estimated from data. The ordering reflects that power and permits usually decide whether and when a project can be built, while tax and environmental rules mainly change cost. A sensitivity check of the ranking under alternative weights has not been run yet.

## Reproduce

```bash
cd ai-datacenter-regulatory-index
python3 scripts/compute_index.py evidence/raw evidence/index_evidence.json outputs/index_scores.csv
```

This merges the ten researcher batches in `evidence/raw/`, validates each row against the rubric (snapping to allowed levels, leaving rows without a source URL unscored), writes `evidence/index_evidence.json` and `outputs/index_scores.csv`, and prints the ranking.

## Files

| Path | What it is |
|---|---|
| `RUBRIC.md` | Indicator definitions and allowed levels |
| `scripts/compute_index.py` | Merge, validate and score |
| `evidence/raw/g01.json` – `g10.json` | Researcher output, five states per batch |
| `evidence/index_evidence.json` | Merged 1,000-row evidence file the dashboard reads |
| `outputs/index_scores.csv` | Composite and component scores by state |
| `evidence/senate_winners.json` | 2026 Senate winners with data center and AI stances and sources |
| `evidence/governors.json` | 2026 governor winners with stances and sources |
| `evidence/dc_investments.json` | Announced data center investment by company, state and site (Jan 2024 – Nov 2026), with counted / not-counted reasons |
| `evidence/polls.json` | National poll figures on data center sentiment, with pollster, dates and links |
| `dashboard/index.html` | Page source for the interactive dashboard (runs inside the Claude Dashboard artifact, which supplies the `dash` data API and d3) |

## Limits

- **Confidence:** 49% of rows come from primary documents or reputable secondary sources. The rest are low confidence, mostly "no rule found" rows scored at the unrestricted level, so a low score partly reflects less evidence found, not only fewer rules.
- **Search limits:** most research batches hit a search budget near the end; Environment, Operating rules and backlog indicators are the thinnest.
- **Unscored rows:** 14 rows are null (e.g. California and Colorado backup-generator rules, several property-tax and backlog rows) and are left out of component averages.
- **Pledges:** governor-elect pledges count only as "proposed" levels, never as rules in effect.
- **Equal indicator weights within a component:** a strict minimum-demand rule counts the same as a collateral rule.

## Refresh

A scheduled task re-checks Power and Permitting for all 50 states daily and the other four components weekly, updating only rows with new, sourced developments. The live evidence file is the dashboard's dataset; this folder is the Nov 4, 2026 snapshot.
