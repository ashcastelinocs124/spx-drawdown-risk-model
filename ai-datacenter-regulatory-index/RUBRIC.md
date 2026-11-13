# AI Data Center Regulatory Index — scoring rubric (v1, Nov 2026)

Higher = MORE RESTRICTIVE / harder or costlier to build and run a large AI data center in the state.
Every indicator is scored on 0–100 using ONLY the levels listed (pick the closest level). Score what is IN EFFECT or formally pending as of the research date; note pending items.

Composite = 0.30·Power + 0.25·Permitting + 0.15·Tax + 0.15·Environment + 0.10·Operating + 0.05·Administration.
Component score = mean of its indicators that are not null.

## Recording rules
- One row per state × indicator. All 20 indicators must appear for each state (Power 4, Permitting 4, Tax 3, Environment 3, Operating 4, Administration 2).
- `level`: one of the allowed values below. Use `null` ONLY if you searched and genuinely cannot tell (not for "no rule exists" — absence of a rule scores the "none" level, with confidence "low" if you found no explicit confirmation).
- `evidence`: one factual sentence in your own words (what the rule is, who adopted it, when). Name the statute, docket, order or tariff where possible.
- `source_url`: a real URL you opened or saw in results (prefer PUC dockets/orders, statutes, agency pages, governor releases, NCSL, then reputable news/trade press). Never invent URLs.
- `source_date`: YYYY-MM-DD or YYYY-MM of the source.
- `confidence`: high (primary document), medium (reputable secondary), low (inferred from absence / thin sourcing).
- `pending`: short note if a bill, docket, pledge or rule could change the level soon, else "".

## POWER (30%)
- `pw_tariff` — Large-load / data-center tariff or rate class (major utilities in the state).
  0 none and no proceeding · 40 docket open or bill pending · 70 approved for some utilities or voluntary · 100 approved/mandated for the state's major utilities
- `pw_min_commit` — Minimum demand / take-or-pay / minimum contract term / exit fees for large loads.
  0 none · 50 moderate (e.g., <80% minimum bill, ≤10-yr term) · 100 strong (≥80% minimum bill or ≥12-yr term or large exit fees)
- `pw_collateral` — Interconnection/service deposits, collateral or credit requirements specific to large loads.
  0 none specific · 50 moderate · 100 large (e.g., $/MW deposits, full credit backing of upgrade costs)
- `pw_cost_alloc` — Law or PUC order making data centers bear their grid/generation costs, or bring their own power (ratepayer-protection mandates).
  0 none · 50 proposed, voluntary, or limited · 100 enacted and mandatory

## PERMITTING (25%)
- `pm_moratorium` — Moratorium status on new data centers.
  0 none · 25 local moratoria in one or more jurisdictions · 60 statewide pause proposed by governor(-elect)/legislature, or partial state pause (state land, certain permits, tax-break-only pause does NOT count here) · 100 statewide moratorium in effect
- `pm_siting` — Siting/approval regime.
  0 local zoning only (often by-right, or state preemption of local limits) · 50 state review/registration, or mandated local approval/public hearing · 100 state siting-board/certificate required
- `pm_threshold` — Size (MW/acreage) thresholds that trigger extra state review.
  0 none · 50 threshold ≥100 MW · 100 threshold <100 MW
- `pm_timeline` — Documented permitting/approval timelines.
  0 expedited/fast-track program · 50 typical/no special program · 100 documented long delays (>18 months) or permit backlog

## TAX (15%)
- `tx_sales` — Sales/use tax treatment of data center equipment.
  0 active exemption with low thresholds, OR state has no general sales tax · 30 active exemption with high thresholds/strict conditions · 60 no data-center exemption program · 80 exemption suspended/paused for new projects · 100 repealed
- `tx_property` — Property-tax abatement/exemption availability for data centers.
  0 broadly available (state program or routine local abatements) · 30 available with strict conditions · 60 none · 80 suspended/restricted · 100 prohibited
- `tx_conditions` — Clawbacks/conditions attached to incentives (jobs, wages, efficiency, water, clean energy).
  0 none/no incentives · 50 some conditions · 100 strict conditions with clawbacks

## ENVIRONMENT (15%)
- `ev_water` — Water withdrawal limits / reporting for data centers.
  0 none · 50 reporting or disclosure required, or water-use review · 100 limits, closed-loop mandates, or withdrawal caps
- `ev_emissions` — Air-permit rules for backup generators/on-site generation beyond federal baseline.
  0 baseline/general permits · 50 state-specific limits or run-hour conditions · 100 strict (cumulative review, tight run-hour caps, Tier 4 mandates)
- `ev_review` — State environmental review applied to data centers.
  0 none · 50 general state review law applies (SEPA/CEQA/Act 250-type) · 100 data-center-specific impact review

## OPERATING RULES (10%)
- `op_backup` — On-site/behind-the-meter generation rules, curtailment or demand-response obligations.
  0 none · 50 voluntary/limited · 100 mandatory curtailment/demand response or limits on on-site generation
- `op_labor` — Labor conditions (prevailing wage, PLA, local hire).
  0 none · 50 tied to incentives · 100 statutory mandate
- `op_reporting` — Ongoing operating reporting (energy, water, jobs, emissions).
  0 none · 50 incentive-linked or limited · 100 statutory public reporting
- `op_restrictions` — Statewide noise/setback/other operating restrictions.
  0 none · 50 some · 100 strict

## ADMINISTRATION (5%)
- `ad_uncertainty` — Legal/policy uncertainty.
  0 stable · 50 major rules/bills pending, or new governor(-elect) pledging changes · 100 active litigation, rules in flux, or conflicting directives
- `ad_backlog` — Interconnection-queue or agency backlog affecting data centers.
  0 none known · 50 moderate · 100 severe/documented

## Output format (JSON array written to the file you are told)
[{"state":"TX","indicator":"pw_tariff","level":70,"evidence":"...","source_url":"https://...","source_date":"2026-06","confidence":"medium","pending":""}, ...]
