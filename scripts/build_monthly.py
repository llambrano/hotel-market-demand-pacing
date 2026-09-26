#!/usr/bin/env python3
"""
Aggregate Amadeus Hospitality 'Destination Insights: Market Daily Occupancy'
exports to a single monthly table.

Reads every *.xlsx in a snapshot folder (raw data/<year>/<snapshot>/) and writes
one merged monthly CSV + XLSX. Layout: one row per market x month x segment.

Usage:  python3 build_monthly.py "raw data/2026/09 01" [output_dir]
"""
import sys, csv, glob, os, datetime, calendar
from collections import defaultdict
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

SEGMENTS = ["Totals", "Transient", "Group Sold", "Unsold Block", "Other"]
SEG_COL = {"Totals": 4, "Transient": 7, "Group Sold": 10, "Unsold Block": 13, "Other": 16}

# Market -> (region, country). The source workbooks carry neither, so the
# mapping lives beside the script rather than inside it: copy
# config/market_regions.example.json to config/market_regions.json and fill in
# the markets in your own export. Anything unlisted falls through to
# "Unassigned" rather than failing the run.
import json as _json, pathlib as _pathlib

_CONFIG = _pathlib.Path(__file__).resolve().parents[1] / "config" / "market_regions.json"
if not _CONFIG.exists():
    _CONFIG = _CONFIG.with_name("market_regions.example.json")
REGION = {k: tuple(v) for k, v in _json.loads(_CONFIG.read_text()).items()}


FIELDS = ["snapshot_date", "data_as_of_date", "market", "region", "country",
          "market_capacity_rooms", "stay_month", "stay_month_label",
          "calendar_days_in_month", "days_with_data", "is_partial_month",
          "demand_segment", "occupancy_pct", "pickup_vs_prior_week_pts",
          "stly_variance_pts", "est_room_nights_on_books",
          "est_room_nights_picked_up", "est_room_nights_vs_last_year"]

# CSV keeps the code names above; the XLSX uses these headers instead.
FRIENDLY = {
    "snapshot_date": "Snapshot Date",
    "data_as_of_date": "Data As Of",
    "market": "Market",
    "region": "Region",
    "country": "Country",
    "market_capacity_rooms": "Market Capacity (rooms)",
    "stay_month": "Stay Month",
    "stay_month_label": "Stay Month Label",
    "calendar_days_in_month": "Calendar Days in Month",
    "days_with_data": "Days with Data",
    "is_partial_month": "Partial Month?",
    "demand_segment": "Demand Segment",
    "occupancy_pct": "Occupancy %",
    "pickup_vs_prior_week_pts": "Pickup vs Prior Week (pts)",
    "stly_variance_pts": "STLY Variance (pts)",
    "est_room_nights_on_books": "Est. Room Nights On the Books",
    "est_room_nights_picked_up": "Est. Room Nights Picked Up",
    "est_room_nights_vs_last_year": "Est. Room Nights vs Last Year",
}


def num(v):
    return v if isinstance(v, (int, float)) else 0.0


def read_market(path, snapshot_date):
    """Return list of monthly records for one workbook."""
    ws = openpyxl.load_workbook(path, data_only=True)["Report"]
    market = ws["C7"].value
    as_of = ws["C11"].value
    capacity = ws["C15"].value
    region, country = REGION.get(market, ("Unassigned", "Unassigned"))

    # bucket daily rows by month
    buckets = defaultdict(list)
    for r in range(20, ws.max_row + 1):
        d = ws.cell(row=r, column=3).value
        if not isinstance(d, datetime.datetime):
            continue                       # skips Subtotal / Total rows
        vals = {}
        for seg, c in SEG_COL.items():
            vals[seg] = (num(ws.cell(row=r, column=c).value),      # Current (fraction)
                         num(ws.cell(row=r, column=c + 1).value),  # Wkly Pickup (pts)
                         num(ws.cell(row=r, column=c + 2).value))  # STLY Var (pts)
        buckets[(d.year, d.month)].append(vals)

    out = []
    for (y, m), days in sorted(buckets.items()):
        # Where the export stops, the remaining days come through as all-zero.
        # Only a TRAILING, CONTIGUOUS run of such days is the data horizon: a
        # zero day with booked days after it is a real zero, which small markets
        # genuinely have (in Cancun, 2,098 rooms, one booked room is 0.049%).
        # Treating every zero day as missing divided by too small a denominator
        # and inflated those markets' occupancy.
        def blank(d):
            return not any(abs(v) > 1e-12 for seg in SEGMENTS for v in d[seg])
        cut = len(days)
        while cut > 0 and blank(days[cut - 1]):
            cut -= 1
        live = days[:cut]
        n_live = len(live)
        n_cal = calendar.monthrange(y, m)[1]
        n_have = len(days)

        rows_for_month = {}
        for seg in SEGMENTS:
            if n_live:
                occ = sum(d[seg][0] for d in live) / n_live * 100.0
                pu = sum(d[seg][1] for d in live) / n_live
                st = sum(d[seg][2] for d in live) / n_live
            else:
                occ = pu = st = 0.0
            rows_for_month[seg] = (occ, pu, st)

        # derived: rooms actually sold = Transient + Group Sold
        t, g = rows_for_month["Transient"], rows_for_month["Group Sold"]
        rows_for_month["Sold (Transient + Group)"] = (t[0] + g[0], t[1] + g[1], t[2] + g[2])

        for seg in SEGMENTS + ["Sold (Transient + Group)"]:
            occ, pu, st = rows_for_month[seg]
            out.append({
                "snapshot_date": snapshot_date,
                "data_as_of_date": as_of.date().isoformat() if hasattr(as_of, "date") else str(as_of),
                "market": market,
                "region": region,
                "country": country,
                "market_capacity_rooms": capacity,
                "stay_month": f"{y:04d}-{m:02d}",
                "stay_month_label": f"{calendar.month_abbr[m]} {y}",
                "calendar_days_in_month": n_cal,
                "days_with_data": n_live,
                "is_partial_month": "Y" if n_live < n_cal else "N",
                "demand_segment": seg,
                "occupancy_pct": round(occ, 4),
                "pickup_vs_prior_week_pts": round(pu, 4),
                "stly_variance_pts": round(st, 4),
                # percentage points -> room nights: pts/100 x capacity x days
                "est_room_nights_on_books": round(occ / 100.0 * capacity * n_live),
                "est_room_nights_picked_up": round(pu / 100.0 * capacity * n_live),
                "est_room_nights_vs_last_year": round(st / 100.0 * capacity * n_live),
            })
    return out, market, n_have


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def write_xlsx(rows, path, snapshot_date, as_of):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Monthly"
    ws.append([FRIENDLY[f] for f in FIELDS])
    for r in rows:
        ws.append([r[k] for k in FIELDS])

    hdr_fill = PatternFill("solid", fgColor="2E2E2E")
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF", size=10)
        c.fill = hdr_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions

    fmt = {"occupancy_pct": "0.00", "pickup_vs_prior_week_pts": "0.00",
           "stly_variance_pts": "0.00", "est_room_nights_on_books": "#,##0",
           "est_room_nights_picked_up": "#,##0",
           "est_room_nights_vs_last_year": "#,##0",
           "market_capacity_rooms": "#,##0"}
    for name, f in fmt.items():
        col = FIELDS.index(name) + 1
        for row in range(2, ws.max_row + 1):
            ws.cell(row=row, column=col).number_format = f

    widths = {"snapshot_date": 14, "data_as_of_date": 12, "market": 20,
              "region": 19, "country": 21, "market_capacity_rooms": 21,
              "stay_month": 12, "stay_month_label": 17,
              "calendar_days_in_month": 21, "days_with_data": 15,
              "is_partial_month": 14, "demand_segment": 25,
              "occupancy_pct": 12, "pickup_vs_prior_week_pts": 25,
              "stly_variance_pts": 19, "est_room_nights_on_books": 27,
              "est_room_nights_picked_up": 26,
              "est_room_nights_vs_last_year": 28}
    for name, w in widths.items():
        ws.column_dimensions[get_column_letter(FIELDS.index(name) + 1)].width = w

    # README sheet
    rm = wb.create_sheet("README")
    notes = [
        ["Market Demand - merged monthly occupancy"],
        [""],
        ["Source", "MarketVision 'Destination Insights: Market Daily Occupancy' exports"],
        ["Snapshot (run) date", snapshot_date],
        ["As of date", as_of],
        ["Grain", "one row per market x month x segment"],
        [""],
        ["Occupancy %", "Average occupancy for the stay month, in PERCENT (source stores a 0-1 fraction; already scaled here)"],
        ["Pickup vs Prior Week (pts)", "How much this stay month moved since the snapshot 7 days earlier, in percentage points. It is the average across the month's stay dates of each date's 7-day pickup - a daily intensity figure, not the month's total movement. 'Weekly' is the comparison window, not the row's grain."],
        ["STLY Variance (pts)", "STLY = Same Time Last Year. Average daily variance vs the equivalent date last year (364-day offset), in percentage points."],
        ["Est. Room Nights On the Books", "Derived: Occupancy % / 100 x Market Capacity x Days with Data. Room nights on the books for this segment - for Totals that includes unsold block. Use this to weight markets, never a plain average of Occupancy %."],
        ["Est. Room Nights Picked Up", "Derived the same way from Pickup vs Prior Week. Reads directly: 'this market added N room nights for this stay month in the past week.' Sums correctly across markets; the points column does not."],
        ["Est. Room Nights vs Last Year", "Derived the same way from STLY Variance. Negative = behind last year by that many room nights."],
        ["Stay Month", "The month being stayed in, NOT the month the snapshot was taken."],
        ["Snapshot Date", "Each weekly export adds one snapshot_date. Stack them over time to get a booking-curve time series; one snapshot alone cannot show one."],
        [""],
        ["Segments", "Totals = Transient + Group Sold + Unsold Block + Other"],
        ["", "Unsold Block is group inventory NOT yet sold; it dominates far-future months."],
        ["Sold (Transient + Group)", "Derived. The honest demand measure for dates more than ~6 months out."],
        [""],
        ["days_with_data", "Days in the month with any non-zero value. Days that are zero across all segments are treated as missing, not as zero demand."],
        ["is_partial_month", "Y where days_with_data < days_in_month. Do not compare partial months to full ones."],
        [""],
        ["Caution", "Occupancy falls steadily across the booking window because distant dates are not booked yet. Compare stly_var_pts across months, not occ_pct."],
        ["region / country", "Assigned during processing, not present in the source files."],
        [""],
        ["Column names", "This sheet uses friendly headers. The companion CSV uses code-safe names:"],
        ["", " | ".join(f"{FRIENDLY[f]} = {f}" for f in FIELDS)],
    ]
    for row in notes:
        rm.append(row)
    rm["A1"].font = Font(bold=True, size=13)
    for row in range(3, rm.max_row + 1):
        rm.cell(row=row, column=1).font = Font(bold=True, size=10)
        rm.cell(row=row, column=2).alignment = Alignment(wrap_text=True, vertical="top")
    rm.column_dimensions["A"].width = 26
    rm.column_dimensions["B"].width = 105

    wb.save(path)


def main():
    src = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "processed"
    os.makedirs(out_dir, exist_ok=True)
    snapshot_date = os.path.basename(src.rstrip("/")).replace(" ", "-")
    year = os.path.basename(os.path.dirname(src.rstrip("/")))
    snapshot_date = f"{year}-{snapshot_date}"

    files = sorted(glob.glob(os.path.join(src, "*.xlsx")))
    all_rows, as_of = [], None
    for p in files:
        rows, market, n_days = read_market(p, snapshot_date)
        all_rows.extend(rows)
        as_of = rows[0]["data_as_of_date"]
        print(f"  {market:24} {n_days:4d} daily rows -> {len(rows):3d} monthly rows")

    all_rows.sort(key=lambda r: (r["region"], r["market"], r["stay_month"],
                                 r["demand_segment"]))
    tag = snapshot_date.replace("-", "_")
    csv_path = os.path.join(out_dir, f"market_demand_monthly_{tag}.csv")
    xlsx_path = os.path.join(out_dir, f"market_demand_monthly_{tag}.xlsx")
    write_csv(all_rows, csv_path)
    write_xlsx(all_rows, xlsx_path, snapshot_date, as_of)
    print(f"\n{len(files)} markets, {len(all_rows)} rows")
    print(f"  {csv_path}\n  {xlsx_path}")


if __name__ == "__main__":
    main()
