import pathlib

# every path is resolved from the repository root, so the script runs from
# anywhere: `python3 scripts/build_synthetic.py` or from inside scripts/
ROOT = pathlib.Path(__file__).resolve().parents[1]

html = (ROOT / "dashboard.html").read_text()
data = (ROOT / "data" / "market_demand_monthly.json").read_text()
assert "__DATA__" in html
out = html.replace("__DATA__", data)
for token in ("__DATA__", "__LOGO"):
    assert token not in out, f"unfilled placeholder: {token}"
(ROOT / "market-demand-pacing.html").write_text(out)
print(f"built {len(out)/1024:.1f} KB")
