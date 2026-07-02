from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .calculations import CORE_MATERIALS, DEFAULT_MATERIALS, Material, safe_json
from .db import DEFAULT_CAR_PANELS, Database, utc_now


def normalize_supabase_url(url: str) -> str:
    """Return the project base URL, not a dashboard/rest/auth sub-path."""
    raw = str(url or "").strip().rstrip("/")
    if not raw:
        return raw
    parts = urlsplit(raw)
    path = parts.path.rstrip("/")
    for suffix in ("/rest/v1", "/auth/v1", "/storage/v1"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    if parts.netloc == "supabase.com" and "/dashboard/project/" in path:
        project_ref = path.split("/dashboard/project/", 1)[1].split("/", 1)[0]
        if project_ref:
            return f"https://{project_ref}.supabase.co"
    return urlunsplit((parts.scheme, parts.netloc, path, "", "")).rstrip("/")


class SupabaseDatabase(Database):
    """Database adapter backed by Supabase PostgREST.

    The backend uses the service-role key server-side only. The frontend never
    receives this key; edit authorization is enforced before write endpoints.
    """

    def __init__(self, url: str, service_role_key: str):
        self.url = normalize_supabase_url(url)
        self.rest_url = f"{self.url}/rest/v1"
        self.service_role_key = service_role_key
        self._seed_defaults()

    def _request(
        self,
        method: str,
        path: str,
        payload: Any | None = None,
        prefer: str | None = None,
    ) -> Any:
        body = None if payload is None else json.dumps(safe_json(payload)).encode("utf-8")
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        request = Request(f"{self.rest_url}{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raw_error = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Supabase {method} {path} failed: {exc.code} {raw_error}") from exc
        except Exception as exc:
            raise RuntimeError(f"Supabase {method} {path} failed: {exc}") from exc
        return json.loads(raw) if raw else None

    def _list(self, table: str, query: str = "select=*") -> list[dict[str, Any]]:
        result = self._request("GET", f"/{table}?{query}")
        return result if isinstance(result, list) else []

    def _single(self, table: str, key: str, value: Any, label: str) -> dict[str, Any]:
        rows = self._list(table, f"select=*&{key}=eq.{quote(str(value), safe='')}&limit=1")
        if not rows:
            raise KeyError(f"{label} {value} not found")
        return rows[0]

    def _insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._request("POST", f"/{table}", payload, prefer="return=representation")
        return rows[0] if rows else {}

    def _patch(self, table: str, key: str, value: Any, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._request(
            "PATCH",
            f"/{table}?{key}=eq.{quote(str(value), safe='')}",
            payload,
            prefer="return=representation",
        )
        if not rows:
            raise KeyError(f"{table} row {value} not found")
        return rows[0]

    def _delete(self, table: str, key: str, value: Any) -> dict[str, Any]:
        rows = self._request(
            "DELETE",
            f"/{table}?{key}=eq.{quote(str(value), safe='')}",
            prefer="return=representation",
        )
        if not rows:
            raise KeyError(f"{table} row {value} not found")
        return rows[0]

    def _upsert(self, table: str, payload: dict[str, Any], conflict: str) -> dict[str, Any]:
        rows = self._request(
            "POST",
            f"/{table}?on_conflict={quote(conflict, safe=',')}",
            payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return rows[0] if rows else {}

    def _seed_defaults(self) -> None:
        if not self.list_materials():
            for material in DEFAULT_MATERIALS:
                self.create_material(material)
        if not self.list_core_materials():
            for core in CORE_MATERIALS:
                self.create_core_material(core)
        if not self.list_cars():
            self.create_car({"name": "MAD Formula Monocoque", "panels": DEFAULT_CAR_PANELS})

    def list_materials(self) -> list[dict[str, Any]]:
        return self._list("materials", "select=*&order=name.asc")

    def create_material(self, payload: dict[str, Any]) -> dict[str, Any]:
        material = Material.from_mapping(payload)
        if not material.name.strip():
            raise ValueError("Material name is required")
        if material.fiber_type not in {"unidirectional", "bidirectional"}:
            raise ValueError("fiber_type must be unidirectional or bidirectional")
        row = {
            "technical_id": material.technical_id.strip() or material.name.strip(),
            "name": material.name.strip(),
            "material_category": material.material_category or "fiber",
            "fiber_family": material.fiber_family,
            "thickness_mm": material.thickness_mm,
            "areal_weight_g_m2": material.areal_weight_g_m2,
            "fiber_type": material.fiber_type,
            "resin_fraction": material.resin_fraction,
            "e1_pa": material.e1_pa,
            "e2_pa": material.e2_pa,
            "g12_pa": material.g12_pa,
            "poisson_input": material.poisson_input,
            "density_kg_m3": material.density_kg_m3,
            "strength_x_mpa": material.strength_x_mpa,
            "strength_x_compression_mpa": material.strength_x_compression_mpa,
            "strength_y_mpa": material.strength_y_mpa,
            "strength_y_compression_mpa": material.strength_y_compression_mpa,
            "strength_s_mpa": material.strength_s_mpa,
            "aliases": material.aliases,
            "notes": material.notes,
            "created_at": utc_now(),
        }
        return self._insert("materials", row)

    def update_material(self, material_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._single("materials", "id", material_id, "Material")
        merged = {**existing, **payload, "id": material_id}
        material = Material.from_mapping(merged)
        row = {
            "technical_id": material.technical_id.strip() or material.name.strip(),
            "name": material.name.strip(),
            "material_category": material.material_category or "fiber",
            "fiber_family": material.fiber_family,
            "thickness_mm": material.thickness_mm,
            "areal_weight_g_m2": material.areal_weight_g_m2,
            "fiber_type": material.fiber_type,
            "resin_fraction": material.resin_fraction,
            "e1_pa": material.e1_pa,
            "e2_pa": material.e2_pa,
            "g12_pa": material.g12_pa,
            "poisson_input": material.poisson_input,
            "density_kg_m3": material.density_kg_m3,
            "strength_x_mpa": material.strength_x_mpa,
            "strength_x_compression_mpa": material.strength_x_compression_mpa,
            "strength_y_mpa": material.strength_y_mpa,
            "strength_y_compression_mpa": material.strength_y_compression_mpa,
            "strength_s_mpa": material.strength_s_mpa,
            "aliases": material.aliases,
            "notes": material.notes,
        }
        return self._patch("materials", "id", material_id, row)

    def delete_material(self, material_id: int) -> dict[str, Any]:
        return self._delete("materials", "id", material_id)

    def list_core_materials(self) -> list[dict[str, Any]]:
        return self._list("core_materials", "select=*&order=name.asc")

    def create_core_material(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not str(payload.get("name") or "").strip():
            raise ValueError("Core material name is required")
        key = str(payload.get("key") or payload.get("name") or "core").strip().lower()
        key = "".join(ch if ch.isalnum() else "_" for ch in key).strip("_")
        now = utc_now()
        row = {
            "key": key,
            "technical_id": str(payload.get("technical_id") or key).strip(),
            "name": str(payload["name"]).strip(),
            "type": str(payload.get("type") or "core").strip(),
            "material_category": str(payload.get("material_category") or "core").strip(),
            "fiber_family": str(payload.get("fiber_family") or "").strip(),
            "thickness_mm": float(payload["thickness_mm"]),
            "density_kg_m3": float(payload.get("density_kg_m3") or 0),
            "e1_pa": payload.get("e1_pa"),
            "e2_pa": payload.get("e2_pa"),
            "g12_pa": payload.get("g12_pa"),
            "poisson_input": payload.get("poisson_input"),
            "strength_x_mpa": payload.get("strength_x_mpa"),
            "strength_x_compression_mpa": payload.get("strength_x_compression_mpa"),
            "strength_y_mpa": payload.get("strength_y_mpa"),
            "strength_y_compression_mpa": payload.get("strength_y_compression_mpa"),
            "strength_s_mpa": payload.get("strength_s_mpa"),
            "aliases": str(payload.get("aliases") or ""),
            "notes": str(payload.get("notes") or ""),
            "mechanical_notes": str(payload.get("mechanical_notes") or ""),
            "geometry_notes": str(payload.get("geometry_notes") or ""),
            "created_at": now,
            "updated_at": now,
        }
        return self._insert("core_materials", row)

    def update_core_material(self, core_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._single("core_materials", "id", core_id, "Core material")
        merged = {**existing, **payload}
        key = str(merged.get("key") or merged.get("name") or "core").strip().lower()
        key = "".join(ch if ch.isalnum() else "_" for ch in key).strip("_")
        row = {
            **merged,
            "key": key,
            "technical_id": str(merged.get("technical_id") or key).strip(),
            "name": str(merged["name"]).strip(),
            "type": str(merged.get("type") or "core").strip(),
            "material_category": str(merged.get("material_category") or "core").strip(),
            "fiber_family": str(merged.get("fiber_family") or "").strip(),
            "thickness_mm": float(merged["thickness_mm"]),
            "density_kg_m3": float(merged.get("density_kg_m3") or 0),
            "updated_at": utc_now(),
        }
        row.pop("id", None)
        row.pop("created_at", None)
        return self._patch("core_materials", "id", core_id, row)

    def delete_core_material(self, core_id: int) -> dict[str, Any]:
        return self._delete("core_materials", "id", core_id)

    def list_cars(self) -> list[dict[str, Any]]:
        return [self._inflate_car(row) for row in self._list("cars", "select=*&order=name.asc")]

    def get_car(self, car_id: int) -> dict[str, Any]:
        return self._inflate_car(self._single("cars", "id", car_id, "Car"))

    def create_car(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Car name is required")
        row = self._insert(
            "cars",
            {
                "name": name,
                "panels_json": self._normalize_car_panels(payload.get("panels") or []),
                "dashboard_json": payload.get("dashboard") or {},
                "created_at": now,
                "updated_at": now,
            },
        )
        car = self._inflate_car(row)
        car["recalculation"] = self.recalculate_probe_metrics_for_car(car["id"])
        return car

    def update_car(self, car_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_car(car_id)
        name = str(payload.get("name") if "name" in payload else existing.get("name") or "").strip()
        if not name:
            raise ValueError("Car name is required")
        row = self._patch(
            "cars",
            "id",
            car_id,
            {
                "name": name,
                "panels_json": self._normalize_car_panels(payload.get("panels") if "panels" in payload else existing.get("panels") or []),
                "dashboard_json": payload.get("dashboard") if "dashboard" in payload else existing.get("dashboard") or {},
                "updated_at": utc_now(),
            },
        )
        car = self._inflate_car(row)
        car["recalculation"] = self.recalculate_probe_metrics_for_car(car["id"])
        return car

    def delete_car(self, car_id: int) -> dict[str, Any]:
        return self._inflate_car(self._delete("cars", "id", car_id))

    def list_car_probe_metrics(self, car_id: int) -> list[dict[str, Any]]:
        self.get_car(car_id)
        rows = self._list("car_probe_metrics", f"select=*&car_id=eq.{int(car_id)}&order=specimen_id.asc")
        for row in rows:
            row["metrics"] = row.pop("metrics_json") or {}
        return rows

    def recalculate_probe_metrics_for_car(self, car_id: int) -> dict[str, Any]:
        car = self.get_car(car_id)
        failed: list[dict[str, str]] = []
        succeeded = 0
        for row in self._list("specimens", "select=*&order=id.asc"):
            specimen_id = row["id"]
            try:
                metrics = self._car_specific_probe_metrics(self._inflate(row), car)
                self._upsert(
                    "car_probe_metrics",
                    {
                        "car_id": car_id,
                        "specimen_id": specimen_id,
                        "metrics_json": metrics,
                        "status": "ok",
                        "error": "",
                        "updated_at": utc_now(),
                    },
                    "car_id,specimen_id",
                )
                succeeded += 1
            except Exception as exc:
                failed.append({"specimen_id": str(specimen_id), "error": str(exc)})
                self._upsert(
                    "car_probe_metrics",
                    {
                        "car_id": car_id,
                        "specimen_id": specimen_id,
                        "metrics_json": {},
                        "status": "error",
                        "error": str(exc),
                        "updated_at": utc_now(),
                    },
                    "car_id,specimen_id",
                )
        return {"car_id": car_id, "total": succeeded + len(failed), "succeeded": succeeded, "failed": failed}

    def upsert_specimen(self, payload: dict[str, Any]) -> dict[str, Any]:
        specimen_id = str(payload["id"]).strip()
        if not specimen_id:
            raise ValueError("Specimen ID is required")
        now = utc_now()
        existing = []
        try:
            existing = self._list("specimens", f"select=created_at&id=eq.{quote(specimen_id, safe='')}&limit=1")
        except Exception:
            existing = []
        row = {
            "id": specimen_id,
            "test_type": payload.get("test_type") or "3PB",
            "laminate_json": payload.get("laminate", []),
            "theoretical_json": payload.get("theoretical", {}),
            "real_weight_g": payload.get("real_weight_g"),
            "real_thickness_mm": payload.get("real_thickness_mm"),
            "core_material": payload.get("core_material"),
            "core_thickness_mm": payload.get("core_thickness_mm"),
            "skin_thickness_mm": payload.get("skin_thickness_mm"),
            "top_skin_thickness_mm": payload.get("top_skin_thickness_mm"),
            "bottom_skin_thickness_mm": payload.get("bottom_skin_thickness_mm"),
            "computed_json": payload.get("computed", {}),
            "raw_points_json": payload.get("raw_points", []),
            "reduced_points_json": payload.get("reduced_points", []),
            "selected_points_json": payload.get("selected_points", []),
            "comments": payload.get("comments"),
            "source_filename": payload.get("source_filename"),
            "updated_at": now,
        }
        if not existing:
            row["created_at"] = now
        self._upsert("specimens", row, "id")
        return self.get_specimen(specimen_id)

    def list_specimens(self) -> list[dict[str, Any]]:
        rows = self._list(
            "specimens",
            "select=id,test_type,real_weight_g,real_thickness_mm,core_material,core_thickness_mm,"
            "top_skin_thickness_mm,bottom_skin_thickness_mm,laminate_json,theoretical_json,"
            "computed_json,raw_points_json,selected_points_json,updated_at&order=updated_at.desc",
        )
        return [self._summary(row) for row in rows]

    def get_specimen(self, specimen_id: str) -> dict[str, Any]:
        return self._inflate(self._single("specimens", "id", specimen_id, "Specimen"))

    def delete_specimen(self, specimen_id: str) -> dict[str, Any]:
        return self._inflate(self._delete("specimens", "id", specimen_id))

    def save_monocoque_weight(self, payload: dict[str, Any]) -> dict[str, Any]:
        computed = self.calculate_monocoque_weight(payload)
        now = utc_now()
        row = {
            "name": str(payload.get("name") or f"Monocoque weight {now}").strip(),
            "car_id": payload.get("car_id"),
            "car_snapshot_json": computed.get("car", {}),
            "assignments_json": computed.get("assignments") or {},
            "front_hoop_volume_mm3": computed.get("front_hoop_volume_mm3"),
            "front_hoop_density_kg_mm3": computed.get("front_hoop_density_kg_mm3"),
            "hardpoints_weight_g": payload.get("hardpoints_weight_g"),
            "computed_json": computed,
            "updated_at": now,
        }
        if payload.get("id"):
            saved = self._patch("monocoque_weight_calculations", "id", int(payload["id"]), row)
        else:
            row["created_at"] = now
            saved = self._insert("monocoque_weight_calculations", row)
        return self._inflate_monocoque(saved)

    def list_monocoque_weights(self) -> list[dict[str, Any]]:
        rows = self._list(
            "monocoque_weight_calculations",
            "select=id,name,car_id,car_snapshot_json,computed_json,updated_at&order=updated_at.desc",
        )
        return [self._inflate_monocoque_summary(row) for row in rows]

    def get_monocoque_weight(self, calc_id: int) -> dict[str, Any]:
        return self._inflate_monocoque(self._single("monocoque_weight_calculations", "id", calc_id, "Monocoque calculation"))

    def update_monocoque_weight_metadata(self, calc_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Calculation name is required")
        return self._inflate_monocoque(
            self._patch("monocoque_weight_calculations", "id", calc_id, {"name": name, "updated_at": utc_now()})
        )

    def delete_monocoque_weight(self, calc_id: int) -> dict[str, Any]:
        self._delete("monocoque_weight_calculations", "id", calc_id)
        return {"deleted": calc_id}


def should_use_supabase() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
