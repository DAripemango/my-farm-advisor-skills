# Grower Web Map Local Instructions

## Purpose

This subskill generates one lightweight, interactive HTML field map per grower
from the boundary GeoJSON the data pipeline already downloaded. It is a
grower-level reporting step, not a farm pipeline step.

## Safe edit scope

Edits stay in this folder and the paired entrypoint
`../src/scripts/generate_grower_web_map.py` unless the user explicitly asks for
a broader change. Do not change the parent `README.md`, `AGENTS.md`, or the
umbrella `SKILL.md` from a grower-web-map task beyond the discovery link.

## Read nearby docs first

Read `GUIDE.md` for the data contract and output design. Read
`../AGENTS.md` for the runtime install contract and `../README.md` for the
data-pipeline overview.

## Data contract

Read-only inputs under `$DATA_PIPELINE_DATA_ROOT/data-pipeline`:

- `growers/<grower>/grower.json`
- `growers/<grower>/farms/<farm>/farm.json`
- `growers/<grower>/farms/<farm>/boundary/field_boundaries.geojson`

Outputs go to `growers/<grower>/derived/reports/<grower>_fields_map.html`.
Never write generated HTML into this skill checkout.

## Runtime notes

- No third-party Python package is required: the generator uses the standard
  library only.
- Leaflet and Esri World Imagery load from CDNs in the browser. The HTML is
  not usable without network access for tiles/JS, by design.
- Do not run `data-pipeline/scripts/install.sh --force-refresh` just to seed
  this subskill into an existing runtime: it replaces the whole runtime source
  tree. Copy only the new entrypoint and module instead.

## Local validation

Run `./scripts/validate.sh` from the repository root after structural changes.
Generate a map into a temporary runtime and check the HTML contains the field
IDs, grower/farm names, Leaflet CDN, and Esri tile URL.
