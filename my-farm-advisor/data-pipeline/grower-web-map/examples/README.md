# Examples — Grower Web Map

No generated HTML is committed. Generate a map against a runtime and open it
locally.

## All growers

```bash
export DATA_PIPELINE_DATA_ROOT=/absolute/path/to/my-farm-advisor-runtime
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src/scripts/generate_grower_web_map.py" \
  --all-growers
```

Expected output, one file per grower:

```text
${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/il-assignment-grower/derived/reports/il-assignment-grower_fields_map.html
${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/ia-assignment-grower/derived/reports/ia-assignment-grower_fields_map.html
```

## Dry run

```bash
... scripts/generate_grower_web_map.py --all-growers --dry-run
```

Prints each discovered farm, its field count, and the planned output path
without writing anything.

## One grower

```bash
... scripts/generate_grower_web_map.py --grower-slug il-assignment-grower
```

Open the written HTML in a browser. The map fits all fields on load; use the
side list or click a polygon for details.
