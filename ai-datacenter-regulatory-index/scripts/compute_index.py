"""Merge researcher outputs, validate against the rubric, compute index scores.
Usage (from the study folder):
  python3 scripts/compute_index.py evidence/raw evidence/index_evidence.json outputs/index_scores.csv
Reads the per-batch researcher files, validates every row against RUBRIC.md
(snapping levels to allowed values), writes the merged evidence file, and writes
component and composite scores per state.
"""
import json, sys, glob, os, re
from collections import defaultdict

ALLOWED = {
 "pw_tariff":[0,40,70,100],"pw_min_commit":[0,50,100],"pw_collateral":[0,50,100],"pw_cost_alloc":[0,50,100],
 "pm_moratorium":[0,25,60,100],"pm_siting":[0,50,100],"pm_threshold":[0,50,100],"pm_timeline":[0,50,100],
 "tx_sales":[0,30,60,80,100],"tx_property":[0,30,60,80,100],"tx_conditions":[0,50,100],
 "ev_water":[0,50,100],"ev_emissions":[0,50,100],"ev_review":[0,50,100],
 "op_backup":[0,50,100],"op_labor":[0,50,100],"op_reporting":[0,50,100],"op_restrictions":[0,50,100],
 "ad_uncertainty":[0,50,100],"ad_backlog":[0,50,100],
}
COMP = {"pw":("Power",0.30),"pm":("Permitting",0.25),"tx":("Tax",0.15),"ev":("Environment",0.15),"op":("Operating rules",0.10),"ad":("Administration",0.05)}
LABEL = {
 "pw_tariff":"Large-load tariff","pw_min_commit":"Minimum demand / contract terms","pw_collateral":"Deposits & collateral","pw_cost_alloc":"Cost-allocation mandate",
 "pm_moratorium":"Moratorium status","pm_siting":"Siting regime","pm_threshold":"Size thresholds","pm_timeline":"Permit timelines",
 "tx_sales":"Sales-tax treatment","tx_property":"Property-tax treatment","tx_conditions":"Incentive conditions",
 "ev_water":"Water rules","ev_emissions":"Backup-generator emissions","ev_review":"Environmental review",
 "op_backup":"On-site generation / curtailment","op_labor":"Labor conditions","op_reporting":"Operating reporting","op_restrictions":"Noise / setback rules",
 "ad_uncertainty":"Legal & policy uncertainty","ad_backlog":"Queue / agency backlog",
}
STATES = "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()

def snap(ind, v):
    if v is None: return None
    try: v = float(v)
    except Exception: return None
    opts = ALLOWED[ind]
    return min(opts, key=lambda o: abs(o - v))

def main(out_dir, ev_out, scores_out=None):
    rows, problems = [], []
    for f in sorted(glob.glob(os.path.join(out_dir, "*.json"))):
        try: data = json.load(open(f))
        except Exception as e: problems.append(f"{f}: unreadable ({e})"); continue
        for r in data: r["_file"] = os.path.basename(f); rows.append(r)
    seen = {}
    for r in rows:
        st = str(r.get("state","")).upper().strip(); ind = str(r.get("indicator","")).strip()
        if st not in STATES or ind not in ALLOWED: problems.append(f"bad key {st}/{ind} in {r['_file']}"); continue
        lv = snap(ind, r.get("level"))
        if r.get("level") is not None and lv != r.get("level"): problems.append(f"{st}/{ind}: level {r.get('level')} snapped to {lv}")
        url = str(r.get("source_url") or "").strip()
        if lv is not None and not re.match(r"^https?://", url):
            problems.append(f"{st}/{ind}: no source url, left unscored"); lv = None
        seen[(st, ind)] = dict(id=f"{st}-{ind}", state=st, indicator=ind, indicator_label=LABEL[ind], component=COMP[ind[:2]][0],
            weight=COMP[ind[:2]][1], level=lv, evidence=str(r.get("evidence") or "").strip(), source_url=url,
            source_date=str(r.get("source_date") or ""), confidence=str(r.get("confidence") or "").lower(), pending=str(r.get("pending") or "").strip())
    missing = [(s,i) for s in STATES for i in ALLOWED if (s,i) not in seen]
    ev = [seen[k] for k in sorted(seen)]
    json.dump(ev, open(ev_out, "w"), ensure_ascii=False, indent=1)
    # scores
    by = defaultdict(lambda: defaultdict(list))
    for r in ev:
        if r["level"] is not None: by[r["state"]][r["component"]].append(r["level"])
    scores = []
    for s in STATES:
        comps = {name: (sum(v)/len(v) if (v := by[s][name]) else None) for name,_ in COMP.values()}
        tot = sum(w * (comps[n] or 0) for n,w in COMP.values())
        scores.append((s, round(tot,1), {k: (round(v) if v is not None else None) for k,v in comps.items()}))
    scores.sort(key=lambda x: -x[1])
    if scores_out:
        import csv
        with open(scores_out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["rank", "state", "composite"] + [n for n,_ in COMP.values()])
            for i,(s_,t,c) in enumerate(scores, 1):
                w.writerow([i, s_, t] + [c[n] for n,_ in COMP.values()])
    print(f"rows={len(ev)} states_with_rows={len({r['state'] for r in ev})} missing={len(missing)} problems={len(problems)}")
    for p in problems[:40]: print("  !", p)
    if missing: print("  missing sample:", missing[:15])
    for s,t,c in scores: print(f"{s} {t:5.1f}  " + " ".join(f"{k[:4]}={v}" for k,v in c.items()))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
