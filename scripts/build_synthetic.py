"""
Build the public, synthetic-data edition of the dashboard from the real one.

There is one source of truth for the page — dashboard.html — and this script
derives the shareable edition from it: same structure, same interactions, same
design system, every Amadeus figure replaced by synthetic data and every claim
about the source rewritten. Run it after any change to dashboard.html so the two
editions cannot drift.

    python3 synth.py data-synth.json
    python3 mksynth.py           ->  build-synth.html

The synthetic labelling is deliberately not a footnote. It sits in the masthead
band, the first words of the standfirst, the About strip, the source line and the
footnotes, so no screenshot of any part of the page can be mistaken for real
market intelligence.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

SYNTH_URL_NOTE = ("Every figure on this page is <b>synthetic</b> — generated to "
                  "behave like hotel booking data, not measured from it.")

EDITS = [

# ── title ────────────────────────────────────────────────────────────────────
("<title>Market Demand Pacing — Global Hotel Markets</title>",
 "<title>Market Demand Pacing — Synthetic Demonstration</title>"),

# ── masthead: a permanent marker in the band, above the as-of line ───────────
('<p class="eyebrow">Hotel demand analytics · work sample</p>',
 '<p class="eyebrow">Hotel demand analytics · work sample</p>\n'
 '        <p class="synthflag">Synthetic demonstration data — not real market figures</p>'),

('''        <p class="asof">On the books as of <b id="asof">—</b> · <b id="nmk">50</b> airport markets · <b id="nmonths">—</b> stay months</p>''',
 '''        <p class="asof">Modelled position as of <b id="asof">—</b> · <b id="nmk">50</b> markets · <b id="nmonths">—</b> stay months</p>'''),

# ── the flag's styling, and a matching band on the closing bar ──────────────
('.mh-contact{display:flex;',
 '''.synthflag{
  display:inline-block; margin:9px 0 0; padding:5px 11px;
  font-size:11px; font-weight:700; letter-spacing:.04em;
  color:#fff; background:var(--charcoal); border-left:3px solid var(--amber);
}
:root[data-theme="dark"] .synthflag{background:#3A332A}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) .synthflag{background:#3A332A}}
.mh-contact{display:flex;'''),

# ── standfirst: says what it is in the first clause ─────────────────────────
('''<p class="standfirst">Where fifty global airport hotel markets stand against the same point last year, read across every stay month still wholly ahead. Built from an Amadeus Hospitality market export, to show what a commercial team can see about softening demand while there is still time to price against it.</p>''',
 '''<p class="standfirst"><b>This is a demonstration built on synthetic data.</b> It shows how fifty hotel markets would be read against the same point last year, across every stay month still wholly ahead — the tool a commercial team uses to catch softening demand while there is still time to price against it. The method, the pipeline and the design are real; the numbers are modelled, so the page can be shared freely.</p>'''),

# ── About: "The data" column ────────────────────────────────────────────────
('''      <p>Fifty market workbooks from <b>Amadeus Hospitality — Destination
      Insights: Market Daily Occupancy</b>, one per airport comp set, each
      carrying every stay date to the export's horizon at a single as-of date.
      <a href="https://www.amadeus-hospitality.com/local-market-report/"
      target="_blank" rel="noopener">Amadeus supplies it on request</a>, at no
      cost, to anyone in the industry who asks.</p>''',
 '''      <p>Fifty markets × fourteen stay months × six demand segments at a single
      as-of date: the structure of an <b>Amadeus Hospitality — Destination
      Insights: Market Daily Occupancy</b> export, which is what the working
      version of this report reads.</p>
      <p><b>The figures on this page are generated, not measured.</b> They are
      modelled on how that export behaves; a real one was used to establish the
      structure and nothing else. Amadeus
      <a href="https://www.amadeus-hospitality.com/local-market-report/"
      target="_blank" rel="noopener">supplies the export on request</a>; its
      figures are Amadeus's and are not republished here. Swapping the synthetic
      file for the real one is a single command, and nothing else on the page
      changes.</p>'''),

# ── About: "How it was built" — the pipeline is real, this data is not ────
# Without this, "before it was allowed on the page" reads as a claim that THESE
# numbers were reconciled against Amadeus's subtotals.
('''      <p>Python (pandas, openpyxl) reduces the fifty workbooks to one monthly
      dataset — commercial teams plan in months, not days — and every monthly
      figure was reconciled against Amadeus's own subtotal rows before it was
      allowed on the page.</p>''',
 '''      <p>Python (pandas, openpyxl) reduces fifty daily workbooks to one monthly
      dataset — commercial teams plan in months, not days. On the working
      version, every monthly figure is reconciled against the export's own
      subtotal rows before it is allowed on the page.</p>
      <p><b>The numbers here went through that same pipeline, but they came out of
      a generator rather than an export.</b> Nothing on this page is a measurement
      of any real market.</p>'''),

# ── About: "How it was built" — name the generator as part of the work ──────
('''      <p>The result is a single self-contained HTML file. No server, no build
      step, nothing leaving the browser. Re-pointing it at the next export is
      one command, and the page relabels its own date ranges.</p>''',
 '''      <p>The result is a single self-contained HTML file. No server, no build
      step, nothing leaving the browser. Re-pointing it at another dataset is one
      command, and the page relabels its own date ranges from whatever it is
      given — which is how one page serves both the real export and this
      synthetic stand-in.</p>'''),

# ── the one hardcoded claim that depended on the real numbers ──────────────
('''<p class="psub">Occupancy on the books across every market in the current selection, weighted by market size, against the same point last year. The steep slope is the booking window, not falling demand. Across the whole portfolio the two lines sit close together — the pacing gap is easier to read month by month on the right, and market by market in the grid above.</p>''',
 '''<p class="psub">Occupancy on the books across every market in the current selection, weighted by market size, against the same point last year. The steep slope is the booking window, not falling demand. At portfolio level the two lines usually sit close together, which is the point: the gap that matters is easier to read month by month on the right, and market by market in the grid above.</p>'''),

# ── footnotes ───────────────────────────────────────────────────────────────
('''      <li><b>One snapshot.</b> Every figure here is the position at a single as-of date, read across future stay months. It is not a history: how a stay month built over successive weeks needs more than one snapshot, and each weekly export adds one.</li>''',
 '''      <li><b>The numbers are synthetic.</b> They are generated to reproduce the character of hotel booking data — a steep booking curve, seasonality, market-size spread, held-but-unsold group inventory growing with lead time, and a plausible spread of pacing against last year. Nothing here is a measurement of any real market, and none of it should be used to make a pricing decision. The caveats below are the ones that apply to the real report; they are on the page because reading them is part of the work.</li>
      <li><b>One snapshot.</b> Every figure here is the position at a single as-of date, read across future stay months. It is not a history: how a stay month built over successive weeks needs more than one snapshot, and each export adds one.</li>'''),

('''      <li><b>The current month is not demand.</b> At the as-of date part of it has already been stayed, so its occupancy mixes nights slept in with nights on the books. The default window therefore opens the month after — on this snapshot, leaving it in would have added +649k room nights of apparent gain that is simply time passing.</li>''',
 '''      <li><b>The current month is not demand.</b> At the as-of date part of it has already been stayed, so its occupancy mixes nights slept in with nights on the books. The default window therefore opens the month after. On the real export, leaving it in added more than half a million room nights of apparent gain against last year that was simply time passing — which is why the window boundary is computed rather than chosen.</li>'''),

('''      <li><b>The last month sits at the edge of the export.</b> Its final days come through empty for every market: that is where the file stops, not zero demand. Amadeus's own subtotal for that month also differs from this one, and occupancy for it is unreliable in the smallest markets. It sits outside the default window; the <i>All months</i> option includes it.</li>''',
 '''      <li><b>The last month sits at the edge of the file.</b> Its final days are empty for every market: that is where coverage stops, not zero demand, and averaging over a part-covered month is unsafe in the smallest markets. It sits outside the default window; the <i>All months</i> option includes it.</li>'''),

('''      <li><b>Markets are airport comp sets, not metros.</b> A 14,404-room "Los Angeles" and a 2,098-room "Cancún" are airport-scoped subsets; do not read them as whole cities.</li>''',
 '''      <li><b>Markets are comp sets, not whole cities.</b> In a real export each market is an airport-scoped set of competing hotels, which is why capacities range from a few thousand rooms to the high tens of thousands and why a small market's occupancy swings on a handful of bookings. The city names here are labels on synthetic markets, nothing more.</li>'''),

# ── source line ─────────────────────────────────────────────────────────────
('''    <p class="srcline">Source: <b>Amadeus Hospitality</b>, <i>Destination Insights — Market Daily Occupancy</i>; 50 market exports, data as of <b id="srcasof">—</b>, pulled <b id="srcrun">—</b>. Amadeus supplies this report <a href="https://www.amadeus-hospitality.com/local-market-report/" target="_blank" rel="noopener">on request at no cost</a>; the figures are Amadeus's and remain theirs. No employer or otherwise confidential data is used here. A red-to-blue colour scale is in the controls above for anyone who finds red and green hard to tell apart.</p>''',
 '''    <p class="srcline"><b>Synthetic data, generated for this demonstration</b> — modelled to the structure of a hotel market daily-occupancy export, dated <b id="srcasof">—</b> for realism. No real market figures appear on this page. The working version of the report runs on an <a href="https://www.amadeus-hospitality.com/local-market-report/" target="_blank" rel="noopener">Amadeus Hospitality market export</a>, supplied on request; those figures are Amadeus's and are not republished here, and no employer or otherwise confidential data is used. A red-to-blue colour scale is in the controls above for anyone who finds red and green hard to tell apart.</p>'''),
]


def main():
    html = (ROOT / "dashboard.html").read_text()
    for old, new in EDITS:
        n = html.count(old)
        if n != 1:
            raise SystemExit(f"mksynth: expected 1 match, found {n}:\n  {old[:110]}...")
        html = html.replace(old, new)

    data = (ROOT / "data" / "market_demand_synthetic.json").read_text()
    assert "__DATA__" in html
    out = html.replace("__DATA__", data)
    for token in ("__DATA__", "__LOGO"):
        assert token not in out, f"unfilled placeholder: {token}"
    # Naming the export this is modelled on is the point of the sample, so the
    # guard is on what must be PRESENT: the disclaimers, in all four places.
    for must in ("Synthetic demonstration data — not real market figures",
                 "This is a demonstration built on synthetic data",
                 "generated, not measured",
                 "No real market figures appear on this page"):
        assert must in out, f"missing the synthetic disclaimer: {must!r}"
    (ROOT / "synthetic-demo.html").write_text(out)
    print(f"built synthetic-demo.html  {len(out)/1024:.1f} KB  ({len(EDITS)} edits applied)")


if __name__ == "__main__":
    main()
