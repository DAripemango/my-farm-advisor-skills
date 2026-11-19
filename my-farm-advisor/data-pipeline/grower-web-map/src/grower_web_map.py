#!/usr/bin/env python3
"""Generate a lightweight grower-level interactive field map.

One self-contained HTML file per grower: every farm and field boundary the
pipeline downloaded, drawn over Esri World Imagery with Leaflet, plus a
clickable field list.  No rasters or imagery are embedded -- the payload is
only the boundary GeoJSON, so the output stays small and opens from ``file://``.

Data contract (all under ``$DATA_PIPELINE_DATA_ROOT/data-pipeline``)::

    growers/<grower>/grower.json
    growers/<grower>/farms/<farm>/farm.json
    growers/<grower>/farms/<farm>/boundary/field_boundaries.geojson

The boundary GeoJSON is expected in EPSG:4326 / OGC:CRS84 (what the pipeline
writes).  Other CRS values are refused rather than silently mis-plotted.

This module uses only the Python standard library so it can run from either
the checkout or the runtime script copy.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import sys
from pathlib import Path
from string import Template
from typing import Any

PALETTE = (
    "#2563eb",  # blue
    "#16a34a",  # green
    "#dc2626",  # red
    "#9333ea",  # purple
    "#d97706",  # amber
    "#0891b2",  # cyan
    "#be185d",  # pink
    "#4d7c0f",  # olive
)

_ACCEPTED_CRS = ("4326", "CRS84", "WGS84", "WGS 84")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _round_coords(value: Any, digits: int = 6) -> Any:
    """Round nested GeoJSON coordinates (~0.1 m) to keep the payload compact."""
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], (int, float)):
            return [round(float(item), digits) for item in value]
        return [_round_coords(item, digits) for item in value]
    return value


def _check_crs(payload: dict[str, Any], source: Path) -> None:
    crs = payload.get("crs")
    if not crs:
        return  # GeoJSON's default is WGS84
    name = str(crs.get("properties", {}).get("name", "")).upper()
    if name and not any(token in name for token in _ACCEPTED_CRS):
        raise ValueError(
            f"{source} declares CRS {name!r}; this generator only accepts "
            "EPSG:4326 / OGC:CRS84 boundary GeoJSON"
        )


def _feature_geometry(feature: dict[str, Any], source: Path) -> dict[str, Any]:
    geometry = feature.get("geometry") or {}
    if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError(
            f"{source} contains a {geometry.get('type')!r} feature; "
            "field boundaries must be Polygon or MultiPolygon"
        )
    return {
        "type": geometry["type"],
        "coordinates": _round_coords(geometry.get("coordinates", [])),
    }


def _field_metadata(
    source_props: dict[str, Any],
    *,
    grower_name: str,
    grower_slug: str,
    farm_name: str,
    farm_slug: str,
    farm_color: str,
    index: int,
) -> dict[str, Any]:
    field_id = str(
        source_props.get("field_id")
        or source_props.get("field_slug")
        or f"field-{index + 1}"
    )
    field_name = str(
        source_props.get("field_name")
        or source_props.get("name")
        or field_id
    )
    return {
        "key": f"{grower_slug}/{farm_slug}/{field_id}",
        "farm_key": f"{grower_slug}/{farm_slug}",
        "grower": grower_name,
        "grower_slug": grower_slug,
        "farm": farm_name,
        "farm_slug": farm_slug,
        "field": field_name,
        "field_id": field_id,
        "area_acres": _as_float(source_props.get("area_acres")),
        "area_ha": _as_float(
            source_props.get("area_ha_est") or source_props.get("area_ha")
        ),
        "crop": source_props.get("crop"),
        "county": source_props.get("county"),
        "state": source_props.get("state"),
        "year": source_props.get("year"),
        "source": source_props.get("source"),
        "farm_color": farm_color,
    }


def _load_grower(grower_dir: Path, color_offset: int = 0) -> dict[str, Any]:
    grower_slug = grower_dir.name
    grower_file = grower_dir / "grower.json"
    grower_meta = _read_json(grower_file) if grower_file.exists() else {}
    grower_name = str(grower_meta.get("display_name") or grower_slug)

    farms_root = grower_dir / "farms"
    farm_dirs = sorted(path for path in farms_root.glob("*") if path.is_dir())
    if not farm_dirs:
        raise ValueError(f"no farms found under {farms_root}")

    features: list[dict[str, Any]] = []
    farms: list[dict[str, Any]] = []
    for farm_index, farm_dir in enumerate(farm_dirs):
        farm_slug = farm_dir.name
        farm_file = farm_dir / "farm.json"
        farm_meta = _read_json(farm_file) if farm_file.exists() else {}
        farm_name = str(farm_meta.get("display_name") or farm_slug)
        boundary_file = farm_dir / "boundary" / "field_boundaries.geojson"
        if not boundary_file.exists():
            print(f"  warn: {boundary_file} is missing; skipping {farm_slug}", file=sys.stderr)
            continue

        payload = _read_json(boundary_file)
        _check_crs(payload, boundary_file)
        raw_features = payload.get("features") or []
        if not raw_features:
            print(f"  warn: {boundary_file} has no features; skipping {farm_slug}", file=sys.stderr)
            continue

        color = PALETTE[(color_offset + farm_index) % len(PALETTE)]
        farms.append(
            {
                "slug": farm_slug,
                "name": farm_name,
                "fields": len(raw_features),
                "boundary": str(boundary_file),
                "color": color,
            }
        )
        for field_index, feature in enumerate(raw_features):
            properties = feature.get("properties") or {}
            features.append(
                {
                    "type": "Feature",
                    "geometry": _feature_geometry(feature, boundary_file),
                    "properties": _field_metadata(
                        properties,
                        grower_name=grower_name,
                        grower_slug=grower_slug,
                        farm_name=farm_name,
                        farm_slug=farm_slug,
                        farm_color=color,
                        index=field_index,
                    ),
                }
            )

    if not features:
        raise ValueError(f"{grower_slug} has no field boundary features")

    return {
        "slug": grower_slug,
        "name": grower_name,
        "farms": farms,
        "features": features,
    }


_HTML_TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>$page_title</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #map { height: 100%; margin: 0; }
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
  #map { position: absolute; inset: 0; background: #e5e7eb; }
  #panel {
    position: absolute; top: 12px; left: 12px; z-index: 1000;
    width: 272px; max-height: calc(100% - 24px); overflow: auto;
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 10px; box-shadow: 0 8px 28px rgba(15, 23, 42, 0.28);
    padding: 12px; box-sizing: border-box;
  }
  #panel h1 { font-size: 15px; line-height: 1.25; margin: 0 0 2px; color: #0f172a; }
  .summary { font-size: 11.5px; color: #4b5563; margin-bottom: 8px; }
  #zoom-all {
    width: 100%; border: 1px solid #bfdbfe; background: #eff6ff; color: #1d4ed8;
    border-radius: 6px; padding: 6px 8px; font-size: 12px; font-weight: 600;
    cursor: pointer; margin-bottom: 4px;
  }
  #zoom-all:hover { background: #dbeafe; }
  .farm-group { margin-top: 7px; }
  .farm-name {
    font-size: 10.5px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.04em; color: #374151; margin: 6px 0 3px;
  }
  .field-item {
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 8px; width: 100%; border: 1px solid #e5e7eb; background: #f9fafb;
    border-radius: 6px; padding: 5px 7px; margin: 2px 0; cursor: pointer;
    font-size: 12px; text-align: left; color: #111827;
  }
  .field-item:hover { background: #eff6ff; border-color: #93c5fd; }
  .field-meta { color: #6b7280; font-size: 10.5px; white-space: nowrap; }
  .foot { margin-top: 10px; font-size: 10px; color: #6b7280; line-height: 1.35; }
  .popup-title { font-weight: 700; font-size: 14px; margin-bottom: 6px; color: #0f172a; }
  .popup-row { display: flex; gap: 8px; font-size: 12px; margin: 2px 0; color: #111827; }
  .popup-label { color: #6b7280; min-width: 54px; }
  @media (max-width: 640px) {
    #panel { width: 205px; padding: 9px; }
    #panel h1 { font-size: 13px; }
    .summary { font-size: 10.5px; }
    .field-item { font-size: 11px; padding: 4px 6px; }
  }
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <h1>$page_title</h1>
  <div class="summary">$summary</div>
  <button id="zoom-all" type="button">Zoom to all fields</button>
  <div id="field-list"></div>
  <div class="foot">Boundaries: pipeline GeoJSON &middot; Basemap: Esri World Imagery<br/>
  Click a field for grower, farm and field details.</div>
</div>
<script>
const MAP_DATA = $map_data;

const map = L.map('map', { zoomControl: false, preferCanvas: true });
L.control.zoom({ position: 'topright' }).addTo(map);

const esri = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  {
    maxZoom: 19,
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
  }
);
const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
});
esri.addTo(map);
L.control.layers(
  { 'Satellite (Esri World Imagery)': esri, 'OpenStreetMap': osm },
  null,
  { position: 'bottomright', collapsed: false }
).addTo(map);

const layers = {};
const bounds = L.latLngBounds([]);

function styleFor(feature) {
  const color = feature.properties.farm_color || '#2563eb';
  return { color: color, weight: 2.2, opacity: 0.95, fillColor: color, fillOpacity: 0.30 };
}

function formatArea(props) {
  const ac = Number(props.area_acres);
  const ha = Number(props.area_ha);
  if (Number.isFinite(ac) && Number.isFinite(ha)) {
    return ac.toLocaleString(undefined, { maximumFractionDigits: 1 }) + ' ac (' +
           ha.toLocaleString(undefined, { maximumFractionDigits: 1 }) + ' ha)';
  }
  if (Number.isFinite(ac)) return ac.toLocaleString(undefined, { maximumFractionDigits: 1 }) + ' ac';
  if (Number.isFinite(ha)) return ha.toLocaleString(undefined, { maximumFractionDigits: 1 }) + ' ha';
  return '';
}

function popupNode(props) {
  const box = document.createElement('div');
  const title = document.createElement('div');
  title.className = 'popup-title';
  title.textContent = props.field;
  box.appendChild(title);
  const rows = [
    ['Grower', props.grower],
    ['Farm', props.farm],
    ['Field', props.field],
    ['Area', formatArea(props)],
    ['Crop', props.crop],
    ['County', props.county],
    ['State', props.state]
  ];
  rows.forEach(function (pair) {
    const value = pair[1];
    if (value === null || value === undefined || value === '') return;
    const row = document.createElement('div');
    row.className = 'popup-row';
    const label = document.createElement('span');
    label.className = 'popup-label';
    label.textContent = pair[0];
    const text = document.createElement('span');
    text.textContent = String(value);
    row.appendChild(label);
    row.appendChild(text);
    box.appendChild(row);
  });
  return box;
}

const fieldLayer = L.geoJSON(MAP_DATA, {
  style: styleFor,
  onEachFeature: function (feature, layer) {
    const props = feature.properties;
    layers[props.key] = layer;
    layer.bindPopup(popupNode(props), { maxWidth: 330, autoPan: true });
    layer.bindTooltip(props.field + ' — ' + props.farm, { sticky: true, direction: 'top' });
    layer.on('mouseover', function () {
      layer.setStyle({ weight: 3.5, fillOpacity: 0.52 });
      layer.bringToFront();
    });
    layer.on('mouseout', function () {
      fieldLayer.resetStyle(layer);
    });
    bounds.extend(layer.getBounds());
  }
}).addTo(map);

function fitAll() {
  if (bounds.isValid()) {
    map.fitBounds(bounds, { padding: [30, 30] });
  } else {
    map.setView([39.5, -89.0], 6);
  }
}
fitAll();

document.getElementById('zoom-all').addEventListener('click', fitAll);

const groups = new Map();
MAP_DATA.features.forEach(function (feature) {
  const props = feature.properties;
  if (!groups.has(props.farm_key)) {
    groups.set(props.farm_key, { farm: props.farm, fields: [] });
  }
  groups.get(props.farm_key).fields.push(props);
});

const list = document.getElementById('field-list');
Array.from(groups.values())
  .sort(function (a, b) { return a.farm.localeCompare(b.farm); })
  .forEach(function (group) {
    const wrap = document.createElement('div');
    wrap.className = 'farm-group';
    const heading = document.createElement('div');
    heading.className = 'farm-name';
    heading.textContent = group.farm;
    wrap.appendChild(heading);
    group.fields
      .sort(function (a, b) {
        return String(a.field).localeCompare(String(b.field), undefined, { numeric: true });
      })
      .forEach(function (props) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'field-item';
        const name = document.createElement('span');
        name.className = 'field-name';
        name.textContent = props.field;
        const meta = document.createElement('span');
        meta.className = 'field-meta';
        const ac = Number(props.area_acres);
        meta.textContent = Number.isFinite(ac)
          ? ac.toLocaleString(undefined, { maximumFractionDigits: 0 }) + ' ac'
          : '';
        button.appendChild(name);
        button.appendChild(meta);
        button.addEventListener('click', function () {
          const layer = layers[props.key];
          if (!layer) return;
          map.flyToBounds(layer.getBounds(), { padding: [60, 60], maxZoom: 16, duration: 0.6 });
          layer.openPopup();
        });
        wrap.appendChild(button);
      });
    list.appendChild(wrap);
  });
</script>
</body>
</html>
"""
)


def _summary(grower: dict[str, Any]) -> str:
    features = grower["features"]
    farms = {feature["properties"]["farm_key"] for feature in features}
    total_ac = sum(
        value
        for value in (
            feature["properties"]["area_acres"] for feature in features
        )
        if value is not None
    )
    total = f"{total_ac:,.0f} ac" if total_ac else ""
    parts = [f"{len(features)} fields", f"{len(farms)} farms"]
    if total:
        parts.append(total)
    return " &middot; ".join(parts)


def _escape_json_for_script(payload: Any) -> str:
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    # A literal </script> inside a string would close the tag early; U+2028/29
    # are legal in JSON but not in pre-ES2019 JavaScript string literals.
    return (
        text.replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_html(grower: dict[str, Any]) -> str:
    page_title = html.escape(f"{grower['name']} — Field Map")
    summary = _summary(grower)
    map_data = {
        "type": "FeatureCollection",
        "features": grower["features"],
    }
    return _HTML_TEMPLATE.safe_substitute(
        page_title=page_title,
        summary=summary,
        map_data=_escape_json_for_script(map_data),
    )


def _discover_grower_dirs(growers_root: Path, slugs: list[str] | None) -> list[Path]:
    if slugs:
        dirs = []
        for slug in slugs:
            candidate = growers_root / slug
            if not candidate.is_dir():
                raise FileNotFoundError(f"grower not found: {candidate}")
            dirs.append(candidate)
        return dirs
    return sorted(
        path
        for path in growers_root.glob("*")
        if path.is_dir() and ((path / "farms").is_dir() or (path / "grower.json").exists())
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate_grower_web_map.py",
        description="Generate one lightweight interactive field map per grower.",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Runtime data root (default: $DATA_PIPELINE_DATA_ROOT).",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--all-growers",
        action="store_true",
        help="Map every grower under the runtime (default when no --grower-slug is given).",
    )
    selection.add_argument(
        "--grower-slug",
        action="append",
        dest="grower_slugs",
        metavar="SLUG",
        help="Grower to map; repeat for several. Defaults to all growers.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for the HTML files (default: growers/<grower>/derived/reports).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List discovered growers/farms/fields and planned outputs without writing.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print errors and the final output paths.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    raw_root = args.data_root or os.environ.get("DATA_PIPELINE_DATA_ROOT")
    if not raw_root:
        print(
            "error: --data-root or DATA_PIPELINE_DATA_ROOT is required",
            file=sys.stderr,
        )
        return 2
    data_root = Path(raw_root).expanduser()
    if not data_root.is_absolute():
        print(f"error: data root must be absolute: {data_root}", file=sys.stderr)
        return 2
    growers_root = data_root / "data-pipeline" / "growers"
    if not growers_root.is_dir():
        print(f"error: growers directory not found: {growers_root}", file=sys.stderr)
        return 2

    try:
        grower_dirs = _discover_grower_dirs(growers_root, args.grower_slugs)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not grower_dirs:
        print(f"error: no growers found under {growers_root}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"Runtime data root: {data_root}")
        print(f"Growers root:      {growers_root}")
        print(f"Mode:              {'dry run' if args.dry_run else 'write'}")

    written: list[tuple[Path, int]] = []
    failures = 0
    for color_offset, grower_dir in enumerate(grower_dirs):
        try:
            grower = _load_grower(grower_dir, color_offset=color_offset)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures += 1
            print(f"error: {grower_dir.name}: {exc}", file=sys.stderr)
            continue

        out_dir = (
            args.output_dir.expanduser()
            if args.output_dir is not None
            else grower_dir / "derived" / "reports"
        )
        out_path = out_dir / f"{grower['slug']}_fields_map.html"

        if not args.quiet:
            print(f"\n{grower['slug']} — {grower['name']}")
            for farm in grower["farms"]:
                print(f"  farm {farm['slug']} ({farm['name']}): {farm['fields']} fields")
            print(f"  total: {len(grower['features'])} fields")
            print(f"  output: {out_path}")

        if args.dry_run:
            continue

        out_dir.mkdir(parents=True, exist_ok=True)
        text = render_html(grower)
        out_path.write_text(text, encoding="utf-8")
        written.append((out_path, len(text.encode("utf-8"))))
        if not args.quiet:
            print(f"  wrote {out_path} ({written[-1][1] / 1024:.1f} KB)")

    if failures and not written:
        return 1
    if not args.dry_run:
        print("\nWrote:")
        for path, size in written:
            print(f"  {path} ({size / 1024:.1f} KB)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
