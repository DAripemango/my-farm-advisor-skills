# Provenance — Grower Web Map

## Origin

Created 2026-11-19 for the Assignment 1 grower web-map task inside the
`my-farm-advisor/data-pipeline` subskill area.

## Sources

- Field polygons: runtime `boundary/field_boundaries.geojson` written by the
  data pipeline's USDA CSB / FIBOA field-boundary ingest.
- Grower and farm names: runtime `grower.json` and `farm.json`.
- Basemap: Esri World Imagery tiles and OpenStreetMap tiles, requested by the
  browser at view time.
- Mapping library: Leaflet 1.9.4, loaded from the unpkg CDN by the generated
  page.

## Code

The generator and its CLI entrypoint are original code written for this
subskill. No third-party source files are vendored or copied into this folder.
The JavaScript map page is emitted from the template in
`src/grower_web_map.py`.

## Generated assets

No generated HTML, tiles, rasters or runtime data are committed here. Maps are
written under the runtime data root
(`growers/<grower>/derived/reports/<grower>_fields_map.html`) and stay out of
Git per the repository asset policy.
