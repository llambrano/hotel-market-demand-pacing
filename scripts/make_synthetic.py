"""
Build a synthetic demonstration dataset in the dashboard's payload shape.

Why this exists
---------------
The real dashboard is built from an Amadeus Hospitality export. Amadeus supplies
that report on request rather than publishing it, and asserts rights over the
figures, so the real numbers are not republished. This script generates a dataset
with the same STRUCTURE and the same statistical CHARACTER — a steep booking
curve, seasonality, market-size spread, unsold block growing with lead time, a
plausible spread of pacing against last year — from a generic model of hotel
booking behaviour. No Amadeus value is used, copied or fitted to.

Market names are real cities, because geography is public and a portfolio page
has to be legible; the list is deliberately not the source export's coverage
list. Every capacity and every measure is invented. The page it feeds is labelled
as synthetic in the masthead, the standfirst, the source line and the footnotes.

Usage:  python3 synth.py data-synth.json
"""

import calendar
import json
import pathlib
import math
import random
import sys

SEED = 20260924
random.seed(SEED)

# ── market universe ───────────────────────────────────────────────────────────
# Real cities (public geography), deliberately not the source export's list:
# several of its markets are absent and several of these are not in it.
MARKETS = [
    # United States
    ("Atlanta", "United States", "United States"),
    ("Austin", "United States", "United States"),
    ("Boston", "United States", "United States"),
    ("Charlotte", "United States", "United States"),
    ("Chicago", "United States", "United States"),
    ("Dallas Fort Worth", "United States", "United States"),
    ("Denver", "United States", "United States"),
    ("Detroit", "United States", "United States"),
    ("Houston", "United States", "United States"),
    ("Las Vegas", "United States", "United States"),
    ("Los Angeles", "United States", "United States"),
    ("Miami", "United States", "United States"),
    ("Minneapolis", "United States", "United States"),
    ("Nashville", "United States", "United States"),
    ("New Orleans", "United States", "United States"),
    ("New York City", "United States", "United States"),
    ("Orlando", "United States", "United States"),
    ("Philadelphia", "United States", "United States"),
    ("Phoenix", "United States", "United States"),
    ("Portland", "United States", "United States"),
    ("San Diego", "United States", "United States"),
    ("San Francisco", "United States", "United States"),
    ("Seattle", "United States", "United States"),
    ("Washington DC", "United States", "United States"),
    # Canada
    ("Calgary", "Canada", "Canada"),
    ("Montreal", "Canada", "Canada"),
    ("Ottawa", "Canada", "Canada"),
    ("Toronto", "Canada", "Canada"),
    ("Vancouver", "Canada", "Canada"),
    # Europe
    ("Amsterdam", "Europe", "Netherlands"),
    ("Barcelona", "Europe", "Spain"),
    ("Berlin", "Europe", "Germany"),
    ("Dublin", "Europe", "Ireland"),
    ("Frankfurt", "Europe", "Germany"),
    ("Lisbon", "Europe", "Portugal"),
    ("London", "Europe", "United Kingdom"),
    ("Milan", "Europe", "Italy"),
    ("Paris", "Europe", "France"),
    ("Rome", "Europe", "Italy"),
    ("Zurich", "Europe", "Switzerland"),
    # Latin America & Caribbean
    ("Bogota", "Latin America & Caribbean", "Colombia"),
    ("Cancun", "Latin America & Caribbean", "Mexico"),
    ("Mexico City", "Latin America & Caribbean", "Mexico"),
    ("Panama City", "Latin America & Caribbean", "Panama"),
    ("Punta Cana", "Latin America & Caribbean", "Dominican Republic"),
    ("Sao Paulo", "Latin America & Caribbean", "Brazil"),
    # Asia Pacific
    ("Bangkok", "Asia Pacific", "Thailand"),
    ("Hong Kong", "Asia Pacific", "Hong Kong SAR"),
    ("Melbourne", "Asia Pacific", "Australia"),
    ("Osaka", "Asia Pacific", "Japan"),
    ("Seoul", "Asia Pacific", "South Korea"),
    ("Singapore", "Asia Pacific", "Singapore"),
    ("Sydney", "Asia Pacific", "Australia"),
    ("Tokyo", "Asia Pacific", "Japan"),
    # Middle East
    ("Doha", "Middle East", "Qatar"),
    ("Dubai", "Middle East", "United Arab Emirates"),
    ("Riyadh", "Middle East", "Saudi Arabia"),
]
# trim the two largest regions so the total stays at 50 with a usable spread
for _drop in ("Detroit", "Portland", "New Orleans", "Charlotte", "Ottawa",
              "Frankfurt", "Milan"):
    MARKETS = [m for m in MARKETS if m[0] != _drop]

# Region character: size multiplier, booking-curve steepness nudge, pacing bias
# in relative terms (a soft region books a little behind last year at every lead).
REGION = {
    "United States":              dict(size=1.00, steep=1.00, bias=+0.008),
    "Canada":                     dict(size=0.62, steep=0.96, bias=+0.020),
    # Europe is the soft region in this synthetic portfolio: the page has to have
    # a problem to find, or it demonstrates nothing. Chosen so the shape of the
    # story does not echo the real export's.
    "Europe":                     dict(size=0.85, steep=0.92, bias=-0.105),
    "Latin America & Caribbean":  dict(size=0.58, steep=1.06, bias=+0.045),
    "Asia Pacific":              dict(size=1.05, steep=1.10, bias=-0.035),
    "Middle East":                dict(size=1.10, steep=1.14, bias=+0.025),
}

SEGMENTS = ["Transient", "Group Sold", "Unsold Block", "Other"]
SEGS_OUT = ["Sold", "Totals", "Transient", "Group Sold", "Unsold Block", "Other"]

AS_OF = "2026-09-13"
SNAPSHOT = "2026-09-15"
MONTHS = ["2026-08", "2026-09", "2026-10", "2026-11", "2026-12",
          "2027-01", "2027-02", "2027-03", "2027-04", "2027-05",
          "2027-06", "2027-07", "2027-08", "2027-09"]
# where the export's coverage stops inside the final month
HORIZON_DAYS = 26


def label(m):
    y, mo = int(m[:4]), int(m[5:])
    return f"{calendar.month_abbr[mo]} {y}"


def seasonality(month_num, coastal):
    """A plain two-term seasonal shape: summer peak, a deeper winter trough for
    leisure-weighted markets, and a December dip for business-weighted ones."""
    phase = (month_num - 7) / 12 * 2 * math.pi
    summer = 0.16 * math.cos(phase)
    if coastal:                       # leisure: strong winter sun demand too
        winter = 0.12 * math.cos((month_num - 2) / 12 * 2 * math.pi)
        dec = 0.0
    else:                             # business: December falls away
        winter = 0.0
        dec = -0.18 if month_num == 12 else 0.0
    return max(0.55, 1.0 + summer + winter + dec)


def build():
    # elapsed months from the as-of month; index 0 (Aug 2026) is already closed
    asof_i = MONTHS.index(AS_OF[:7])
    markets = []

    for name, region, country in MARKETS:
        rc = REGION[region]
        coastal = name in {
            "Cancun", "Punta Cana", "Miami", "Orlando", "San Diego", "Las Vegas",
            "Barcelona", "Lisbon", "Rome", "Milan", "Panama City", "Sydney",
            "Phoenix", "New Orleans",
        }
        # size: lognormal spread, so the portfolio has a few very large markets
        cap = random.lognormvariate(math.log(22000 * rc["size"]), 0.62)
        cap = int(min(102000, max(2400, round(cap / 50) * 50)))

        strength = random.lognormvariate(0, 0.30)          # market booking pace
        steep = rc["steep"] * random.uniform(0.92, 1.08)   # curve decay rate
        # this market's own pacing bias against last year, in relative terms
        bias = rc["bias"] + random.gauss(0, 0.075)
        group_share = random.uniform(0.10, 0.34)           # group vs transient
        block_scale = random.uniform(0.6, 1.5)             # how much held block

        days, cal, vals = [], [], {s: [] for s in SEGS_OUT}

        for i, m in enumerate(MONTHS):
            mo = int(m[5:])
            n_cal = calendar.monthrange(int(m[:4]), mo)[1]
            n_live = HORIZON_DAYS if i == len(MONTHS) - 1 else n_cal
            cal.append(n_cal)
            days.append(n_live)

            lead = i - asof_i            # months ahead of the as-of month
            if lead < 0:                 # closed month: nearly fully actualised
                sold = 74.0 * strength * seasonality(mo, coastal) * random.uniform(.95, 1.05)
            elif lead == 0:              # current month, part stayed part booked
                sold = 46.0 * strength * seasonality(mo, coastal) * random.uniform(.95, 1.05)
            else:
                # the booking curve: steep exponential decay with lead time
                sold = (31.0 * math.exp(-0.62 * steep * (lead - 1)) + 0.22) \
                       * strength * seasonality(mo, coastal) * random.uniform(.90, 1.10)
            sold = min(88.0, max(0.03, sold))

            group = sold * group_share * random.uniform(.85, 1.15)
            transient = max(0.01, sold - group)

            # held-but-unsold group inventory: negligible up close, dominant far out
            block = block_scale * 14.0 * (1 - math.exp(-0.45 * max(0, lead))) \
                    * random.uniform(.8, 1.2)
            if lead <= 0:
                block = random.uniform(0.02, 0.4)
            other = max(0.0, sold * random.uniform(0.02, 0.09) + random.uniform(0, 0.4))

            totals = transient + group + block + other
            if totals > 95.0:                    # keep occupancy physical
                k = 95.0 / totals
                transient, group, block, other = (transient * k, group * k, block * k, other * k)
                totals = 95.0

            # pacing against the same point last year, as a relative change on the
            # level held — so near months move in whole points, far months in tenths
            rel = bias + random.gauss(0, 0.085)
            pu_rel = random.uniform(0.04, 0.16) if lead > 0 else random.uniform(0, 0.05)

            def triple(level, scale=1.0):
                return [round(level, 2),
                        round(level * pu_rel * scale, 2),
                        round(level * rel * scale, 2)]

            vals["Transient"].append(triple(transient))
            vals["Group Sold"].append(triple(group))
            vals["Sold"].append(triple(transient + group))
            vals["Unsold Block"].append(triple(block, 0.45))
            vals["Other"].append(triple(other, 0.6))
            parts = [vals[s][-1] for s in SEGMENTS]
            vals["Totals"].append([round(sum(p[0] for p in parts), 2),
                                   round(sum(p[1] for p in parts), 2),
                                   round(sum(p[2] for p in parts), 2)])

        markets.append({"n": name, "r": region, "c": country, "cap": cap,
                        "days": days, "cal": cal, "v": vals})

    markets.sort(key=lambda m: m["n"])
    return {"asOf": AS_OF, "snapshot": SNAPSHOT, "months": MONTHS,
            "labels": [label(m) for m in MONTHS], "segs": SEGS_OUT,
            "markets": markets, "synthetic": True}


if __name__ == "__main__":
    data = build()
    root = pathlib.Path(__file__).resolve().parents[1]
    out = sys.argv[1] if len(sys.argv) > 1 else str(root / "data" / "market_demand_synthetic.json")
    json.dump(data, open(out, "w"), separators=(",", ":"))
    print(f"{len(data['markets'])} markets, {len(data['months'])} months -> {out}")
