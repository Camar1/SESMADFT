from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .calculations import (
    CORE_MATERIALS,
    DEFAULT_MATERIALS,
    DEFAULT_PANEL_HEIGHTS_MM,
    DEFAULT_SPECIMEN_LENGTH_MM,
    DEFAULT_SPAN_MM,
    Material,
    compute_3pb_panel_results,
    energy_absorbed_until_displacement,
    finite_number,
    is_energy_absorbed_test,
    laminate_sequence,
    panel_abbreviation,
    safe_json,
)


DEFAULT_CAR_PANELS = [
    {"name": "Front Bulkhead", "code": "FBH", "area_mm2": 60798.57, "height_mm": 149.98, "multiplier": 1},
    {"name": "Front Hoop Bulkhead", "code": "FHB", "area_mm2": 433988.68, "height_mm": 121.68, "multiplier": 1},
    {"name": "Front Bulkhead Side", "code": "FBHS", "area_mm2": 372409.54, "height_mm": 337.81, "multiplier": 2},
    {"name": "Side Impact Structure Horizontal", "code": "SISh", "area_mm2": 1110232.31, "height_mm": 185.40, "multiplier": 1},
    {"name": "Side Impact Structure Vertical", "code": "SISv", "area_mm2": 287720.74, "height_mm": 274.86, "multiplier": 2},
    {"name": "Main Hoop Bulkhead Side", "code": "MHBS", "area_mm2": 328335.11, "height_mm": 248.17, "multiplier": 2},
    {"name": "Side Hoop Bulkhead", "code": "SHB", "area_mm2": 96160.39, "height_mm": 101.29, "multiplier": 1},
    {"name": "Dashboard", "code": "DASH", "area_mm2": 31463.69, "height_mm": 0, "multiplier": 1},
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def decode_json_field(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        if not value:
            return default
        return json.loads(value)
    return value


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    technical_id TEXT,
                    name TEXT NOT NULL UNIQUE,
                    material_category TEXT NOT NULL DEFAULT 'fiber',
                    fiber_family TEXT,
                    thickness_mm REAL NOT NULL,
                    areal_weight_g_m2 REAL NOT NULL,
                    fiber_type TEXT NOT NULL CHECK (fiber_type IN ('unidirectional', 'bidirectional')),
                    resin_fraction REAL NOT NULL DEFAULT 0,
                    e1_pa REAL,
                    e2_pa REAL,
                    g12_pa REAL,
                    poisson_input REAL,
                    density_kg_m3 REAL,
                    strength_x_mpa REAL,
                    strength_x_compression_mpa REAL,
                    strength_y_mpa REAL,
                    strength_y_compression_mpa REAL,
                    strength_s_mpa REAL,
                    aliases TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS core_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    technical_id TEXT,
                    name TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL DEFAULT 'honeycomb',
                    material_category TEXT NOT NULL DEFAULT 'core',
                    fiber_family TEXT,
                    thickness_mm REAL NOT NULL,
                    density_kg_m3 REAL NOT NULL DEFAULT 0,
                    e1_pa REAL,
                    e2_pa REAL,
                    g12_pa REAL,
                    poisson_input REAL,
                    strength_x_mpa REAL,
                    strength_x_compression_mpa REAL,
                    strength_y_mpa REAL,
                    strength_y_compression_mpa REAL,
                    strength_s_mpa REAL,
                    aliases TEXT,
                    notes TEXT,
                    mechanical_notes TEXT,
                    geometry_notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS specimens (
                    id TEXT PRIMARY KEY,
                    test_type TEXT NOT NULL,
                    laminate_json TEXT NOT NULL DEFAULT '[]',
                    theoretical_json TEXT NOT NULL DEFAULT '{}',
                    real_weight_g REAL,
                    real_thickness_mm REAL,
                    core_material TEXT,
                    core_thickness_mm REAL,
                    skin_thickness_mm REAL,
                    top_skin_thickness_mm REAL,
                    bottom_skin_thickness_mm REAL,
                    computed_json TEXT NOT NULL DEFAULT '{}',
                    raw_points_json TEXT NOT NULL DEFAULT '[]',
                    reduced_points_json TEXT NOT NULL DEFAULT '[]',
                    selected_points_json TEXT NOT NULL DEFAULT '[]',
                    comments TEXT,
                    source_filename TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_specimens_test_type ON specimens(test_type);
                CREATE INDEX IF NOT EXISTS idx_specimens_updated_at ON specimens(updated_at);

                CREATE TABLE IF NOT EXISTS cars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    panels_json TEXT NOT NULL DEFAULT '[]',
                    dashboard_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS monocoque_weight_calculations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    car_id INTEGER,
                    car_snapshot_json TEXT NOT NULL DEFAULT '{}',
                    assignments_json TEXT NOT NULL DEFAULT '{}',
                    front_hoop_volume_mm3 REAL,
                    front_hoop_density_kg_mm3 REAL,
                    hardpoints_weight_g REAL,
                    computed_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_monocoque_updated_at ON monocoque_weight_calculations(updated_at);

                CREATE TABLE IF NOT EXISTS car_probe_metrics (
                    car_id INTEGER NOT NULL,
                    specimen_id TEXT NOT NULL,
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'ok',
                    error TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (car_id, specimen_id),
                    FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE,
                    FOREIGN KEY (specimen_id) REFERENCES specimens(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_car_probe_metrics_car ON car_probe_metrics(car_id);
                CREATE INDEX IF NOT EXISTS idx_car_probe_metrics_specimen ON car_probe_metrics(specimen_id);
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(specimens)").fetchall()}
            if "top_skin_thickness_mm" not in columns:
                conn.execute("ALTER TABLE specimens ADD COLUMN top_skin_thickness_mm REAL")
            if "bottom_skin_thickness_mm" not in columns:
                conn.execute("ALTER TABLE specimens ADD COLUMN bottom_skin_thickness_mm REAL")
            if "comments" not in columns:
                conn.execute("ALTER TABLE specimens ADD COLUMN comments TEXT")
            material_columns = {row[1] for row in conn.execute("PRAGMA table_info(materials)").fetchall()}
            for column, ddl in {
                "technical_id": "TEXT",
                "material_category": "TEXT NOT NULL DEFAULT 'fiber'",
                "fiber_family": "TEXT",
                "e1_pa": "REAL",
                "e2_pa": "REAL",
                "g12_pa": "REAL",
                "poisson_input": "REAL",
                "density_kg_m3": "REAL",
                "strength_x_mpa": "REAL",
                "strength_x_compression_mpa": "REAL",
                "strength_y_mpa": "REAL",
                "strength_y_compression_mpa": "REAL",
                "strength_s_mpa": "REAL",
                "aliases": "TEXT",
                "notes": "TEXT",
            }.items():
                if column not in material_columns:
                    conn.execute(f"ALTER TABLE materials ADD COLUMN {column} {ddl}")
            core_columns = {row[1] for row in conn.execute("PRAGMA table_info(core_materials)").fetchall()}
            for column, ddl in {
                "technical_id": "TEXT",
                "material_category": "TEXT NOT NULL DEFAULT 'core'",
                "fiber_family": "TEXT",
                "e1_pa": "REAL",
                "e2_pa": "REAL",
                "g12_pa": "REAL",
                "poisson_input": "REAL",
                "strength_x_mpa": "REAL",
                "strength_x_compression_mpa": "REAL",
                "strength_y_mpa": "REAL",
                "strength_y_compression_mpa": "REAL",
                "strength_s_mpa": "REAL",
                "aliases": "TEXT",
                "notes": "TEXT",
            }.items():
                if column not in core_columns:
                    conn.execute(f"ALTER TABLE core_materials ADD COLUMN {column} {ddl}")
            count = conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
            if count == 0:
                for material in DEFAULT_MATERIALS:
                    conn.execute(
                        """
                        INSERT INTO materials
                            (technical_id, name, material_category, fiber_family,
                             thickness_mm, areal_weight_g_m2, fiber_type, resin_fraction,
                             e1_pa, e2_pa, g12_pa, poisson_input, density_kg_m3,
                             strength_x_mpa, strength_x_compression_mpa, strength_y_mpa,
                             strength_y_compression_mpa, strength_s_mpa, aliases, notes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            material.get("technical_id"),
                            material["name"],
                            material.get("material_category", "fiber"),
                            material.get("fiber_family"),
                            material["thickness_mm"],
                            material["areal_weight_g_m2"],
                            material["fiber_type"],
                            material["resin_fraction"],
                            material.get("e1_pa"),
                            material.get("e2_pa"),
                            material.get("g12_pa"),
                            material.get("poisson_input"),
                            material.get("density_kg_m3"),
                            material.get("strength_x_mpa"),
                            material.get("strength_x_compression_mpa"),
                            material.get("strength_y_mpa"),
                            material.get("strength_y_compression_mpa"),
                            material.get("strength_s_mpa"),
                            material.get("aliases"),
                            material.get("notes"),
                            utc_now(),
                        ),
                    )
            self._migrate_material_catalog(conn)
            core_count = conn.execute("SELECT COUNT(*) FROM core_materials").fetchone()[0]
            if core_count == 0:
                for core in CORE_MATERIALS:
                    conn.execute(
                        """
                        INSERT INTO core_materials
                            (key, technical_id, name, type, material_category, fiber_family,
                             thickness_mm, density_kg_m3,
                             e1_pa, e2_pa, g12_pa, poisson_input, aliases,
                             strength_x_mpa, strength_x_compression_mpa, strength_y_mpa,
                             strength_y_compression_mpa, strength_s_mpa, notes,
                             mechanical_notes, geometry_notes, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            core["key"],
                            core.get("technical_id"),
                            core["name"],
                            core.get("type") or ("honeycomb" if "honeycomb" in core["name"].lower() else "wood"),
                            core.get("material_category", "core"),
                            core.get("fiber_family"),
                            core["thickness_mm"],
                            core["density_kg_m3"],
                            core.get("e1_pa"),
                            core.get("e2_pa"),
                            core.get("g12_pa"),
                            core.get("poisson_input"),
                            core.get("aliases"),
                            core.get("strength_x_mpa"),
                            core.get("strength_x_compression_mpa"),
                            core.get("strength_y_mpa"),
                            core.get("strength_y_compression_mpa"),
                            core.get("strength_s_mpa"),
                            core.get("notes"),
                            "",
                            "",
                            utc_now(),
                            utc_now(),
                        ),
                    )
            self._migrate_core_catalog(conn)
            car_count = conn.execute("SELECT COUNT(*) FROM cars").fetchone()[0]
            if car_count == 0:
                now = utc_now()
                conn.execute(
                    """
                    INSERT INTO cars (name, panels_json, dashboard_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "MAD Formula Monocoque",
                        json.dumps(DEFAULT_CAR_PANELS),
                        json.dumps({"area_mm2": 31463.69}),
                        now,
                        now,
                    ),
                )

    def _migrate_material_catalog(self, conn: sqlite3.Connection) -> None:
        for material in DEFAULT_MATERIALS:
            aliases = [alias.strip() for alias in str(material.get("aliases") or "").split(";") if alias.strip()]
            names = [material["name"], *aliases]
            placeholders = ",".join("?" for _ in names)
            row = conn.execute(
                f"SELECT * FROM materials WHERE lower(name) IN ({placeholders}) ORDER BY id LIMIT 1",
                tuple(name.lower() for name in names),
            ).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO materials
                        (technical_id, name, material_category, fiber_family,
                         thickness_mm, areal_weight_g_m2, fiber_type, resin_fraction,
                         e1_pa, e2_pa, g12_pa, poisson_input, density_kg_m3,
                         strength_x_mpa, strength_x_compression_mpa, strength_y_mpa,
                         strength_y_compression_mpa, strength_s_mpa, aliases, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        material.get("technical_id"),
                        material["name"],
                        material.get("material_category", "fiber"),
                        material.get("fiber_family"),
                        material["thickness_mm"],
                        material["areal_weight_g_m2"],
                        material["fiber_type"],
                        material["resin_fraction"],
                        material.get("e1_pa"),
                        material.get("e2_pa"),
                        material.get("g12_pa"),
                        material.get("poisson_input"),
                        material.get("density_kg_m3"),
                        material.get("strength_x_mpa"),
                        material.get("strength_x_compression_mpa"),
                        material.get("strength_y_mpa"),
                        material.get("strength_y_compression_mpa"),
                        material.get("strength_s_mpa"),
                        material.get("aliases"),
                        material.get("notes"),
                        utc_now(),
                    ),
                )
                continue

            target_name = material["name"]
            existing_target = conn.execute(
                "SELECT id FROM materials WHERE lower(name) = ? AND id <> ?",
                (target_name.lower(), row["id"]),
            ).fetchone()
            name_to_save = target_name if existing_target is None else row["name"]
            conn.execute(
                """
                UPDATE materials
                SET name = ?,
                    thickness_mm = CASE
                        WHEN lower(name) IN ('rc416', 'rc416t') AND ABS(COALESCE(thickness_mm, 0) - 0.44) < 0.000001 THEN ?
                        ELSE thickness_mm
                    END,
                    technical_id = COALESCE(NULLIF(technical_id, ''), ?),
                    material_category = COALESCE(NULLIF(material_category, ''), ?),
                    fiber_family = COALESCE(NULLIF(fiber_family, ''), ?),
                    e1_pa = COALESCE(e1_pa, ?),
                    e2_pa = COALESCE(e2_pa, ?),
                    g12_pa = COALESCE(g12_pa, ?),
                    poisson_input = COALESCE(poisson_input, ?),
                    density_kg_m3 = COALESCE(density_kg_m3, ?),
                    strength_x_mpa = COALESCE(strength_x_mpa, ?),
                    strength_x_compression_mpa = COALESCE(strength_x_compression_mpa, ?),
                    strength_y_mpa = COALESCE(strength_y_mpa, ?),
                    strength_y_compression_mpa = COALESCE(strength_y_compression_mpa, ?),
                    strength_s_mpa = COALESCE(strength_s_mpa, ?),
                    aliases = COALESCE(NULLIF(aliases, ''), ?),
                    notes = COALESCE(NULLIF(notes, ''), ?)
                WHERE id = ?
                """,
                (
                    name_to_save,
                    material["thickness_mm"],
                    material.get("technical_id"),
                    material.get("material_category", "fiber"),
                    material.get("fiber_family"),
                    material.get("e1_pa"),
                    material.get("e2_pa"),
                    material.get("g12_pa"),
                    material.get("poisson_input"),
                    material.get("density_kg_m3"),
                    material.get("strength_x_mpa"),
                    material.get("strength_x_compression_mpa"),
                    material.get("strength_y_mpa"),
                    material.get("strength_y_compression_mpa"),
                    material.get("strength_s_mpa"),
                    material.get("aliases"),
                    material.get("notes"),
                    row["id"],
                ),
            )

    def _migrate_core_catalog(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            DELETE FROM core_materials
            WHERE lower(name) LIKE '%aramid%' OR lower(key) LIKE '%aramid%'
            """
        )
        for core in CORE_MATERIALS:
            aliases = [alias.strip() for alias in str(core.get("aliases") or "").split(";") if alias.strip()]
            names = [core["key"], core["name"], *aliases]
            placeholders = ",".join("?" for _ in names)
            row = conn.execute(
                f"""
                SELECT * FROM core_materials
                WHERE lower(key) IN ({placeholders}) OR lower(name) IN ({placeholders})
                ORDER BY id LIMIT 1
                """,
                tuple(name.lower() for name in names) * 2,
            ).fetchone()
            if row is None:
                now = utc_now()
                conn.execute(
                    """
                    INSERT INTO core_materials
                        (key, technical_id, name, type, material_category, fiber_family,
                         thickness_mm, density_kg_m3,
                         e1_pa, e2_pa, g12_pa, poisson_input, aliases,
                         strength_x_mpa, strength_x_compression_mpa, strength_y_mpa,
                         strength_y_compression_mpa, strength_s_mpa, notes,
                         mechanical_notes, geometry_notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        core["key"],
                        core.get("technical_id"),
                        core["name"],
                        core.get("type") or "core",
                        core.get("material_category", "core"),
                        core.get("fiber_family"),
                        core["thickness_mm"],
                        core["density_kg_m3"],
                        core.get("e1_pa"),
                        core.get("e2_pa"),
                        core.get("g12_pa"),
                        core.get("poisson_input"),
                        core.get("aliases"),
                        core.get("strength_x_mpa"),
                        core.get("strength_x_compression_mpa"),
                        core.get("strength_y_mpa"),
                        core.get("strength_y_compression_mpa"),
                        core.get("strength_s_mpa"),
                        core.get("notes"),
                        "",
                        "",
                        now,
                        now,
                    ),
                )
                continue

            existing_key = conn.execute(
                "SELECT id FROM core_materials WHERE lower(key) = ? AND id <> ?",
                (str(core["key"]).lower(), row["id"]),
            ).fetchone()
            key_to_save = core["key"] if existing_key is None else row["key"]
            existing_name = conn.execute(
                "SELECT id FROM core_materials WHERE lower(name) = ? AND id <> ?",
                (str(core["name"]).lower(), row["id"]),
            ).fetchone()
            name_to_save = core["name"] if existing_name is None else row["name"]
            conn.execute(
                """
                UPDATE core_materials
                SET key = ?,
                    name = ?,
                    type = ?,
                    technical_id = COALESCE(NULLIF(technical_id, ''), ?),
                    material_category = COALESCE(NULLIF(material_category, ''), ?),
                    fiber_family = COALESCE(NULLIF(fiber_family, ''), ?),
                    thickness_mm = ?,
                    density_kg_m3 = ?,
                    e1_pa = COALESCE(e1_pa, ?),
                    e2_pa = COALESCE(e2_pa, ?),
                    g12_pa = COALESCE(g12_pa, ?),
                    poisson_input = COALESCE(poisson_input, ?),
                    aliases = COALESCE(NULLIF(aliases, ''), ?),
                    strength_x_mpa = COALESCE(strength_x_mpa, ?),
                    strength_x_compression_mpa = COALESCE(strength_x_compression_mpa, ?),
                    strength_y_mpa = COALESCE(strength_y_mpa, ?),
                    strength_y_compression_mpa = COALESCE(strength_y_compression_mpa, ?),
                    strength_s_mpa = COALESCE(strength_s_mpa, ?),
                    notes = COALESCE(NULLIF(notes, ''), ?),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    key_to_save,
                    name_to_save,
                    core.get("type") or row["type"] or "core",
                    core.get("technical_id"),
                    core.get("material_category", "core"),
                    core.get("fiber_family"),
                    core["thickness_mm"],
                    core["density_kg_m3"],
                    core.get("e1_pa"),
                    core.get("e2_pa"),
                    core.get("g12_pa"),
                    core.get("poisson_input"),
                    core.get("aliases"),
                    core.get("strength_x_mpa"),
                    core.get("strength_x_compression_mpa"),
                    core.get("strength_y_mpa"),
                    core.get("strength_y_compression_mpa"),
                    core.get("strength_s_mpa"),
                    core.get("notes"),
                    utc_now(),
                    row["id"],
                ),
            )
        conn.execute(
            """
            DELETE FROM core_materials
            WHERE lower(key) IN (
                'aluminium_honeycomb_hc_al',
                'aluminum_honeycomb_hc_al',
                'honeycomb',
                'balsa_wood__9_5_mm',
                'balsa_wood_9_5_mm',
                'balsa_wood__12_7mm',
                'balsa_wood_12_7mm'
            )
            AND lower(key) NOT IN ('hc_al', 'balsa', 'balsa_12_7')
            """
        )

    def list_materials(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM materials ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def create_material(self, payload: dict[str, Any]) -> dict[str, Any]:
        material = Material.from_mapping(payload)
        if not material.name.strip():
            raise ValueError("Material name is required")
        if material.fiber_type not in {"unidirectional", "bidirectional"}:
            raise ValueError("fiber_type must be unidirectional or bidirectional")
        try:
            with self.connect() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO materials
                        (technical_id, name, material_category, fiber_family,
                         thickness_mm, areal_weight_g_m2, fiber_type, resin_fraction,
                         e1_pa, e2_pa, g12_pa, poisson_input, density_kg_m3,
                         strength_x_mpa, strength_x_compression_mpa, strength_y_mpa,
                         strength_y_compression_mpa, strength_s_mpa, aliases, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        material.technical_id.strip() or material.name.strip(),
                        material.name.strip(),
                        material.material_category or "fiber",
                        material.fiber_family,
                        material.thickness_mm,
                        material.areal_weight_g_m2,
                        material.fiber_type,
                        material.resin_fraction,
                        material.e1_pa,
                        material.e2_pa,
                        material.g12_pa,
                        material.poisson_input,
                        material.density_kg_m3,
                        material.strength_x_mpa,
                        material.strength_x_compression_mpa,
                        material.strength_y_mpa,
                        material.strength_y_compression_mpa,
                        material.strength_s_mpa,
                        material.aliases,
                        material.notes,
                        utc_now(),
                    ),
                )
                row = conn.execute("SELECT * FROM materials WHERE id = ?", (cur.lastrowid,)).fetchone()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Carbon fiber '{material.name.strip()}' already exists") from exc
        return dict(row)

    def update_material(self, material_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as conn:
            existing = conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
            if existing is None:
                raise KeyError(f"Material {material_id} not found")
            merged = {**dict(existing), **payload, "id": material_id}
            material = Material.from_mapping(merged)
            if material.fiber_type not in {"unidirectional", "bidirectional"}:
                raise ValueError("fiber_type must be unidirectional or bidirectional")
            conn.execute(
                """
                UPDATE materials
                SET technical_id = ?, name = ?, material_category = ?, fiber_family = ?,
                    thickness_mm = ?, areal_weight_g_m2 = ?, fiber_type = ?, resin_fraction = ?,
                    e1_pa = ?, e2_pa = ?, g12_pa = ?, poisson_input = ?, density_kg_m3 = ?,
                    strength_x_mpa = ?, strength_x_compression_mpa = ?, strength_y_mpa = ?,
                    strength_y_compression_mpa = ?, strength_s_mpa = ?, aliases = ?, notes = ?
                WHERE id = ?
                """,
                (
                    material.technical_id.strip() or material.name.strip(),
                    material.name.strip(),
                    material.material_category or "fiber",
                    material.fiber_family,
                    material.thickness_mm,
                    material.areal_weight_g_m2,
                    material.fiber_type,
                    material.resin_fraction,
                    material.e1_pa,
                    material.e2_pa,
                    material.g12_pa,
                    material.poisson_input,
                    material.density_kg_m3,
                    material.strength_x_mpa,
                    material.strength_x_compression_mpa,
                    material.strength_y_mpa,
                    material.strength_y_compression_mpa,
                    material.strength_s_mpa,
                    material.aliases,
                    material.notes,
                    material_id,
                ),
            )
            row = conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
        if row is None:
            raise KeyError(f"Material {material_id} not found")
        return dict(row)

    def delete_material(self, material_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
            if row is None:
                raise KeyError(f"Material {material_id} not found")
            conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))
        return dict(row)

    def list_core_materials(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM core_materials
                ORDER BY name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def create_core_material(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not str(payload.get("name") or "").strip():
            raise ValueError("Core material name is required")
        key = str(payload.get("key") or payload.get("name") or "core").strip().lower()
        key = "".join(ch if ch.isalnum() else "_" for ch in key).strip("_")
        now = utc_now()
        try:
            with self.connect() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO core_materials
                        (key, technical_id, name, type, material_category, fiber_family,
                         thickness_mm, density_kg_m3,
                         e1_pa, e2_pa, g12_pa, poisson_input,
                         strength_x_mpa, strength_x_compression_mpa, strength_y_mpa,
                         strength_y_compression_mpa, strength_s_mpa, aliases,
                         notes, mechanical_notes, geometry_notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        str(payload.get("technical_id") or key).strip(),
                        str(payload["name"]).strip(),
                        str(payload.get("type") or "core").strip(),
                        str(payload.get("material_category") or "core").strip(),
                        str(payload.get("fiber_family") or "").strip(),
                        float(payload["thickness_mm"]),
                        float(payload.get("density_kg_m3") or 0),
                        finite_number(payload.get("e1_pa")),
                        finite_number(payload.get("e2_pa")),
                        finite_number(payload.get("g12_pa")),
                        finite_number(payload.get("poisson_input")),
                        finite_number(payload.get("strength_x_mpa")),
                        finite_number(payload.get("strength_x_compression_mpa")),
                        finite_number(payload.get("strength_y_mpa")),
                        finite_number(payload.get("strength_y_compression_mpa")),
                        finite_number(payload.get("strength_s_mpa")),
                        str(payload.get("aliases") or ""),
                        str(payload.get("notes") or ""),
                        str(payload.get("mechanical_notes") or ""),
                        str(payload.get("geometry_notes") or ""),
                        now,
                        now,
                    ),
                )
                row = conn.execute("SELECT * FROM core_materials WHERE id = ?", (cur.lastrowid,)).fetchone()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Core material '{str(payload['name']).strip()}' already exists") from exc
        return dict(row)

    def update_core_material(self, core_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        with self.connect() as conn:
            existing = conn.execute("SELECT * FROM core_materials WHERE id = ?", (core_id,)).fetchone()
            if existing is None:
                raise KeyError(f"Core material {core_id} not found")
            payload = {**dict(existing), **payload}
            key = str(payload.get("key") or payload.get("name") or "core").strip().lower()
            key = "".join(ch if ch.isalnum() else "_" for ch in key).strip("_")
            conn.execute(
                """
                UPDATE core_materials
                SET key = ?, technical_id = ?, name = ?, type = ?, material_category = ?, fiber_family = ?,
                    thickness_mm = ?, density_kg_m3 = ?,
                    e1_pa = ?, e2_pa = ?, g12_pa = ?, poisson_input = ?,
                    strength_x_mpa = ?, strength_x_compression_mpa = ?, strength_y_mpa = ?,
                    strength_y_compression_mpa = ?, strength_s_mpa = ?, aliases = ?, notes = ?,
                    mechanical_notes = ?, geometry_notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    key,
                    str(payload.get("technical_id") or key).strip(),
                    str(payload["name"]).strip(),
                    str(payload.get("type") or "core").strip(),
                    str(payload.get("material_category") or "core").strip(),
                    str(payload.get("fiber_family") or "").strip(),
                    float(payload["thickness_mm"]),
                    float(payload.get("density_kg_m3") or 0),
                    finite_number(payload.get("e1_pa")),
                    finite_number(payload.get("e2_pa")),
                    finite_number(payload.get("g12_pa")),
                    finite_number(payload.get("poisson_input")),
                    finite_number(payload.get("strength_x_mpa")),
                    finite_number(payload.get("strength_x_compression_mpa")),
                    finite_number(payload.get("strength_y_mpa")),
                    finite_number(payload.get("strength_y_compression_mpa")),
                    finite_number(payload.get("strength_s_mpa")),
                    str(payload.get("aliases") or ""),
                    str(payload.get("notes") or ""),
                    str(payload.get("mechanical_notes") or ""),
                    str(payload.get("geometry_notes") or ""),
                    now,
                    core_id,
                ),
            )
            row = conn.execute("SELECT * FROM core_materials WHERE id = ?", (core_id,)).fetchone()
        if row is None:
            raise KeyError(f"Core material {core_id} not found")
        return dict(row)

    def delete_core_material(self, core_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM core_materials WHERE id = ?", (core_id,)).fetchone()
            if row is None:
                raise KeyError(f"Core material {core_id} not found")
            conn.execute("DELETE FROM core_materials WHERE id = ?", (core_id,))
        return dict(row)

    def delete_specimen(self, specimen_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM specimens WHERE id = ?", (specimen_id,)).fetchone()
            if row is None:
                raise KeyError(f"Specimen {specimen_id} not found")
            conn.execute("DELETE FROM specimens WHERE id = ?", (specimen_id,))
        return self._inflate(dict(row))

    def list_cars(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM cars ORDER BY name").fetchall()
        return [self._inflate_car(dict(row)) for row in rows]

    def get_car(self, car_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone()
        if row is None:
            raise KeyError(f"Car {car_id} not found")
        return self._inflate_car(dict(row))

    def create_car(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Car name is required")
        panels = self._normalize_car_panels(payload.get("panels") or [])
        dashboard = payload.get("dashboard") or {}
        try:
            with self.connect() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO cars (name, panels_json, dashboard_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        json.dumps(safe_json(panels)),
                        json.dumps(safe_json(dashboard)),
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Car '{name}' already exists") from exc
        car = self.get_car(cur.lastrowid)
        car["recalculation"] = self.recalculate_probe_metrics_for_car(car["id"])
        return car

    def update_car(self, car_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as conn:
            existing = conn.execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone()
            if existing is None:
                raise KeyError(f"Car {car_id} not found")
            existing_data = self._inflate_car(dict(existing))
            panels = self._normalize_car_panels(payload.get("panels") if "panels" in payload else existing_data.get("panels") or [])
            dashboard = payload.get("dashboard") if "dashboard" in payload else existing_data.get("dashboard") or {}
            name = str(payload.get("name") if "name" in payload else existing_data.get("name") or "").strip()
            if not name:
                raise ValueError("Car name is required")
            conn.execute(
                """
                UPDATE cars
                SET name = ?, panels_json = ?, dashboard_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    json.dumps(safe_json(panels)),
                    json.dumps(safe_json(dashboard)),
                    utc_now(),
                    car_id,
                ),
            )
            row = conn.execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone()
        if row is None:
            raise KeyError(f"Car {car_id} not found")
        car = self._inflate_car(dict(row))
        car["recalculation"] = self.recalculate_probe_metrics_for_car(car["id"])
        return car

    def delete_car(self, car_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone()
            if row is None:
                raise KeyError(f"Car {car_id} not found")
            conn.execute("DELETE FROM cars WHERE id = ?", (car_id,))
        return self._inflate_car(dict(row))

    def list_car_probe_metrics(self, car_id: int) -> list[dict[str, Any]]:
        self.get_car(car_id)
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT car_id, specimen_id, metrics_json, status, error, updated_at
                FROM car_probe_metrics
                WHERE car_id = ?
                ORDER BY specimen_id
                """,
                (car_id,),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["metrics"] = json.loads(item.pop("metrics_json") or "{}")
            out.append(item)
        return out

    def recalculate_probe_metrics_for_car(self, car_id: int) -> dict[str, Any]:
        car = self.get_car(car_id)
        now = utc_now()
        failed: list[dict[str, str]] = []
        succeeded = 0
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM specimens ORDER BY id").fetchall()
            for row in rows:
                specimen_id = row["id"]
                try:
                    specimen = self._inflate(dict(row))
                    metrics = self._car_specific_probe_metrics(specimen, car)
                    conn.execute(
                        """
                        INSERT INTO car_probe_metrics
                            (car_id, specimen_id, metrics_json, status, error, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(car_id, specimen_id) DO UPDATE SET
                            metrics_json = excluded.metrics_json,
                            status = excluded.status,
                            error = excluded.error,
                            updated_at = excluded.updated_at
                        """,
                        (
                            car_id,
                            specimen_id,
                            json.dumps(safe_json(metrics)),
                            "ok",
                            "",
                            now,
                        ),
                    )
                    succeeded += 1
                except Exception as exc:
                    failed.append({"specimen_id": str(specimen_id), "error": str(exc)})
                    conn.execute(
                        """
                        INSERT INTO car_probe_metrics
                            (car_id, specimen_id, metrics_json, status, error, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(car_id, specimen_id) DO UPDATE SET
                            metrics_json = excluded.metrics_json,
                            status = excluded.status,
                            error = excluded.error,
                            updated_at = excluded.updated_at
                        """,
                        (car_id, specimen_id, "{}", "error", str(exc), now),
                    )
        return {
            "car_id": car_id,
            "total": succeeded + len(failed),
            "succeeded": succeeded,
            "failed": failed,
        }

    def _panel_heights_for_car(self, car: dict[str, Any]) -> dict[str, float]:
        heights: dict[str, float] = {}
        for panel in car.get("panels") or []:
            code = panel_abbreviation(panel.get("code") or panel.get("name"))
            height = finite_number(panel.get("height_mm"))
            if height is not None:
                heights[code] = height
        return heights

    def _car_specific_probe_metrics(self, specimen: dict[str, Any], car: dict[str, Any]) -> dict[str, Any]:
        computed = specimen.get("computed") or {}
        theoretical = specimen.get("theoretical") or {}
        common = computed.get("common") or {}
        mode = str(computed.get("mode") or specimen.get("test_type") or "")
        original_panel_results = computed.get("panel_results") or {}
        panel_heights = self._panel_heights_for_car(car)

        panel_results = original_panel_results
        if original_panel_results and mode != "Shear" and common:
            core = finite_number(computed.get("core_thickness_mm"))
            if core is None:
                core = finite_number(specimen.get("core_thickness_mm"))
            if core is None:
                core = finite_number(theoretical.get("core_thickness_mm"))
            skin = finite_number(computed.get("skin_thickness_each_side_mm"))
            if skin is None:
                skin = finite_number(specimen.get("skin_thickness_mm"))
            if skin is None:
                skin = finite_number(theoretical.get("skin_thickness_equivalent_mm"))
            top_skin = finite_number(computed.get("top_skin_thickness_mm"), specimen.get("top_skin_thickness_mm"))
            bottom_skin = finite_number(computed.get("bottom_skin_thickness_mm"), specimen.get("bottom_skin_thickness_mm"))
            total_skin = finite_number(computed.get("total_skin_thickness_mm"))
            if total_skin is None:
                total_skin = finite_number(theoretical.get("total_skin_thickness_mm"))
            if total_skin is None and top_skin is not None and bottom_skin is not None:
                total_skin = top_skin + bottom_skin
            specimen_length = finite_number(theoretical.get("specimen_length_mm"), DEFAULT_SPECIMEN_LENGTH_MM)
            if core is None or skin is None or total_skin is None:
                raise ValueError("Probe is missing core/skin data for car-specific EI recalculation")
            panel_results = compute_3pb_panel_results(
                common,
                core_thickness_mm=core,
                skin_thickness_mm=skin,
                skin_total_thickness_mm=total_skin,
                specimen_length_mm=specimen_length or DEFAULT_SPECIMEN_LENGTH_MM,
                span_mm=DEFAULT_SPAN_MM,
                panel_heights_mm=panel_heights,
            )

        cs_ei_by_panel = {
            panel_code: values.get("cs_ei")
            for panel_code, values in (panel_results or {}).items()
            if isinstance(values, dict)
        }
        perimeter_shear_by_panel = {
            panel_code: values.get("cs_perimeter_shear")
            for panel_code, values in (panel_results or {}).items()
            if isinstance(values, dict)
        }
        return {
            "car_id": car.get("id"),
            "car_name": car.get("name"),
            "specimen_id": specimen.get("id"),
            "test_type": specimen.get("test_type"),
            "panel_heights_mm": panel_heights,
            "panel_results": panel_results,
            "cs_ei_by_panel": cs_ei_by_panel,
            "perimeter_shear_by_panel": perimeter_shear_by_panel,
            "updated_at": utc_now(),
        }

    def calculate_monocoque_weight(self, payload: dict[str, Any]) -> dict[str, Any]:
        car_id = int(payload.get("car_id") or 0)
        car = self.get_car(car_id)
        assignments = dict(payload.get("assignments") or {})
        if payload.get("front_hoop_volume_m3") is not None:
            front_volume_m3 = float(payload.get("front_hoop_volume_m3") or 0)
        else:
            front_volume_m3 = float(payload.get("front_hoop_volume_mm3") or 0) / 1_000_000_000.0
        if payload.get("front_hoop_density_kg_m3") is not None:
            front_density_kg_m3 = float(payload.get("front_hoop_density_kg_m3") or 0)
        else:
            front_density_kg_m3 = float(payload.get("front_hoop_density_kg_mm3") or 0) * 1_000_000_000.0
        hardpoints_weight_g = float(payload.get("hardpoints_weight_g") or 0)

        rows: list[dict[str, Any]] = []
        total_theoretical = 0.0
        total_real = 0.0
        for panel in car["panels"]:
            panel_key = str(panel.get("id") or panel.get("code") or panel.get("name"))
            specimen_id = assignments.get(panel_key) or assignments.get(panel.get("name")) or assignments.get(panel.get("code")) or ""
            area_mm2 = float(panel.get("area_mm2") or 0)
            multiplier = float(panel.get("multiplier") or 1)
            theoretical_weight = None
            real_weight = None
            delta = None
            sequence = ""
            specimen_area_m2 = None
            if specimen_id:
                try:
                    specimen = self.get_specimen(str(specimen_id))
                    theoretical = specimen.get("theoretical", {}) or {}
                    specimen_area_m2 = float(theoretical.get("area_m2") or 0)
                    if specimen_area_m2 > 0 and area_mm2 > 0:
                        scale = (area_mm2 / 1_000_000.0) / specimen_area_m2 * multiplier
                        base_theoretical = theoretical.get("total_weight_g")
                        base_real = specimen.get("real_weight_g")
                        theoretical_weight = float(base_theoretical) * scale if base_theoretical is not None else None
                        if base_real is not None:
                            real_weight = float(base_real) * scale
                        elif base_theoretical is not None:
                            real_weight = float(base_theoretical) * scale
                        if theoretical_weight is not None:
                            total_theoretical += theoretical_weight
                        if real_weight is not None:
                            total_real += real_weight
                        if theoretical_weight is not None and real_weight is not None:
                            delta = real_weight - theoretical_weight
                    sequence = theoretical.get("laminate_sequence") or laminate_sequence(specimen.get("laminate"))
                except (KeyError, TypeError, ValueError):
                    sequence = "Specimen not found"

            rows.append(
                {
                    "panel_id": panel_key,
                    "panel_name": panel.get("name"),
                    "panel_code": panel.get("code"),
                    "area_mm2": area_mm2,
                    "height_mm": float(panel.get("height_mm") or 0),
                    "multiplier": multiplier,
                    "specimen_id": specimen_id,
                    "specimen_area_m2": specimen_area_m2,
                    "laminate_sequence": sequence,
                    "theoretical_weight_g": theoretical_weight,
                    "real_weight_g": real_weight,
                    "delta_g": delta,
                }
            )

        front_hoop_weight_kg = front_volume_m3 * front_density_kg_m3
        front_hoop_weight_g = front_hoop_weight_kg * 1000.0
        final_total_g = total_real + front_hoop_weight_g + hardpoints_weight_g
        return {
            "car": car,
            "assignments": assignments,
            "panels": rows,
            "front_hoop_volume_m3": front_volume_m3,
            "front_hoop_density_kg_m3": front_density_kg_m3,
            "front_hoop_volume_mm3": front_volume_m3 * 1_000_000_000.0,
            "front_hoop_density_kg_mm3": front_density_kg_m3 / 1_000_000_000.0,
            "front_hoop_weight_kg": front_hoop_weight_kg,
            "front_hoop_weight_g": front_hoop_weight_g,
            "hardpoints_weight_g": hardpoints_weight_g,
            "total_theoretical_monocoque_g": total_theoretical,
            "total_real_monocoque_g": total_real,
            "final_total_weight_g": final_total_g,
        }

    def save_monocoque_weight(self, payload: dict[str, Any]) -> dict[str, Any]:
        computed = self.calculate_monocoque_weight(payload)
        now = utc_now()
        calc_id = payload.get("id")
        fields = {
            "name": str(payload.get("name") or f"Monocoque weight {now}").strip(),
            "car_id": payload.get("car_id"),
            "car_snapshot_json": json.dumps(safe_json(computed.get("car", {}))),
            "assignments_json": json.dumps(safe_json(computed.get("assignments") or {})),
            "front_hoop_volume_mm3": computed.get("front_hoop_volume_mm3"),
            "front_hoop_density_kg_mm3": computed.get("front_hoop_density_kg_mm3"),
            "hardpoints_weight_g": payload.get("hardpoints_weight_g"),
            "computed_json": json.dumps(safe_json(computed)),
            "updated_at": now,
        }
        with self.connect() as conn:
            if calc_id:
                fields["id"] = int(calc_id)
                conn.execute(
                    """
                    UPDATE monocoque_weight_calculations SET
                        name = :name,
                        car_id = :car_id,
                        car_snapshot_json = :car_snapshot_json,
                        assignments_json = :assignments_json,
                        front_hoop_volume_mm3 = :front_hoop_volume_mm3,
                        front_hoop_density_kg_mm3 = :front_hoop_density_kg_mm3,
                        hardpoints_weight_g = :hardpoints_weight_g,
                        computed_json = :computed_json,
                        updated_at = :updated_at
                    WHERE id = :id
                    """,
                    fields,
                )
                saved_id = int(calc_id)
            else:
                fields["created_at"] = now
                cur = conn.execute(
                    """
                    INSERT INTO monocoque_weight_calculations (
                        name, car_id, car_snapshot_json, assignments_json, front_hoop_volume_mm3,
                        front_hoop_density_kg_mm3, hardpoints_weight_g, computed_json, created_at, updated_at
                    ) VALUES (
                        :name, :car_id, :car_snapshot_json, :assignments_json, :front_hoop_volume_mm3,
                        :front_hoop_density_kg_mm3, :hardpoints_weight_g, :computed_json, :created_at, :updated_at
                    )
                    """,
                    fields,
                )
                saved_id = cur.lastrowid
        return self.get_monocoque_weight(saved_id)

    def list_monocoque_weights(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, car_id, car_snapshot_json, computed_json, updated_at
                FROM monocoque_weight_calculations
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [self._inflate_monocoque_summary(dict(row)) for row in rows]

    def get_monocoque_weight(self, calc_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM monocoque_weight_calculations WHERE id = ?", (calc_id,)).fetchone()
        if row is None:
            raise KeyError(f"Monocoque calculation {calc_id} not found")
        return self._inflate_monocoque(dict(row))

    def update_monocoque_weight_metadata(self, calc_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Calculation name is required")
        now = utc_now()
        with self.connect() as conn:
            row = conn.execute("SELECT 1 FROM monocoque_weight_calculations WHERE id = ?", (calc_id,)).fetchone()
            if row is None:
                raise KeyError(f"Monocoque calculation {calc_id} not found")
            conn.execute(
                "UPDATE monocoque_weight_calculations SET name = ?, updated_at = ? WHERE id = ?",
                (name, now, calc_id),
            )
        return self.get_monocoque_weight(calc_id)

    def delete_monocoque_weight(self, calc_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT id FROM monocoque_weight_calculations WHERE id = ?", (calc_id,)).fetchone()
            if row is None:
                raise KeyError(f"Monocoque calculation {calc_id} not found")
            conn.execute("DELETE FROM monocoque_weight_calculations WHERE id = ?", (calc_id,))
        return {"deleted": calc_id}

    def upsert_specimen(self, payload: dict[str, Any]) -> dict[str, Any]:
        specimen_id = str(payload["id"]).strip()
        if not specimen_id:
            raise ValueError("Specimen ID is required")
        now = utc_now()

        fields = {
            "id": specimen_id,
            "test_type": payload.get("test_type") or "3PB",
            "laminate_json": json.dumps(safe_json(payload.get("laminate", []))),
            "theoretical_json": json.dumps(safe_json(payload.get("theoretical", {}))),
            "real_weight_g": payload.get("real_weight_g"),
            "real_thickness_mm": payload.get("real_thickness_mm"),
            "core_material": payload.get("core_material"),
            "core_thickness_mm": payload.get("core_thickness_mm"),
            "skin_thickness_mm": payload.get("skin_thickness_mm"),
            "top_skin_thickness_mm": payload.get("top_skin_thickness_mm"),
            "bottom_skin_thickness_mm": payload.get("bottom_skin_thickness_mm"),
            "computed_json": json.dumps(safe_json(payload.get("computed", {}))),
            "raw_points_json": json.dumps(safe_json(payload.get("raw_points", []))),
            "reduced_points_json": json.dumps(safe_json(payload.get("reduced_points", []))),
            "selected_points_json": json.dumps(safe_json(payload.get("selected_points", []))),
            "comments": payload.get("comments"),
            "source_filename": payload.get("source_filename"),
            "updated_at": now,
        }
        with self.connect() as conn:
            exists = conn.execute("SELECT 1 FROM specimens WHERE id = ?", (specimen_id,)).fetchone()
            if exists:
                conn.execute(
                    """
                    UPDATE specimens SET
                        test_type = :test_type,
                        laminate_json = :laminate_json,
                        theoretical_json = :theoretical_json,
                        real_weight_g = :real_weight_g,
                        real_thickness_mm = :real_thickness_mm,
                        core_material = :core_material,
                        core_thickness_mm = :core_thickness_mm,
                        skin_thickness_mm = :skin_thickness_mm,
                        top_skin_thickness_mm = :top_skin_thickness_mm,
                        bottom_skin_thickness_mm = :bottom_skin_thickness_mm,
                        computed_json = :computed_json,
                        raw_points_json = :raw_points_json,
                        reduced_points_json = :reduced_points_json,
                        selected_points_json = :selected_points_json,
                        comments = :comments,
                        source_filename = :source_filename,
                        updated_at = :updated_at
                    WHERE id = :id
                    """,
                    fields,
                )
            else:
                fields["created_at"] = now
                conn.execute(
                    """
                    INSERT INTO specimens (
                        id, test_type, laminate_json, theoretical_json, real_weight_g, real_thickness_mm,
                        core_material, core_thickness_mm, skin_thickness_mm, top_skin_thickness_mm,
                        bottom_skin_thickness_mm, computed_json, raw_points_json,
                        reduced_points_json, selected_points_json, comments, source_filename, created_at, updated_at
                    ) VALUES (
                        :id, :test_type, :laminate_json, :theoretical_json, :real_weight_g, :real_thickness_mm,
                        :core_material, :core_thickness_mm, :skin_thickness_mm, :top_skin_thickness_mm,
                        :bottom_skin_thickness_mm, :computed_json, :raw_points_json,
                        :reduced_points_json, :selected_points_json, :comments, :source_filename, :created_at, :updated_at
                    )
                    """,
                    fields,
                )
        return self.get_specimen(specimen_id)

    def list_specimens(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, test_type, real_weight_g, real_thickness_mm, core_material,
                       core_thickness_mm, top_skin_thickness_mm, bottom_skin_thickness_mm,
                       laminate_json, theoretical_json, computed_json, raw_points_json, selected_points_json, updated_at
                FROM specimens
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [self._summary(dict(row)) for row in rows]

    def get_specimen(self, specimen_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM specimens WHERE id = ?", (specimen_id,)).fetchone()
        if row is None:
            raise KeyError(f"Specimen {specimen_id} not found")
        return self._inflate(dict(row))

    def _inflate(self, row: dict[str, Any]) -> dict[str, Any]:
        inflated = dict(row)
        inflated["laminate"] = decode_json_field(inflated.pop("laminate_json"), [])
        inflated["theoretical"] = decode_json_field(inflated.pop("theoretical_json"), {})
        inflated["computed"] = decode_json_field(inflated.pop("computed_json"), {})
        inflated["raw_points"] = decode_json_field(inflated.pop("raw_points_json"), [])
        inflated["reduced_points"] = decode_json_field(inflated.pop("reduced_points_json"), [])
        inflated["selected_points"] = decode_json_field(inflated.pop("selected_points_json"), [])
        energy = self._energy_absorbed_value(
            inflated.get("test_type"),
            inflated.get("computed"),
            inflated.get("raw_points"),
        )
        if energy is not None:
            inflated["energyAbsorbedJ"] = energy
            inflated["energy_absorbed_j"] = energy
            common = inflated.setdefault("computed", {}).setdefault("common", {})
            if isinstance(common, dict):
                common["energyAbsorbedJ"] = energy
                common["energy_absorbed_j"] = energy
        return inflated

    def _normalize_car_panels(self, panels: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for index, panel in enumerate(panels, start=1):
            name = str(panel.get("name") or panel.get("code") or f"Panel {index}").strip()
            code = str(panel.get("code") or name).strip()
            abbreviated = panel_abbreviation(code or name)
            area = float(panel.get("area_mm2") or 0)
            height = finite_number(panel.get("height_mm"), DEFAULT_PANEL_HEIGHTS_MM.get(abbreviated, 0.0)) or 0.0
            multiplier = float(panel.get("multiplier") or 1)
            normalized.append(
                {
                    "id": str(panel.get("id") or code or name),
                    "name": name,
                    "code": code,
                    "area_mm2": area,
                    "height_mm": height,
                    "multiplier": multiplier,
                }
            )
        return normalized

    def _panel_key(self, panel: dict[str, Any]) -> str:
        return str(panel.get("id") or panel.get("code") or panel.get("name") or "")

    def _is_fhb_panel(self, panel: dict[str, Any]) -> bool:
        return panel_abbreviation(panel.get("code") or panel.get("name")) == "FHB"

    def _is_dashboard_panel(self, panel: dict[str, Any]) -> bool:
        return panel_abbreviation(panel.get("code") or panel.get("name")) == "Dashboard"

    def _sync_dashboard_assignments(self, car: dict[str, Any], assignments: dict[str, Any]) -> dict[str, Any]:
        return dict(assignments or {})

    def _inflate_car(self, row: dict[str, Any]) -> dict[str, Any]:
        inflated = dict(row)
        inflated["panels"] = self._normalize_car_panels(decode_json_field(inflated.pop("panels_json"), []))
        inflated["dashboard"] = decode_json_field(inflated.pop("dashboard_json"), {})
        return inflated

    def _inflate_monocoque(self, row: dict[str, Any]) -> dict[str, Any]:
        inflated = dict(row)
        inflated["car_snapshot"] = decode_json_field(inflated.pop("car_snapshot_json"), {})
        inflated["assignments"] = decode_json_field(inflated.pop("assignments_json"), {})
        inflated["computed"] = decode_json_field(inflated.pop("computed_json"), {})
        inflated["front_hoop_volume_m3"] = float(inflated.get("front_hoop_volume_mm3") or 0) / 1_000_000_000.0
        inflated["front_hoop_density_kg_m3"] = float(inflated.get("front_hoop_density_kg_mm3") or 0) * 1_000_000_000.0
        car = inflated.get("car_snapshot") or {}
        if inflated.get("car_id"):
            try:
                car = self.get_car(int(inflated["car_id"]))
            except KeyError:
                pass
        inflated["assignments"] = self._sync_dashboard_assignments(car, inflated["assignments"])
        if isinstance(inflated.get("computed"), dict):
            inflated["computed"]["assignments"] = self._sync_dashboard_assignments(car, inflated["computed"].get("assignments") or inflated["assignments"])
        return inflated

    def _inflate_monocoque_summary(self, row: dict[str, Any]) -> dict[str, Any]:
        inflated = dict(row)
        car = decode_json_field(inflated.pop("car_snapshot_json"), {})
        computed = decode_json_field(inflated.pop("computed_json"), {})
        inflated["car_name"] = car.get("name")
        inflated["total_real_monocoque_g"] = computed.get("total_real_monocoque_g")
        inflated["final_total_weight_g"] = computed.get("final_total_weight_g")
        return inflated

    def _summary(self, row: dict[str, Any]) -> dict[str, Any]:
        laminate = decode_json_field(row.pop("laminate_json"), {})
        theoretical = decode_json_field(row.pop("theoretical_json"), {})
        computed = decode_json_field(row.pop("computed_json"), {})
        raw_points = decode_json_field(row.pop("raw_points_json", []), [])
        selected = decode_json_field(row.pop("selected_points_json"), [])
        panel_results = computed.get("panel_results", {}) if isinstance(computed, dict) else {}
        cs_values = []
        for panel in panel_results.values():
            for key, value in panel.items():
                if key.startswith("cs_") and isinstance(value, (int, float)):
                    cs_values.append(float(value))
        row["theoretical_weight_g"] = theoretical.get("total_weight_g")
        row["theoretical_thickness_mm"] = theoretical.get("total_thickness_mm")
        row["zero_percent"] = theoretical.get("zero_percent")
        row["warping_percent"] = theoretical.get("warping_percent")
        formatted_sequence = laminate_sequence(laminate)
        row["laminate_sequence"] = formatted_sequence if formatted_sequence != "Incomplete laminate" else theoretical.get("laminate_sequence")
        core = theoretical.get("core", {}) if isinstance(theoretical, dict) else {}
        row["core_type"] = core.get("type") or row.get("core_material")
        row["panel_results"] = panel_results
        energy = self._energy_absorbed_value(row.get("test_type"), computed, raw_points)
        row["energyAbsorbedJ"] = energy
        row["energy_absorbed_j"] = energy
        if str(row.get("test_type", "")).upper().startswith("SHEAR") or computed.get("mode") == "Shear":
            row["perimeter_shear_by_panel"] = {
                panel_code: values.get("cs_perimeter_shear")
                for panel_code, values in panel_results.items()
                if isinstance(values, dict)
            }
            row["perimeter_shear_cs"] = row["perimeter_shear_by_panel"].get("FBH")
        else:
            row["cs_ei_by_panel"] = {
                panel_code: values.get("cs_ei")
                for panel_code, values in panel_results.items()
                if isinstance(values, dict)
            }
            row["perimeter_shear_by_panel"] = {}
        row["selected_points"] = selected
        return row

    def _energy_absorbed_value(
        self,
        test_type: Any,
        computed: dict[str, Any] | None,
        raw_points: list[dict[str, Any]] | None = None,
    ) -> float | None:
        computed = computed if isinstance(computed, dict) else {}
        common = computed.get("common", {}) if isinstance(computed.get("common"), dict) else {}
        candidates = (
            common.get("energyAbsorbedJ"),
            common.get("energy_absorbed_j"),
            common.get("energyAbsorbed"),
            computed.get("energyAbsorbedJ"),
            computed.get("energy_absorbed_j"),
            computed.get("energyAbsorbed"),
        )
        for candidate in candidates:
            number = finite_number(candidate)
            if number is not None:
                return number
        if is_energy_absorbed_test(test_type) and raw_points:
            calculated = energy_absorbed_until_displacement(raw_points, target_mm=12.7).get("energyAbsorbedJ")
            return finite_number(calculated)
        return None
