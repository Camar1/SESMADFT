from __future__ import annotations

import io
import json
import mimetypes
import os
import sys
import traceback
import argparse
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ses_engine.calculations import (
    DEFAULT_SPECIMEN_LENGTH_MM,
    DEFAULT_SPECIMEN_WIDTH_MM,
    DEFAULT_SPAN_MM,
    Material,
    calculate_laminate,
    finite_number,
    generate_shuffle_variants,
    get_core_definition,
    panel_abbreviation,
    process_test,
    safe_json,
)
from ses_engine.db import Database
from ses_engine.supabase_db import SupabaseDatabase, should_use_supabase
from ses_engine.excel_io import export_specimen_workbook, parse_workbook_bytes


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
DATA_DIR = ROOT / "data"


def create_database():
    if should_use_supabase():
        return SupabaseDatabase(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
    return Database(DATA_DIR / "ses.sqlite3")


DB = create_database()


EDIT_AUTH_MODE = os.environ.get("EDIT_AUTH_MODE", "public").lower()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("VITE_SUPABASE_ANON_KEY") or ""
ALLOWED_ORIGINS = [origin.strip() for origin in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if origin.strip()]


def cors_origin(handler: BaseHTTPRequestHandler) -> str | None:
    origin = handler.headers.get("Origin")
    if not origin:
        return "*"
    if "*" in ALLOWED_ORIGINS or origin in ALLOWED_ORIGINS:
        return origin
    return None


def send_cors_headers(handler: BaseHTTPRequestHandler) -> None:
    origin = cors_origin(handler)
    if origin:
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Vary", "Origin")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")


def auth_required() -> bool:
    return EDIT_AUTH_MODE in {"authenticated", "auth", "login"}


def verify_bearer_token(handler: BaseHTTPRequestHandler) -> dict:
    if not auth_required():
        return {}
    if not (SUPABASE_URL and SUPABASE_ANON_KEY):
        raise PermissionError("Edit authentication is enabled but Supabase Auth is not configured")
    auth = handler.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        raise PermissionError("Login required to modify SES Platform data")
    token = auth.split(" ", 1)[1].strip()
    request = Request(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {token}",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8") or "{}")
            message = payload.get("msg") or payload.get("error_description") or payload.get("error")
        except Exception:
            message = None
        raise PermissionError(message or "Invalid or expired login session") from exc
    except Exception as exc:
        raise PermissionError("Invalid or expired login session") from exc


def require_edit_access(handler: BaseHTTPRequestHandler) -> None:
    verify_bearer_token(handler)


def read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8") or "{}")


def material_catalog() -> list[Material]:
    return [Material.from_mapping(row) for row in DB.list_materials()]


def json_response(handler: BaseHTTPRequestHandler, payload, status: int = 200) -> None:
    encoded = json.dumps(safe_json(payload), ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    send_cors_headers(handler)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def error_response(handler: BaseHTTPRequestHandler, exc: Exception, status: int = 400) -> None:
    json_response(handler, {"error": str(exc)}, status=status)


def as_float(value, default=None):
    return finite_number(value, default)


class FormField:
    def __init__(self, name: str, value=None, filename: str | None = None, file_bytes: bytes | None = None):
        self.name = name
        self.value = value
        self.filename = filename
        self.file = io.BytesIO(file_bytes or b"")


def add_form_field(form: dict, field: FormField) -> None:
    if field.name in form:
        existing = form[field.name]
        if isinstance(existing, list):
            existing.append(field)
        else:
            form[field.name] = [existing, field]
    else:
        form[field.name] = field


def parse_multipart_form(handler: BaseHTTPRequestHandler) -> dict:
    content_type = handler.headers.get("Content-Type") or ""
    if "multipart/form-data" not in content_type.lower():
        raise ValueError("Expected multipart form data")
    length = int(handler.headers.get("Content-Length", "0") or 0)
    body = handler.rfile.read(length) if length else b""
    raw_message = (
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
        + body
    )
    message = BytesParser(policy=policy.default).parsebytes(raw_message)
    form: dict = {}
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename is not None:
            add_form_field(form, FormField(name=name, filename=filename, file_bytes=payload))
        else:
            charset = part.get_content_charset() or "utf-8"
            add_form_field(form, FormField(name=name, value=payload.decode(charset, errors="replace")))
    return form


def get_form_value(form: dict, name: str, default=None):
    if name not in form:
        return default
    field = form[name]
    if isinstance(field, list):
        field = field[0]
    return field.value if field.value not in ("", None) else default


def precalculate_payload(payload: dict) -> dict:
    width = as_float(payload.get("specimen_width_mm"), DEFAULT_SPECIMEN_WIDTH_MM)
    length = as_float(payload.get("specimen_length_mm"), DEFAULT_SPECIMEN_LENGTH_MM)
    laminate = payload.get("laminate")
    if laminate is None:
        laminate = payload.get("layers", [])
    return calculate_laminate(laminate, material_catalog(), specimen_width_mm=width, specimen_length_mm=length)


def store_laminate(payload: dict) -> dict:
    theoretical = precalculate_payload(payload)
    specimen = DB.upsert_specimen(
        {
            "id": payload.get("id"),
            "test_type": payload.get("test_type", "3PB"),
            "laminate": payload.get("laminate", payload.get("layers", [])),
            "theoretical": theoretical,
            "real_weight_g": as_float(payload.get("real_weight_g")),
            "real_thickness_mm": as_float(payload.get("real_thickness_mm")),
            "core_material": theoretical.get("core", {}).get("name") or payload.get("core_material"),
            "core_thickness_mm": theoretical.get("core_thickness_mm") or as_float(payload.get("core_thickness_mm")),
            "skin_thickness_mm": theoretical.get("skin_thickness_equivalent_mm") or as_float(payload.get("skin_thickness_mm")),
            "top_skin_thickness_mm": theoretical.get("top_skin_thickness_mm"),
            "bottom_skin_thickness_mm": theoretical.get("bottom_skin_thickness_mm"),
            "comments": payload.get("comments"),
        }
    )
    return specimen


def process_form(form: dict) -> dict:
    specimen_id = str(get_form_value(form, "specimen_id", "")).strip()
    if not specimen_id:
        raise ValueError("Specimen ID is required")

    if "file" not in form:
        raise ValueError("Excel file is required")
    file_item = form["file"]
    if isinstance(file_item, list):
        file_item = file_item[0]
    file_bytes = file_item.file.read()
    parsed = parse_workbook_bytes(file_bytes, include_metadata=True)

    try:
        existing = DB.get_specimen(specimen_id)
    except KeyError:
        existing = {}

    materials = material_catalog()
    laminate = existing.get("laminate") or []

    laminate_json = get_form_value(form, "laminate_json")
    if laminate_json:
        laminate = json.loads(laminate_json)
    if not laminate:
        raise ValueError("Specimen laminate is required before processing experimental data")

    specimen_width = as_float(get_form_value(form, "specimen_width_mm"), DEFAULT_SPECIMEN_WIDTH_MM)
    specimen_length = as_float(get_form_value(form, "specimen_length_mm"), DEFAULT_SPECIMEN_LENGTH_MM)
    theoretical = calculate_laminate(
        laminate,
        materials,
        specimen_width_mm=specimen_width,
        specimen_length_mm=specimen_length,
    )

    test_type = get_form_value(form, "test_type") or existing.get("test_type") or "3PB"
    real_weight = as_float(get_form_value(form, "real_weight_g"), existing.get("real_weight_g"))
    real_thickness = as_float(get_form_value(form, "real_thickness_mm"), existing.get("real_thickness_mm"))
    comments = get_form_value(form, "comments", existing.get("comments"))
    core = get_core_definition(theoretical.get("core"))
    core_material = core.get("name")
    core_thickness = as_float(core.get("thickness_mm"))
    top_skin_thickness = as_float(get_form_value(form, "top_skin_thickness_mm"), theoretical.get("top_skin_thickness_mm"))
    bottom_skin_thickness = as_float(
        get_form_value(form, "bottom_skin_thickness_mm"), theoretical.get("bottom_skin_thickness_mm")
    )
    skin_thickness = (top_skin_thickness + bottom_skin_thickness) / 2 if (
        top_skin_thickness is not None and bottom_skin_thickness is not None
    ) else None
    span = as_float(get_form_value(form, "span_mm"), DEFAULT_SPAN_MM)
    energy_target = as_float(
        get_form_value(form, "energy_target_mm"),
        (parsed.get("metadata") or {}).get("energy_target_mm") or 12.7,
    )
    car_id = as_float(get_form_value(form, "car_id"))
    panel_heights_mm = None
    if car_id is not None:
        try:
            car = DB.get_car(int(car_id))
            panel_heights_mm = {
                panel_abbreviation(panel.get("code") or panel.get("name")): panel.get("height_mm")
                for panel in car.get("panels", [])
            }
        except (KeyError, ValueError, TypeError):
            panel_heights_mm = None

    if core_thickness is None:
        raise ValueError("Core thickness is required for SES panel calculations")

    result = process_test(
        parsed["points"],
        test_type=test_type,
        theoretical=theoretical,
        core_thickness_mm=core_thickness,
        skin_thickness_mm=skin_thickness,
        real_thickness_mm=real_thickness,
        top_skin_thickness_mm=top_skin_thickness,
        bottom_skin_thickness_mm=bottom_skin_thickness,
        specimen_length_mm=specimen_length,
        span_mm=span,
        energy_target_mm=energy_target or 12.7,
        panel_heights_mm=panel_heights_mm,
    )
    computed = {key: value for key, value in result.items() if key not in {"raw_points", "reduced_points"}}
    if car_id is not None:
        computed["active_car_id"] = int(car_id)

    specimen = DB.upsert_specimen(
        {
            "id": specimen_id,
            "test_type": test_type,
            "laminate": laminate,
            "theoretical": theoretical,
            "real_weight_g": real_weight,
            "real_thickness_mm": real_thickness,
            "core_material": core_material,
            "core_thickness_mm": core_thickness,
            "skin_thickness_mm": result["skin_thickness_each_side_mm"],
            "top_skin_thickness_mm": result["top_skin_thickness_mm"],
            "bottom_skin_thickness_mm": result["bottom_skin_thickness_mm"],
            "computed": computed,
            "raw_points": result["raw_points"],
            "reduced_points": result["reduced_points"],
            "selected_points": result["selected_points"],
            "comments": comments,
            "source_filename": Path(file_item.filename or "uploaded.xlsx").name,
        }
    )
    return specimen


class SESHandler(BaseHTTPRequestHandler):
    server_version = "SESServer/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path == "/api/materials":
                return json_response(self, DB.list_materials())
            if path == "/api/core-materials":
                return json_response(self, DB.list_core_materials())
            if path == "/api/cars":
                return json_response(self, DB.list_cars())
            if path.startswith("/api/cars/"):
                parts = path.strip("/").split("/")
                if len(parts) == 4 and parts[3] == "probe-metrics":
                    return json_response(self, DB.list_car_probe_metrics(int(parts[2])))
                if len(parts) == 3:
                    return json_response(self, DB.get_car(int(parts[2])))
            if path == "/api/monocoque-weights":
                return json_response(self, DB.list_monocoque_weights())
            if path.startswith("/api/monocoque-weights/"):
                parts = path.strip("/").split("/")
                if len(parts) == 3:
                    return json_response(self, DB.get_monocoque_weight(int(parts[2])))
            if path == "/api/specimens":
                return json_response(self, DB.list_specimens())
            if path.startswith("/api/specimens/"):
                parts = path.strip("/").split("/")
                if len(parts) >= 3:
                    specimen_id = parts[2]
                    if len(parts) == 4 and parts[3] == "export":
                        return self.send_export(specimen_id)
                    return json_response(self, DB.get_specimen(specimen_id))
            return self.send_static(path)
        except KeyError as exc:
            return error_response(self, exc, status=404)
        except Exception as exc:
            traceback.print_exc()
            return error_response(self, exc, status=500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path == "/api/materials":
                require_edit_access(self)
                payload = read_json(self)
                return json_response(self, DB.create_material(payload), status=201)
            if path == "/api/core-materials":
                require_edit_access(self)
                payload = read_json(self)
                return json_response(self, DB.create_core_material(payload), status=201)
            if path == "/api/cars":
                require_edit_access(self)
                payload = read_json(self)
                return json_response(self, DB.create_car(payload), status=201)
            if path.startswith("/api/cars/"):
                parts = path.strip("/").split("/")
                if len(parts) == 4 and parts[3] == "recalculate":
                    require_edit_access(self)
                    return json_response(self, DB.recalculate_probe_metrics_for_car(int(parts[2])))
            if path == "/api/monocoque-weights/calculate":
                payload = read_json(self)
                return json_response(self, DB.calculate_monocoque_weight(payload))
            if path == "/api/monocoque-weights":
                require_edit_access(self)
                payload = read_json(self)
                return json_response(self, DB.save_monocoque_weight(payload), status=201)
            if path == "/api/precalculate":
                payload = read_json(self)
                return json_response(self, precalculate_payload(payload))
            if path == "/api/precalculate/shuffle":
                payload = read_json(self)
                return json_response(self, generate_shuffle_variants(payload, material_catalog()))
            if path == "/api/specimens/laminate":
                require_edit_access(self)
                payload = read_json(self)
                return json_response(self, store_laminate(payload), status=201)
            if path == "/api/specimens/process":
                require_edit_access(self)
                form = parse_multipart_form(self)
                return json_response(self, process_form(form), status=201)
            return error_response(self, ValueError("Unknown endpoint"), status=404)
        except Exception as exc:
            traceback.print_exc()
            return error_response(self, exc, status=401 if isinstance(exc, PermissionError) else 400)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[:2] == ["api", "materials"]:
                require_edit_access(self)
                return json_response(self, DB.update_material(int(parts[2]), read_json(self)))
            if len(parts) == 3 and parts[:2] == ["api", "core-materials"]:
                require_edit_access(self)
                return json_response(self, DB.update_core_material(int(parts[2]), read_json(self)))
            if len(parts) == 3 and parts[:2] == ["api", "cars"]:
                require_edit_access(self)
                return json_response(self, DB.update_car(int(parts[2]), read_json(self)))
            if len(parts) == 3 and parts[:2] == ["api", "monocoque-weights"]:
                require_edit_access(self)
                payload = read_json(self)
                if payload.get("metadata_only"):
                    return json_response(self, DB.update_monocoque_weight_metadata(int(parts[2]), payload))
                payload["id"] = int(parts[2])
                return json_response(self, DB.save_monocoque_weight(payload))
            return error_response(self, ValueError("Unknown endpoint"), status=404)
        except KeyError as exc:
            return error_response(self, exc, status=404)
        except Exception as exc:
            traceback.print_exc()
            return error_response(self, exc, status=401 if isinstance(exc, PermissionError) else 400)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[:2] == ["api", "materials"]:
                require_edit_access(self)
                return json_response(self, DB.delete_material(int(parts[2])))
            if len(parts) == 3 and parts[:2] == ["api", "core-materials"]:
                require_edit_access(self)
                return json_response(self, DB.delete_core_material(int(parts[2])))
            if len(parts) == 3 and parts[:2] == ["api", "cars"]:
                require_edit_access(self)
                return json_response(self, DB.delete_car(int(parts[2])))
            if len(parts) == 3 and parts[:2] == ["api", "monocoque-weights"]:
                require_edit_access(self)
                return json_response(self, DB.delete_monocoque_weight(int(parts[2])))
            if len(parts) == 3 and parts[:2] == ["api", "specimens"]:
                require_edit_access(self)
                return json_response(self, DB.delete_specimen(parts[2]))
            return error_response(self, ValueError("Unknown endpoint"), status=404)
        except KeyError as exc:
            return error_response(self, exc, status=404)
        except Exception as exc:
            traceback.print_exc()
            return error_response(self, exc, status=401 if isinstance(exc, PermissionError) else 400)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        send_cors_headers(self)
        self.end_headers()

    def send_static(self, path: str) -> None:
        if path == "/config.js":
            return self.send_frontend_config()
        target = STATIC_DIR / ("index.html" if path in {"", "/"} else path.lstrip("/"))
        target = target.resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.exists() or target.is_dir():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = target.read_bytes()
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        send_cors_headers(self)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_frontend_config(self) -> None:
        payload = {
            "API_BASE_URL": os.environ.get("FRONTEND_API_BASE_URL", ""),
            "SUPABASE_URL": SUPABASE_URL,
            "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
            "AUTH_MODE": EDIT_AUTH_MODE,
        }
        content = f"window.SES_CONFIG = {json.dumps(payload, ensure_ascii=False)};\n".encode("utf-8")
        self.send_response(200)
        send_cors_headers(self)
        self.send_header("Content-Type", "application/javascript; charset=utf-8")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_export(self, specimen_id: str) -> None:
        specimen = DB.get_specimen(specimen_id)
        safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in specimen_id)
        filename = f"specimen_{safe_id}_export.xlsx"
        output_path = DATA_DIR / "exports" / filename
        export_specimen_workbook(specimen, output_path)
        content = output_path.read_bytes()
        self.send_response(200)
        send_cors_headers(self)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SES laminate web app")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    args = parser.parse_args()
    host = args.host
    port = args.port
    server = ThreadingHTTPServer((host, port), SESHandler)
    print(f"SES web app running at http://{host}:{port}")
    print(f"Database: {getattr(DB, 'path', 'Supabase')}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
