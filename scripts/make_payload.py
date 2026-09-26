import csv, json, sys, collections

src = sys.argv[1]; out = sys.argv[2]
rows = list(csv.DictReader(open(src)))

months = sorted({r["stay_month"] for r in rows})
labels = {}
for r in rows: labels[r["stay_month"]] = r["stay_month_label"]
labels = [labels[m] for m in months]

SEGS = ["Sold","Totals","Transient","Group Sold","Unsold Block","Other"]
# the build names the derived segment in full; the dashboard calls it "Sold"
RENAME = {"Sold (Transient + Group)":"Sold"}
mi = {m:i for i,m in enumerate(months)}

mk = collections.OrderedDict()
for r in rows:
    n = r["market"]
    if n not in mk:
        mk[n] = {"n":n, "r":r["region"], "c":r["country"],
                 "cap":int(float(r["market_capacity_rooms"])),
                 "days":[0]*len(months), "cal":[0]*len(months),
                 "v":{s:[None]*len(months) for s in SEGS}}
    m = mk[n]; i = mi[r["stay_month"]]
    m["days"][i] = int(float(r["days_with_data"]))
    m["cal"][i]  = int(float(r["calendar_days_in_month"]))
    seg = RENAME.get(r["demand_segment"], r["demand_segment"])
    if seg in m["v"]:
        m["v"][seg][i] = [round(float(r["occupancy_pct"]),2),
                          round(float(r["pickup_vs_prior_week_pts"]),2),
                          round(float(r["stly_variance_pts"]),2)]

markets = sorted(mk.values(), key=lambda m: m["n"])
for m in markets:
    for s in SEGS:
        for i,v in enumerate(m["v"][s]):
            if v is None: m["v"][s][i] = [0.0,0.0,0.0]

data = {"asOf":rows[0]["data_as_of_date"], "snapshot":rows[0]["snapshot_date"],
        "months":months, "labels":labels, "segs":SEGS, "markets":markets}
json.dump(data, open(out,"w"), separators=(",",":"))
print(f"{len(markets)} markets, {len(months)} months -> {out}")
