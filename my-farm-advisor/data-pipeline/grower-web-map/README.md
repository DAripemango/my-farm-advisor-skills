# Grower Web Map

Generate one lightweight interactive HTML map per grower from the field
boundaries the data pipeline already downloaded.

- Every farm and field for the grower is drawn over **Esri World Imagery**.
- Click a field for **grower, farm and field** details (plus area/crop/county).
- Zoom controls, fit-to-all-fields, and a side list that flies to each field.
- Only boundary GeoJSON is embedded; no rasters or imagery. A three-field
  grower is typically 30–60 KB.
- No extra Python dependency: the generator uses the standard library.

## Quick start

```bash
export DATA_PIPELINE_DATA_ROOT=/absolute/path/to/my-farm-advisor-runtime
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src/scripts/generate_grower_web_map.py" \
  --all-growers
```

Output:

```text
$DATA_PIPELINE_DATA_ROOT/data-pipeline/growers/<grower>/derived/reports/<grower>_fields_map.html
```

See [GUIDE.md](GUIDE.md) for the data contract, options and verification notes.
The runtime-side implementation lives in [`src/grower_web_map.py`](src/grower_web_map.py).
