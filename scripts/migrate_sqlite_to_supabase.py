from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ses_engine.db import Database
from ses_engine.supabase_db import SupabaseDatabase


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def find_by_name(rows: list[dict], name: str) -> dict | None:
    normalized = str(name or "").strip().lower()
    return next((row for row in rows if str(row.get("name") or "").strip().lower() == normalized), None)


def main() -> None:
    sqlite_db = Database(ROOT / "data" / "ses.sqlite3")
    supabase_db = SupabaseDatabase(
        require_env("SUPABASE_URL"),
        require_env("SUPABASE_SERVICE_ROLE_KEY"),
    )

    for material in sqlite_db.list_materials():
        existing = find_by_name(supabase_db.list_materials(), material.get("name"))
        if existing:
            supabase_db.update_material(int(existing["id"]), material)
        else:
            supabase_db.create_material(material)

    for core in sqlite_db.list_core_materials():
        existing = find_by_name(supabase_db.list_core_materials(), core.get("name"))
        if existing:
            supabase_db.update_core_material(int(existing["id"]), core)
        else:
            supabase_db.create_core_material(core)

    car_id_map: dict[int, int] = {}
    for car in sqlite_db.list_cars():
        existing = find_by_name(supabase_db.list_cars(), car.get("name"))
        if existing:
            saved = supabase_db.update_car(int(existing["id"]), car)
        else:
            saved = supabase_db.create_car(car)
        car_id_map[int(car["id"])] = int(saved["id"])

    for specimen in sqlite_db.list_specimens():
        full = sqlite_db.get_specimen(specimen["id"])
        supabase_db.upsert_specimen(full)

    for calc in sqlite_db.list_monocoque_weights():
        full = sqlite_db.get_monocoque_weight(int(calc["id"]))
        old_car_id = full.get("car_id")
        if old_car_id in car_id_map:
            full["car_id"] = car_id_map[int(old_car_id)]
        full.pop("id", None)
        supabase_db.save_monocoque_weight(full)

    for car in supabase_db.list_cars():
        supabase_db.recalculate_probe_metrics_for_car(int(car["id"]))

    print("SQLite data migrated to Supabase.")


if __name__ == "__main__":
    main()
