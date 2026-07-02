# SES Platform

Local web application for laminate pre-calculation, mechanical test post-processing, specimen persistence, visualization, and Excel export.

## Run

```powershell
& "C:\Users\carlo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" app.py --port 8000
```

Open `http://127.0.0.1:8000`.

## Modules

- `Pre-calculation`: reusable carbon fiber and core databases, top skin + core + bottom skin laminate model, live laminate metrics.
- `Post-processing`: staged laminate definition plus Excel upload for 3PB and shear processing.
- `Database`: filterable/sortable specimen table, modal detail view, MATLAB-style graph, panel safety coefficients, Excel export.

## Implementation

- Backend: Python standard-library HTTP server, SQLite, OpenPyXL.
- Frontend: dependency-free ES modules, canvas plotting, REST API calls.
- Calculation engine: [ses_engine/calculations.py](./ses_engine/calculations.py)
- Excel parser/exporter: [ses_engine/excel_io.py](./ses_engine/excel_io.py)
- Database layer: [ses_engine/db.py](./ses_engine/db.py)
- Architecture notes: [docs/IMPLEMENTATION_SPEC.md](./docs/IMPLEMENTATION_SPEC.md)

## Verify

```powershell
& "C:\Users\carlo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest discover -s tests
```
