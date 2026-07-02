# SES Web Application Implementation Specification

## 1. System Architecture

The application is split into four layers:

- Browser UI: ES-module frontend in `static/`, with module tabs for pre-calculation, post-processing, and database review.
- API server: `app.py`, a small Python HTTP server exposing JSON and multipart endpoints.
- Domain engine: `ses_engine/calculations.py`, deterministic laminate and mechanical calculations ported from the workbook/MATLAB logic.
- Persistence and files: SQLite database in `data/ses.sqlite3`; Excel exports generated with OpenPyXL under `data/exports/`.

This keeps the numerical engine independent from the UI and API, so the same functions power live pre-calculation, specimen storage, test processing, export, and tests.

## 2. Database Schema

`materials`

| Column | Type | Notes |
| --- | --- | --- |
| id | integer primary key | Material selector key |
| name | text unique | e.g. RC416, UD300 |
| thickness_mm | real | Ply thickness |
| areal_weight_g_m2 | real | Grammage |
| fiber_type | text | `unidirectional` or `bidirectional` |
| resin_fraction | real | Stored as 0.35, 0.40 |
| created_at | text | UTC ISO timestamp |

`core_materials`

| Column | Type | Notes |
| --- | --- | --- |
| id | integer primary key | Core selector key |
| key | text unique | Stable API/UI value |
| name | text unique | e.g. Aluminium honeycomb (HC Al) |
| type | text | Honeycomb, wood, custom |
| thickness_mm | real | Default core thickness |
| density_kg_m3 | real | Used for theoretical core weight |
| mechanical_notes | text | Optional engineering notes |
| geometry_notes | text | Optional geometry notes |
| created_at / updated_at | text | UTC ISO timestamps |

`specimens`

| Column | Type | Notes |
| --- | --- | --- |
| id | text primary key | Specimen ID |
| test_type | text | 3PB, Shear, etc. |
| laminate_json | text | Structured laminate: top skin, selected core, bottom skin |
| theoretical_json | text | Weight, thickness, 0 deg %, warping, ply table |
| real_weight_g | real | Uploaded/measured |
| real_thickness_mm | real | Uploaded/measured |
| core_material | text | HC, Balsa, etc. |
| core_thickness_mm | real | Derived from selected core |
| skin_thickness_mm | real | Equivalent skin thickness for legacy formulas |
| top_skin_thickness_mm | real | Top skin thickness |
| bottom_skin_thickness_mm | real | Bottom skin thickness |
| computed_json | text | Common points, panel metrics, CS values |
| raw_points_json | text | Full cleaned force-displacement curve |
| reduced_points_json | text | LTTB-reduced curve, about 300 points |
| selected_points_json | text | x1/x2/y1/y2/Ymax or shear peaks |
| source_filename | text | Uploaded workbook name |
| created_at / updated_at | text | UTC ISO timestamps |

SQLite is used as the relational default for a local engineering app; the JSON columns preserve flexible scientific results without schema churn.

## 3. API Design

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/materials` | List reusable materials |
| GET | `/api/core-materials` | List selectable core materials |
| POST | `/api/core-materials` | Create a core material |
| PUT | `/api/core-materials/{id}` | Update a core material |
| DELETE | `/api/core-materials/{id}` | Delete a core material |
| PUT | `/api/materials/{id}` | Update a carbon fiber material |
| DELETE | `/api/materials/{id}` | Delete a carbon fiber material |
| POST | `/api/materials` | Create a material |
| POST | `/api/precalculate` | Calculate laminate metrics from ply rows |
| POST | `/api/specimens/laminate` | Store step-1 specimen laminate and theoretical values |
| POST | `/api/specimens/process` | Upload Excel, compute mechanical metrics, persist result |
| GET | `/api/specimens` | List specimen summaries |
| GET | `/api/specimens/{id}` | Full specimen detail |
| GET | `/api/specimens/{id}/export` | Download Excel export with graph |
| DELETE | `/api/specimens/{id}` | Delete a specimen, UI exposes only in edit mode |

## 4. UI Structure

- `Pre-calculation`
  - Material list with hidden edit mode for creating carbon fiber materials.
  - Separate Add New Carbon Fiber and Edit Existing Carbon Fibers flows.
  - Separate core database with add/edit/delete flows.
  - Laminate hierarchy: top skin, selected core, bottom skin.
  - Each skin has its own stacking sequence and optional thickness override.
  - New top layers insert at the outer surface; new bottom layers append outward from the core.
  - Live KPI panel: total weight, total thickness, 0 deg fiber percentage, warping percentage.
  - Ply-by-ply result table.

- `Post-processing`
  - Step 1: same top/core/bottom laminate model, without a specimen ID field.
  - Step 2: specimen ID, Excel file upload, real weight/thickness, and span.
  - Experimental upload strictly reads force and displacement; workbook metadata columns are ignored.
  - Curve graph with selected points highlighted.
  - Panel result table for EI and CS values.

- `Database`
  - Specimen summary table only at first render.
  - Filtering and column sorting.
  - EI cells are green when `>= 1` and red when `< 1`.
  - Detail modal overlays the table with full theoretical/real values, selected points, graph, panel metrics, laminate structure, and export button.

## 5. Core Calculation Logic

Material and core formulas:

- Ply fiber weight: `area_m2 * areal_weight_g_m2`
- Ply total weight: `fiber_weight / (1 - resin_fraction)`
- Core materials: Aluminium honeycomb, Aramid honeycomb, Balsa wood
- Total thickness: top skin thickness + core thickness + bottom skin thickness
- 0 deg fiber percentage: `sum(zero_fiber_weight) / sum(fiber_weight)`
- Warping percentage: `sum(abs(top_fiber_by_orientation - bottom_fiber_by_orientation)) / total_fiber_weight`

Orientation constraints:

- Unidirectional: `0`, `+45`, `90`, `-45`
- Bidirectional: `+-45`, `+-90`

3PB formulas port the MATLAB/workbook cells:

- Maximum force from curve.
- Maximum slope pair from ascending branch only, with `dx >= 1 mm`.
- Probe second moment:
  `specimen_length * ((core + total_skin)^3 - core^3) / 12`
- Probe stress:
  `max_force * span * 0.5 * (core + 2 * skin_each) / (4 * I_probe) * 1e6`
- Panel inertia uses the same parallel-axis calculation as `secondMomentPanel`.
- `E = slope * span^3 / (48 * I_probe) * 0.001`
- `EI = E * 1e9 * I_panel_m4`
- Safety coefficients are calculated per panel against the workbook constants.
- For asymmetric skins, the application stores top and bottom skin thickness separately and uses their average as the equivalent `D18` value required by the workbook/MATLAB equations. Probe inertia uses the total skin thickness, so top + bottom is preserved.

Shear formulas:

- Peak distance defaults to `max(1 mm, 20% of displacement span)`.
- Peak prominence defaults to `8%` of max absolute load.
- Fallback selects the two highest sufficiently separated peaks.
- Shear stress:
  - FBH/FHB/SHB/MHBS/SISh use lower peak.
  - FBHS/SISv use higher peak.
  - Formula: `peak / (pi * 25 * skin_each)`.
- FBH perimeter shear:
  `(outer_width + outer_height) * 0.002 * (skin_each/1000) * shear_stress * 1e6`

## 6. MATLAB Replication Strategy

The MATLAB script was treated as the executable source of truth for:

- Metadata label extraction.
- Load/displacement parsing.
- Workbook-style laminate parsing.
- 3PB maximum slope point selection.
- Shear peak selection/fallback.
- Panel constants: FBH, FHB, FBHS, SHB, MHBS, SISv, SISh.
- EI, CS, stress, deflection, and energy equations.

Reference formulas are ported one-to-one into named Python functions. Unit tests include a known workbook case for `MHBS` where `EI = 4337.554406573872 GPa*m^4` and `CS_EI = 1.6184904502141315`.

## 7. Excel Data Processing Pipeline

1. Load workbook with OpenPyXL.
2. Try each sheet until a valid force/load and displacement block is found.
3. Locate only `Force`/`LOAD` and `Displacement` columns.
4. Ignore all other columns and workbook metadata for the upload calculation.
5. Convert decimal comma/period values safely.
6. Sort by displacement and drop duplicate displacement values.
7. Calculate selected points and panel metrics.
8. Reduce the curve to about 300 points using Largest-Triangle-Three-Buckets to preserve shape.
9. Persist raw, reduced, selected, theoretical, and computed data.

## 8. Export Logic

`/api/specimens/{id}/export` builds an `.xlsx` file with:

- Summary sheet: specimen inputs, theoretical values, skin/core thickness, selected points.
- Panel Results sheet: EI, CS, strength, deflection, energy, shear metrics.
- Processed Data sheet: reduced curve and selected point coordinates.
- Embedded scatter chart with curve and highlighted selected points.
- Chart data uses displacement in mm and load in kN; axis major units are 1 mm and 5 kN.
- Export autosizing uses `openpyxl.utils.get_column_letter()` and never reads `.column_letter` from merged cells.

For 3PB, the export includes `x1`, `x2`, `y1`, `y2`, slope, and `Ymax`. For shear, it includes lower and higher peak coordinates.
