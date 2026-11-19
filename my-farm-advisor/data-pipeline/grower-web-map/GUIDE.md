---
name: grower-web-map
description: Generate a lightweight interactive HTML field map for each grower from the data-pipeline boundary GeoJSON, with Esri World Imagery, clickable field popups, and a zoom-to-field list.
version: 1.0.0
tags: [web-map, leaflet, grower, field-boundaries, interactive, reporting]
---

# Grower Web Map

## What it produces

One self-contained HTML file per grower containing:

- every farm and field polygon the pipeline downloaded for that grower;
- Esri World Imagery satellite tiles (with an OpenStreetMap fallback);
- zoom controls and fit-to-all-fields on load;
- click/hover popups with **grower, farm, field**, plus area, crop, county and
  state when the boundary properties carry them;
- a side panel listing fields grouped by farm, where clicking a field flies to
  its bounds.

The page embeds only boundary GeoJSON and a small amount of CSS/JS. It does not
embed rasters, imagery, or report bundles, so a three-field grower is typically
30–60 KB. Leaflet and the basemap tiles load from the internet.

## Inputs

Read-only runtime data:

```text
$DATA_PIPELINE_DATA_ROOT/data-pipeline/growers/<grower>/grower.json
$DATA_PIPELINE_DATA_ROOT/data-pipeline/growers/<grower>/farms/<farm>/farm.json
$DATA_PIPELINE_DATA_ROOT/data-pipeline/growers/<grower>/farms/<farm>/boundary/field_boundaries.geojson
```

Boundaries must be EPSG:4326 / OGC:CRS84 (the pipeline's standard). Other CRS
values are refused rather than silently mis-plotted.

## Run

From the runtime source copy:

```bash
export DATA_PIPELINE_DATA_ROOT=/absolute/path/to/my-farm-advisor-runtime

"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src/scripts/generate_grower_web_map.py" \
  --all-growers
```

Or select growers explicitly:

```bash
... scripts/generate_grower_web_map.py \
  --grower-slug il-assignment-grower \
  --grower-slug ia-assignment-grower
```

Useful options:

- `--all-growers` — map every grower (also the default when no `--grower-slug`
  is supplied).
- `--grower-slug SLUG` — repeatable, selects specific growers.
- `--output-dir DIR` — override the default output directory for every grower.
- `--dry-run` — list discovered farms/fields and planned outputs without
  writing.
- `--quiet` — print only errors and final paths.

## Output

```text
$DATA_PIPELINE_DATA_ROOT/data-pipeline/growers/<grower>/derived/reports/<grower>_fields_map.html
```

Open the HTML directly in a browser. The map fits all of the grower's fields on
load; the side panel zooms to individual fields.

## Design notes

- **Tile layer:** `World_Imagery` from
  `server.arcgisonline.com/ArcGIS/rest/services/...`; OSM is available in the
  layer control if imagery is unavailable.
- **Field list:** grouped by farm display name; each item targets the Leaflet
  layer by `grower/farm/field` key so duplicate field IDs across farms cannot
  collide.
- **Popup safety:** popup rows are built as DOM nodes with `textContent`, not
  interpolated HTML.
- **Script safety:** the embedded JSON escapes `<` and U+2028/U+2029 so field
  names cannot terminate the `<script>` block.
- **Coordinates:** rounded to six decimals (~0.1 m) only to keep the payload
  small; geometry type and vertex order are unchanged.

## Verification

1. `--dry-run` reports the expected grower, farm and field counts.
2. Generate the HTML and confirm the file contains:
   - every expected field ID;
   - the grower and farm display names;
   - the Leaflet CDN and the Esri `World_Imagery` tile URL;
   - three `Feature` objects for a three-field grower.
3. Run `./scripts/validate.sh` from the repository root.

There is no headless browser in the standard runtime, so tile rendering is
checked in a normal browser rather than by screenshot.

## Limits

- Internet access is required for Leaflet and basemap tiles.
- The map is a boundary/identity viewer; it does not carry soil, weather, NDVI
  or yield layers.
- Very large growers (hundreds of fields) remain usable, but the inline
  GeoJSON grows with the number of vertices; simplify upstream if a grower
  approaches tens of MB.
