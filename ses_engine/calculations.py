from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any, Iterable


DEFAULT_SPECIMEN_WIDTH_MM = 500.0
DEFAULT_SPECIMEN_LENGTH_MM = 275.0
DEFAULT_SPAN_MM = 400.0


PANEL_ABBREVIATIONS = {
    "FBH": "FBH",
    "FHB": "FHB",
    "FBHS": "FBHS",
    "SHB": "SHB",
    "MHBS": "MHBS",
    "SISv": "SISv",
    "SISh": "SISh",
    "DASH": "Dashboard",
    "frontbulkhead": "FBH",
    "fronthoopbulkhead": "FHB",
    "frontbulkheadside": "FBHS",
    "sidehoopbulkhead": "SHB",
    "mainhoopbulkheadside": "MHBS",
    "sideimpactstructurevertical": "SISv",
    "sideimpactstructurehorizontal": "SISh",
    "dashboard": "Dashboard",
}


def panel_abbreviation(name_or_code: Any) -> str:
    text = str(name_or_code or "").strip()
    normalized = "".join(ch for ch in text.lower() if ch.isalnum())
    return PANEL_ABBREVIATIONS.get(text) or PANEL_ABBREVIATIONS.get(normalized) or text


def normalized_test_type(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def is_energy_absorbed_test(value: Any) -> bool:
    text = normalized_test_type(value)
    return (
        "3pb" in text
        or "3pointbend" in text
        or "threepointbend" in text
        or "sideimpact" in text
        or "sisv" in text
        or "sish" in text
    )


DEFAULT_MIN_SLOPE_DX_MM = 1.0
DEFAULT_PEAK_PROMINENCE_FRACTION = 0.08


UD_ORIENTATIONS = ["0", "+45", "90", "-45"]
BIDIRECTIONAL_ORIENTATIONS = ["+-45", "+-90"]
PANEL_CODES = ["FBH", "FHB", "FBHS", "SHB", "MHBS", "SISv", "SISh"]


DEFAULT_MATERIALS = [
    {
        "technical_id": "RC416T",
        "name": "RC416",
        "material_category": "fiber",
        "fiber_family": "twill",
        "thickness_mm": 0.43,
        "areal_weight_g_m2": 416.0,
        "fiber_type": "bidirectional",
        "resin_fraction": 0.40,
        "e1_pa": 62.45e9,
        "e2_pa": 61.20e9,
        "g12_pa": 3.71e9,
        "poisson_input": 0.037,
        "density_kg_m3": 1600.0,
        "strength_x_mpa": 593.0,
        "strength_x_compression_mpa": 489.6,
        "strength_y_mpa": 593.3,
        "strength_y_compression_mpa": 489.6,
        "strength_s_mpa": 68.2,
        "aliases": "RC416T",
        "notes": "Reference Twill material mapped from RC416T.",
    },
    {
        "technical_id": "UD",
        "name": "UD300",
        "material_category": "fiber",
        "fiber_family": "ud",
        "thickness_mm": 0.30,
        "areal_weight_g_m2": 300.0,
        "fiber_type": "unidirectional",
        "resin_fraction": 0.35,
        "e1_pa": 130.33e9,
        "e2_pa": 7.22e9,
        "g12_pa": 4.23e9,
        "poisson_input": 0.337,
        "density_kg_m3": 1600.0,
        "strength_x_mpa": 1433.6,
        "strength_x_compression_mpa": 1003.3,
        "strength_y_mpa": 32.5,
        "strength_y_compression_mpa": 108.3,
        "strength_s_mpa": 76.1,
        "aliases": "UD",
        "notes": "Reference UD material mapped from UD.",
    },
]

CORE_MATERIALS = [
    {
        "key": "hc_al",
        "technical_id": "Honeycomb",
        "name": "Aluminum HC (20 mm)",
        "type": "honeycomb",
        "material_category": "core",
        "fiber_family": "",
        "thickness_mm": 20.0,
        "density_kg_m3": 72.1,
        "e1_pa": 1.0e6,
        "e2_pa": 1.0e6,
        "g12_pa": 1.0e6,
        "poisson_input": 0.5,
        "strength_x_mpa": 10.0,
        "strength_x_compression_mpa": 10.0,
        "strength_y_mpa": 10.0,
        "strength_y_compression_mpa": 10.0,
        "strength_s_mpa": 10.0,
        "aliases": "Honeycomb;Aluminium honeycomb (HC Al);Aluminum honeycomb;HC Al;aluminium_honeycomb_hc_al",
        "notes": "Reference Honeycomb core mapped to SES Aluminum HC.",
    },
    {
        "key": "balsa",
        "technical_id": "BALSA_9_5",
        "name": "Balsa Wood (9.5 mm)",
        "type": "wood",
        "material_category": "core",
        "fiber_family": "",
        "thickness_mm": 9.5,
        "density_kg_m3": 155.0,
        "e1_pa": 3.17e9,
        "e2_pa": 3.17e9,
        "g12_pa": 1.10e9,
        "poisson_input": 0.4409,
        "strength_x_mpa": 0.0,
        "strength_x_compression_mpa": 0.0,
        "strength_y_mpa": 0.0,
        "strength_y_compression_mpa": 0.0,
        "strength_s_mpa": 0.0,
        "aliases": "Balsa wood;balsa;MD Balsa Wood;balsa_wood__9_5_mm;Balsa Wood (9,5 mm)",
        "notes": "Balsa core option compatible with MD Balsa Wood.",
    },
    {
        "key": "balsa_12_7",
        "technical_id": "BALSA_12_7",
        "name": "Balsa Wood (12.7 mm)",
        "type": "wood",
        "material_category": "core",
        "fiber_family": "",
        "thickness_mm": 12.7,
        "density_kg_m3": 155.0,
        "e1_pa": 3.17e9,
        "e2_pa": 3.17e9,
        "g12_pa": 1.10e9,
        "poisson_input": 0.4409,
        "strength_x_mpa": 0.0,
        "strength_x_compression_mpa": 0.0,
        "strength_y_mpa": 0.0,
        "strength_y_compression_mpa": 0.0,
        "strength_s_mpa": 0.0,
        "aliases": "MD Balsa Wood 12.7;Balsa 12.7;balsa_wood__12_7mm;Balsa Wood (12,7mm);Balsa Wood (12,7 mm)",
        "notes": "Balsa core option compatible with MD Balsa Wood.",
    },
]


PANEL_CONSTANTS: dict[str, dict[str, float]] = {
    "FBH": {
        "panel_height_mm": 149.98,
        "yield_target_n": 73000.0,
        "uts_target_n": 87300.0,
        "max_load_target_n": 1960.0,
        "max_deflection_target_m": 0.012,
        "energy_target_j": 11.7,
        "ei_target_gpa_m4": 3400.0,
    },
    "FHB": {
        "panel_height_mm": 121.68,
        "yield_target_n": 36500.0,
        "uts_target_n": 43700.0,
        "max_load_target_n": 978.0,
        "max_deflection_target_m": 0.012,
        "energy_target_j": 5.86,
        "ei_target_gpa_m4": 1700.0,
    },
    "FBHS": {
        "panel_height_mm": 337.81,
        "yield_target_n": 83500.0,
        "uts_target_n": 99900.0,
        "max_load_target_n": 2310.0,
        "max_deflection_target_m": 0.012,
        "energy_target_j": 13.8,
        "ei_target_gpa_m4": 4020.0,
    },
    "SHB": {
        "panel_height_mm": 101.29,
        "yield_target_n": 52900.0,
        "uts_target_n": 63300.0,
        "max_load_target_n": 1330.0,
        "max_deflection_target_m": 0.012,
        "energy_target_j": 7.98,
        "ei_target_gpa_m4": 2320.0,
    },
    "MHBS": {
        "panel_height_mm": 248.17,
        "yield_target_n": 55700.0,
        "uts_target_n": 66600.0,
        "max_load_target_n": 1540.0,
        "max_deflection_target_m": 0.012,
        "energy_target_j": 9.22,
        "ei_target_gpa_m4": 2680.0,
    },
    "SISv": {
        "panel_height_mm": 274.86,
        "yield_target_n": 109000.0,
        "uts_target_n": 131000.0,
        "max_load_target_n": 2930.0,
        "max_deflection_target_m": 0.012,
        "energy_target_j": 17.6,
        "ei_target_gpa_m4": 5110.0,
    },
    "SISh": {
        "panel_height_mm": 185.40,
        "yield_target_n": 109000.0,
        "uts_target_n": 131000.0,
        "max_load_target_n": 2930.0,
        "max_deflection_target_m": 0.012,
        "energy_target_j": 17.6,
        "ei_target_gpa_m4": 5110.0,
    },
}

DEFAULT_PANEL_HEIGHTS_MM = {
    panel_code: values["panel_height_mm"]
    for panel_code, values in PANEL_CONSTANTS.items()
}

OUTER_WIDTH_MM = 313.98
OUTER_HEIGHT_MM = 314.00


@dataclass
class Material:
    id: int | None
    name: str
    thickness_mm: float
    areal_weight_g_m2: float
    fiber_type: str
    resin_fraction: float
    e1_pa: float | None = None
    e2_pa: float | None = None
    g12_pa: float | None = None
    poisson_input: float | None = None
    density_kg_m3: float | None = None
    strength_x_mpa: float | None = None
    strength_x_compression_mpa: float | None = None
    strength_y_mpa: float | None = None
    strength_y_compression_mpa: float | None = None
    strength_s_mpa: float | None = None
    aliases: str = ""
    technical_id: str = ""
    material_category: str = "fiber"
    fiber_family: str = ""
    notes: str = ""

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "Material":
        def number(key: str) -> float | None:
            aliases = {
                "strength_x_mpa": "strength_x",
                "strength_x_compression_mpa": "strength_x_compression",
                "strength_y_mpa": "strength_y",
                "strength_y_compression_mpa": "strength_y_compression",
                "strength_s_mpa": "strength_s",
            }
            value = data.get(key, data.get(aliases.get(key, "")))
            try:
                if value is None or value == "":
                    return None
                out = float(str(value).replace(",", "."))
                return out if math.isfinite(out) else None
            except (TypeError, ValueError):
                return None

        fiber_family = str(data.get("fiber_family") or "").strip().lower()
        fiber_type = str(data.get("fiber_type") or "").strip().lower()
        if not fiber_type:
            fiber_type = "unidirectional" if fiber_family == "ud" else "bidirectional"
        return cls(
            id=data.get("id"),
            name=str(data["name"]),
            thickness_mm=float(data["thickness_mm"]),
            areal_weight_g_m2=float(data["areal_weight_g_m2"]),
            fiber_type=fiber_type,
            resin_fraction=float(data.get("resin_fraction", 0.0)),
            e1_pa=number("e1_pa"),
            e2_pa=number("e2_pa"),
            g12_pa=number("g12_pa"),
            poisson_input=number("poisson_input"),
            density_kg_m3=number("density_kg_m3"),
            strength_x_mpa=number("strength_x_mpa"),
            strength_x_compression_mpa=number("strength_x_compression_mpa"),
            strength_y_mpa=number("strength_y_mpa"),
            strength_y_compression_mpa=number("strength_y_compression_mpa"),
            strength_s_mpa=number("strength_s_mpa"),
            aliases=str(data.get("aliases") or ""),
            technical_id=str(data.get("technical_id") or data.get("material_id") or data.get("name") or ""),
            material_category=str(data.get("material_category") or "fiber"),
            fiber_family=fiber_family or ("ud" if fiber_type == "unidirectional" else "twill"),
            notes=str(data.get("notes") or ""),
        )


def finite_number(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        out = float(str(value).replace(",", "."))
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def normalize_orientation(value: Any) -> str:
    text = str(value or "").strip().upper()
    replacements = {
        "0 DEG": "0",
        "0DEG": "0",
        "0º": "0",
        "+45 DEG": "+45",
        "+45º": "+45",
        "-45 DEG": "-45",
        "-45º": "-45",
        "90 DEG": "90",
        "90º": "90",
        "+-45 DEG": "+-45",
        "+-45º": "+-45",
        "±45": "+-45",
        "45": "+45",
        "+/-45": "+-45",
        "+-90 DEG": "+-90",
        "+-90º": "+-90",
        "±90": "+-90",
        "+/-90": "+-90",
        "RC +-45": "+-45",
        "RC +-90": "+-90",
        "UD 0": "0",
        "UD +45": "+45",
        "UD -45": "-45",
        "UD 90": "90",
        "XC +-45": "+-45",
        "XC+-45": "+-45",
        "XC +-90": "+-90",
        "XC+-90": "+-90",
    }
    return replacements.get(text, text.replace(" ", ""))


def orientation_label(material: Material, orientation: str) -> str:
    if material.fiber_type == "unidirectional":
        return f"UD {orientation} deg"
    return f"RC {orientation} deg"


def validate_orientation(material: Material, orientation: str) -> None:
    allowed = UD_ORIENTATIONS if material.fiber_type == "unidirectional" else BIDIRECTIONAL_ORIENTATIONS
    if orientation not in allowed:
        raise ValueError(f"{material.name} only allows orientations: {', '.join(allowed)}")


def zero_fiber_factor(material: Material, orientation: str) -> float:
    if material.fiber_type == "unidirectional":
        return 1.0 if orientation == "0" else 0.0
    return 0.5 if orientation == "+-90" else 0.0


def get_core_definition(value: Any = None) -> dict[str, Any]:
    if isinstance(value, dict):
        key = value.get("key") or value.get("name") or value.get("material")
        base = get_core_definition(key)
        out = dict(base)
        if value.get("id") is not None:
            out["id"] = value.get("id")
        if value.get("key"):
            out["key"] = str(value["key"])
        if value.get("name"):
            out["name"] = str(value["name"])
        if value.get("type"):
            out["type"] = str(value["type"])
        if finite_number(value.get("thickness_mm")) is not None:
            out["thickness_mm"] = float(finite_number(value.get("thickness_mm")))
        if finite_number(value.get("density_kg_m3")) is not None:
            out["density_kg_m3"] = float(finite_number(value.get("density_kg_m3")))
        for optional in (
            "e1_pa",
            "e2_pa",
            "g12_pa",
            "poisson_input",
            "strength_x_mpa",
            "strength_x_compression_mpa",
            "strength_y_mpa",
            "strength_y_compression_mpa",
            "strength_s_mpa",
        ):
            if finite_number(value.get(optional)) is not None:
                out[optional] = float(finite_number(value.get(optional)))
        for optional in ("mechanical_notes", "geometry_notes", "aliases"):
            if value.get(optional):
                out[optional] = str(value[optional])
        return out

    text = str(value or "").strip().lower()
    for core in CORE_MATERIALS:
        aliases = {core["key"].lower(), core["name"].lower()}
        aliases.update(alias.strip().lower() for alias in str(core.get("aliases") or "").split(";") if alias.strip())
        if text in aliases or (text and text in core["name"].lower()):
            return dict(core)
    return dict(CORE_MATERIALS[0])


def normalize_laminate_structure(laminate: Any) -> dict[str, Any]:
    if isinstance(laminate, dict):
        top = laminate.get("top_skin") or laminate.get("topSkin") or []
        bottom = laminate.get("bottom_skin") or laminate.get("bottomSkin") or []
        core = get_core_definition(laminate.get("core"))
        return {
            "top_skin": list(top),
            "bottom_skin": list(bottom),
            "core": core,
            "top_skin_thickness_mm": finite_number(laminate.get("top_skin_thickness_mm") or laminate.get("topSkinThicknessMm")),
            "bottom_skin_thickness_mm": finite_number(
                laminate.get("bottom_skin_thickness_mm") or laminate.get("bottomSkinThicknessMm")
            ),
            "legacy_flat": False,
        }

    # Backward compatibility: a legacy flat layer list is interpreted as skin
    # laminate with no core. Existing saved specimens still calculate.
    return {
        "top_skin": list(laminate or []),
        "bottom_skin": [],
        "core": {"key": "none", "name": "No core", "thickness_mm": 0.0, "density_kg_m3": 0.0},
        "top_skin_thickness_mm": None,
        "bottom_skin_thickness_mm": None,
        "legacy_flat": True,
    }


def _layer_has_orientation(layer: Any) -> bool:
    if not isinstance(layer, dict):
        return False
    material_id = layer.get("material_id")
    material_name = str(layer.get("material_name") or "").strip()
    orientation = normalize_orientation(layer.get("orientation"))
    return bool((material_id not in (None, "")) or material_name) and bool(orientation)


def _layer_signature(layer: Any) -> tuple[str, str, str]:
    if not isinstance(layer, dict):
        return ("", "", "")
    return (
        str(layer.get("material_id") or ""),
        str(layer.get("material_name") or ""),
        normalize_orientation(layer.get("orientation")),
    )


def laminate_is_symmetric(laminate: Any) -> bool:
    structure = normalize_laminate_structure(laminate)
    top = structure.get("top_skin") or []
    bottom = structure.get("bottom_skin") or []
    return bool(top) and len(top) == len(bottom) and all(
        _layer_signature(layer) == _layer_signature(bottom[len(bottom) - 1 - index])
        for index, layer in enumerate(top)
    )


def laminate_sequence(laminate: Any) -> str:
    """Return the compact top/core/bottom laminate sequence used by the UI/export."""
    structure = normalize_laminate_structure(laminate)
    top = structure.get("top_skin") or []
    bottom = structure.get("bottom_skin") or []
    if not top or not bottom:
        return "Incomplete laminate"
    if not all(_layer_has_orientation(layer) for layer in [*top, *bottom]):
        return "Incomplete laminate"

    def skin_sequence(layers: list[dict[str, Any]]) -> str:
        return "/".join(f"{normalize_orientation(layer.get('orientation'))}º" for layer in layers)

    return f"[{skin_sequence(top)}] S" if laminate_is_symmetric(structure) else f"[{skin_sequence(top)}] Core [{skin_sequence(bottom)}]"


def parse_laminate_text(text: str, material_catalog: Iterable[Material]) -> list[dict[str, Any]]:
    """Parse workbook-style laminate text into actual ply rows.

    The workbook stores half-stacks such as "[+-45/0/+-45] S.". When the
    suffix is present, this expands to a full mirrored stack. Plain text without
    an S suffix is treated as the exact row order supplied.
    """
    clean = str(text or "").strip()
    is_symmetric = "S." in clean.upper() or clean.upper().endswith(" S")
    clean = (
        clean.replace("[", "")
        .replace("]", "")
        .replace(" S.", "")
        .replace(" s.", "")
        .replace(" S", "")
        .strip()
    )
    if not clean:
        return []

    materials = list(material_catalog)
    ud = next((m for m in materials if m.fiber_type == "unidirectional"), None)
    bidi = next((m for m in materials if m.fiber_type == "bidirectional"), None)
    tokens = [t.strip() for t in clean.split("/") if t.strip()]
    if is_symmetric:
        tokens = tokens + list(reversed(tokens))

    layers: list[dict[str, Any]] = []
    for index, token in enumerate(tokens, start=1):
        orientation = normalize_orientation(token)
        material = ud if orientation in UD_ORIENTATIONS else bidi
        if material is None:
            continue
        layers.append(
            {
                "material_id": material.id,
                "material_name": material.name,
                "orientation": orientation,
                "zone": "external" if index in (1, len(tokens)) else "internal",
            }
        )
    return layers


def _calculate_skin(
    layers: list[dict[str, Any]],
    materials: list[Material],
    area_m2: float,
    skin_name: str,
) -> dict[str, Any]:
    catalog = [m if isinstance(m, Material) else Material.from_mapping(m) for m in materials]
    by_id = {m.id: m for m in catalog if m.id is not None}
    by_name = {m.name: m for m in catalog}

    ply_table: list[dict[str, Any]] = []
    total_thickness = 0.0
    total_fiber_weight = 0.0
    total_weight = 0.0
    zero_fiber_weight = 0.0
    fiber_by_orientation: dict[str, float] = {}

    for idx, layer in enumerate(layers, start=1):
        material = None
        if layer.get("material_id") not in (None, ""):
            material = by_id.get(int(layer["material_id"]))
        if material is None and layer.get("material_name"):
            material = by_name.get(str(layer["material_name"]))
        if material is None:
            raise ValueError(f"Unknown material in layer {idx}")

        orientation = normalize_orientation(layer.get("orientation"))
        validate_orientation(material, orientation)

        fiber_weight = area_m2 * material.areal_weight_g_m2
        resin_fraction = min(max(material.resin_fraction, 0.0), 0.95)
        layer_total_weight = fiber_weight / (1.0 - resin_fraction) if resin_fraction < 1 else math.nan
        zero_weight = fiber_weight * zero_fiber_factor(material, orientation)

        total_thickness += material.thickness_mm
        total_fiber_weight += fiber_weight
        total_weight += layer_total_weight
        zero_fiber_weight += zero_weight
        orientation_key = f"{material.fiber_type}:{orientation}"
        fiber_by_orientation[orientation_key] = fiber_by_orientation.get(orientation_key, 0.0) + fiber_weight

        ply_table.append(
            {
                "index": idx,
                "skin": skin_name,
                "zone": layer.get("zone", "internal"),
                "material": material.name,
                "fiber_type": material.fiber_type,
                "orientation": orientation,
                "orientation_label": orientation_label(material, orientation),
                "thickness_mm": material.thickness_mm,
                "fiber_weight_g": fiber_weight,
                "total_weight_g": layer_total_weight,
                "zero_fiber_weight_g": zero_weight,
            }
        )

    return {
        "layers": ply_table,
        "layer_count": len(ply_table),
        "fiber_weight_g": total_fiber_weight,
        "skin_weight_g": total_weight,
        "layer_thickness_mm": total_thickness,
        "zero_fiber_weight_g": zero_fiber_weight,
        "fiber_by_orientation": fiber_by_orientation,
    }


def calculate_laminate(
    laminate: Any,
    materials: Iterable[Material | dict[str, Any]],
    specimen_width_mm: float = DEFAULT_SPECIMEN_WIDTH_MM,
    specimen_length_mm: float = DEFAULT_SPECIMEN_LENGTH_MM,
) -> dict[str, Any]:
    catalog = [m if isinstance(m, Material) else Material.from_mapping(m) for m in materials]
    structure = normalize_laminate_structure(laminate)
    area_m2 = (float(specimen_width_mm) * 0.001) * (float(specimen_length_mm) * 0.001)

    top = _calculate_skin(structure["top_skin"], catalog, area_m2, "top")
    bottom = _calculate_skin(structure["bottom_skin"], catalog, area_m2, "bottom")
    core = get_core_definition(structure["core"])

    top_thickness = (
        float(structure["top_skin_thickness_mm"])
        if structure.get("top_skin_thickness_mm") is not None
        else top["layer_thickness_mm"]
    )
    bottom_thickness = (
        float(structure["bottom_skin_thickness_mm"])
        if structure.get("bottom_skin_thickness_mm") is not None
        else bottom["layer_thickness_mm"]
    )
    core_thickness = float(core.get("thickness_mm") or 0.0)
    core_weight = float(core.get("density_kg_m3") or 0.0) * area_m2 * (core_thickness / 1000.0) * 1000.0

    total_fiber_weight = top["fiber_weight_g"] + bottom["fiber_weight_g"]
    total_skin_weight = top["skin_weight_g"] + bottom["skin_weight_g"]
    total_weight = total_skin_weight + core_weight
    zero_fiber_weight = top["zero_fiber_weight_g"] + bottom["zero_fiber_weight_g"]
    zero_percent = zero_fiber_weight / total_fiber_weight if total_fiber_weight else math.nan

    if structure.get("legacy_flat"):
        asymmetry_weight = abs(
            top["fiber_by_orientation"].get("unidirectional:0", 0.0)
            - top["fiber_by_orientation"].get("unidirectional:90", 0.0)
        )
    else:
        orientation_keys = set(top["fiber_by_orientation"]) | set(bottom["fiber_by_orientation"])
        asymmetry_weight = sum(
            abs(top["fiber_by_orientation"].get(key, 0.0) - bottom["fiber_by_orientation"].get(key, 0.0))
            for key in orientation_keys
        )
    warping_percent = asymmetry_weight / total_fiber_weight if total_fiber_weight else math.nan

    all_layers = top["layers"] + bottom["layers"]
    theory = compute_laminate_theory(
        structure,
        catalog,
        core,
        specimen_length_mm=float(specimen_length_mm),
    )

    return {
        "specimen_width_mm": specimen_width_mm,
        "specimen_length_mm": specimen_length_mm,
        "area_m2": area_m2,
        "structure": {
            "top_skin": structure["top_skin"],
            "core": core,
            "bottom_skin": structure["bottom_skin"],
            "top_skin_thickness_mm": top_thickness,
            "bottom_skin_thickness_mm": bottom_thickness,
        },
        "laminate_sequence": laminate_sequence(structure),
        "top_skin": top,
        "bottom_skin": bottom,
        "core": {
            **core,
            "weight_g": core_weight,
        },
        "layers": all_layers,
        "layer_count": len(all_layers),
        "total_weight_g": total_weight,
        "total_skin_weight_g": total_skin_weight,
        "core_weight_g": core_weight,
        "fiber_weight_g": total_fiber_weight,
        "top_skin_thickness_mm": top_thickness,
        "bottom_skin_thickness_mm": bottom_thickness,
        "skin_thickness_equivalent_mm": (top_thickness + bottom_thickness) / 2.0,
        "total_skin_thickness_mm": top_thickness + bottom_thickness,
        "core_thickness_mm": core_thickness,
        "total_thickness_mm": top_thickness + core_thickness + bottom_thickness,
        "zero_percent": zero_percent,
        "warping_percent": warping_percent,
        "warping_asymmetry_weight_g": asymmetry_weight,
        "laminate_theory": theory,
    }


def _mat3_zero() -> list[list[float]]:
    return [[0.0, 0.0, 0.0] for _ in range(3)]


def _mat3_add(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[a[i][j] + b[i][j] for j in range(3)] for i in range(3)]


def _mat3_sub(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[a[i][j] - b[i][j] for j in range(3)] for i in range(3)]


def _mat3_scale(a: list[list[float]], factor: float) -> list[list[float]]:
    return [[a[i][j] * factor for j in range(3)] for i in range(3)]


def _mat3_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mat3_inv(m: list[list[float]]) -> list[list[float]]:
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-18:
        raise ValueError("Laminate stiffness matrix is singular")
    return [
        [(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
        [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
        [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det],
    ]


def _qbar(e1: float, e2: float, g12: float, poisson_input: float, theta_deg: float) -> list[list[float]]:
    # Matches the reference laminate-theory app: poisson_input is read as the
    # reciprocal Poisson input and nu12 is derived from E2/E1.
    nu21 = poisson_input
    nu12 = (e2 / e1) * nu21
    denominator = 1.0 - nu12 * nu21
    q11 = e1 / denominator
    q12 = (nu21 * e2) / denominator
    q22 = e2 / denominator
    q66 = g12

    m = math.cos(math.radians(theta_deg))
    n = math.sin(math.radians(theta_deg))
    m2 = m * m
    n2 = n * n
    m3 = m2 * m
    n3 = n2 * n
    m4 = m2 * m2
    n4 = n2 * n2

    q11_bar = q11 * m4 + 2.0 * (q12 + 2.0 * q66) * m2 * n2 + q22 * n4
    q22_bar = q11 * n4 + 2.0 * (q12 + 2.0 * q66) * m2 * n2 + q22 * m4
    q12_bar = (q11 + q22 - 4.0 * q66) * m2 * n2 + q12 * (m4 + n4)
    q16_bar = (q11 - q12 - 2.0 * q66) * m3 * n - (q22 - q12 - 2.0 * q66) * m * n3
    q26_bar = (q11 - q12 - 2.0 * q66) * m * n3 - (q22 - q12 - 2.0 * q66) * m3 * n
    q66_bar = (q11 + q22 - 2.0 * q12 - 2.0 * q66) * m2 * n2 + q66 * (m4 + n4)
    return [
        [q11_bar, q12_bar, q16_bar],
        [q12_bar, q22_bar, q26_bar],
        [q16_bar, q26_bar, q66_bar],
    ]


def _orientation_angles(orientation: str) -> list[float]:
    normalized = normalize_orientation(orientation)
    if normalized == "+-45":
        return [45.0]
    if normalized == "+-90":
        return [90.0]
    return [float(normalized.replace("+", ""))]


def _material_lookup(materials: list[Material]) -> tuple[dict[int, Material], dict[str, Material]]:
    by_id = {int(m.id): m for m in materials if m.id is not None}
    by_name: dict[str, Material] = {}
    for material in materials:
        names = [material.name, *[alias.strip() for alias in str(material.aliases or "").split(";") if alias.strip()]]
        for name in names:
            by_name[name.strip().lower()] = material
    return by_id, by_name


def _resolve_layer_material(layer: dict[str, Any], by_id: dict[int, Material], by_name: dict[str, Material]) -> Material | None:
    material_id = layer.get("material_id")
    if material_id not in (None, ""):
        try:
            material = by_id.get(int(material_id))
            if material:
                return material
        except (TypeError, ValueError):
            pass
    material_name = str(layer.get("material_name") or layer.get("material") or "").strip().lower()
    return by_name.get(material_name) if material_name else None


def _material_theory_ready(material: Material | dict[str, Any]) -> bool:
    if isinstance(material, Material):
        return all(
            finite_number(value) is not None and float(value) > 0
            for value in (material.e1_pa, material.e2_pa, material.g12_pa)
        ) and finite_number(material.poisson_input) is not None
    return all(
        finite_number(material.get(key)) is not None and float(material.get(key) or 0) > 0
        for key in ("e1_pa", "e2_pa", "g12_pa")
    ) and finite_number(material.get("poisson_input")) is not None


def _build_theory_layers(
    structure: dict[str, Any],
    materials: list[Material],
    core: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    by_id, by_name = _material_lookup(materials)
    layers: list[dict[str, Any]] = []
    warnings: list[str] = []

    def add_skin(skin_layers: list[dict[str, Any]], source: str) -> None:
        for layer in skin_layers:
            material = _resolve_layer_material(layer, by_id, by_name)
            if not material:
                warnings.append("A carbon ply is missing a resolvable material.")
                continue
            if not _material_theory_ready(material):
                warnings.append(f"{material.name} is missing E1/E2/G12/Poisson data for laminate theory.")
                continue
            angles = _orientation_angles(layer.get("orientation"))
            thickness = material.thickness_mm / max(len(angles), 1)
            for angle in angles:
                layers.append(
                    {
                        "zone": source,
                        "material_name": material.name,
                        "orientation": angle,
                        "thickness_mm": thickness,
                        "e1_pa": material.e1_pa,
                        "e2_pa": material.e2_pa,
                        "g12_pa": material.g12_pa,
                        "poisson_input": material.poisson_input,
                    }
                )

    add_skin(list(structure.get("top_skin") or []), "top")
    if _material_theory_ready(core):
        layers.append(
            {
                "zone": "core",
                "material_name": core.get("name") or "Core",
                "orientation": 0.0,
                "thickness_mm": float(core.get("thickness_mm") or 0.0),
                "e1_pa": finite_number(core.get("e1_pa")),
                "e2_pa": finite_number(core.get("e2_pa")),
                "g12_pa": finite_number(core.get("g12_pa")),
                "poisson_input": finite_number(core.get("poisson_input")),
            }
        )
    else:
        warnings.append(f"{core.get('name') or 'Core'} is missing E1/E2/G12/Poisson data for laminate theory.")
    add_skin(list(structure.get("bottom_skin") or []), "bottom")
    return layers, warnings


def _compute_trace(theory_layers: list[dict[str, Any]]) -> dict[str, Any]:
    total_thickness_mm = sum(float(layer["thickness_mm"]) for layer in theory_layers)
    current_z = total_thickness_mm / 2.0
    z_interfaces = [current_z]
    a_matrix = _mat3_zero()
    b_matrix = _mat3_zero()
    d_matrix = _mat3_zero()

    display_layers: list[dict[str, Any]] = []
    for index, layer in enumerate(theory_layers, start=1):
        thickness = float(layer["thickness_mm"])
        next_z = current_z - thickness
        qbar = _qbar(
            float(layer["e1_pa"]),
            float(layer["e2_pa"]),
            float(layer["g12_pa"]),
            float(layer["poisson_input"]),
            float(layer.get("orientation") or 0.0),
        )
        a_matrix = _mat3_add(a_matrix, _mat3_scale(qbar, current_z - next_z))
        b_matrix = _mat3_add(b_matrix, _mat3_scale(qbar, (current_z**2 - next_z**2) / 2.0))
        d_matrix = _mat3_add(d_matrix, _mat3_scale(qbar, (current_z**3 - next_z**3) / 3.0))
        display_layers.append(
            {
                "index": index,
                "zone": layer.get("zone"),
                "material_name": layer.get("material_name"),
                "orientation_deg": layer.get("orientation"),
                "thickness_mm": thickness,
                "z_top_mm": current_z,
                "z_bottom_mm": next_z,
            }
        )
        current_z = next_z
        z_interfaces.append(current_z)

    return {
        "total_thickness_mm": total_thickness_mm,
        "z_interfaces_mm": z_interfaces,
        "a_matrix": a_matrix,
        "b_matrix": b_matrix,
        "d_matrix": d_matrix,
        "layers": display_layers,
    }


def _equivalent_properties(a_matrix: list[list[float]], d_matrix: list[list[float]], total_thickness_mm: float) -> dict[str, Any]:
    a1_matrix = _mat3_scale(a_matrix, 1.0 / total_thickness_mm)
    d1_matrix = _mat3_scale(d_matrix, 12.0 / (total_thickness_mm**3))
    compliance = _mat3_inv(a1_matrix)
    e11 = 1.0 / compliance[0][0]
    e22 = 1.0 / compliance[1][1]
    g122 = 1.0 / compliance[2][2]
    nu12 = -compliance[0][1] / compliance[0][0]
    nu21 = -compliance[0][1] / compliance[1][1]
    return {
        "a1_matrix": a1_matrix,
        "d1_matrix": d1_matrix,
        "e11_pa": e11,
        "e22_pa": e22,
        "g122_pa": g122,
        "g12g_pa": g122,
        "nu12": nu12,
        "nu21": nu21,
        "e11_gpa": e11 / 1e9,
        "e22_gpa": e22 / 1e9,
        "g122_gpa": g122 / 1e9,
        "g12g_gpa": g122 / 1e9,
    }


def _three_point_bending_theory(
    structure: dict[str, Any],
    full_trace: dict[str, Any],
    top_trace: dict[str, Any] | None,
    core_thickness_mm: float,
    specimen_length_mm: float,
) -> dict[str, Any]:
    elastic_gradient = 2649.0
    rigidez_rig = 14871.0
    span_m = DEFAULT_SPAN_MM / 1000.0
    width_m = specimen_length_mm / 1000.0
    corrected = (elastic_gradient * rigidez_rig) / (rigidez_rig - elastic_gradient)
    ei_ensayo = corrected * 1000.0 * (span_m**3) / 48.0

    if laminate_is_symmetric(structure) and top_trace and top_trace["total_thickness_mm"] > 0:
        top_equivalent = _equivalent_properties(
            top_trace["a_matrix"],
            top_trace["d_matrix"],
            top_trace["total_thickness_mm"],
        )
        t_skin_m = top_trace["total_thickness_mm"] * 0.001
        t_core_m = core_thickness_mm * 0.001
        denominator = 0.5 * width_m * t_skin_m * ((t_skin_m + t_core_m) ** 2)
        ei_theory = denominator * float(top_equivalent["e11_pa"])
        e_fibra_ensayo = 0.0 if denominator == 0.0 else ei_ensayo / denominator
        mode = "symmetric_skin_formula"
    else:
        a_inverse = _mat3_inv(full_trace["a_matrix"])
        d_effective = _mat3_sub(full_trace["d_matrix"], _mat3_mul(_mat3_mul(full_trace["b_matrix"], a_inverse), full_trace["b_matrix"]))
        ei_theory = float(d_effective[0][0]) * width_m * 1e-9
        e_fibra_ensayo = None
        mode = "unsymmetric_d_star"

    elastic_gradient_theory = 48.0 * ei_theory / ((span_m**3) * 1000.0)
    return {
        "mode": mode,
        "elastic_gradient": elastic_gradient,
        "rigidez_rig": rigidez_rig,
        "elastic_gradient_corrected": corrected,
        "ei_ensayo": ei_ensayo,
        "e_fibra_ensayo": e_fibra_ensayo,
        "ei_theory": ei_theory,
        "elastic_gradient_theory": elastic_gradient_theory,
        "th_fibra_mm": sum(float(layer.get("thickness_mm") or 0.0) for layer in full_trace["layers"] if layer.get("zone") != "core"),
        "core_thickness_mm": core_thickness_mm,
    }


def compute_laminate_theory(
    structure: dict[str, Any],
    materials: list[Material],
    core: dict[str, Any],
    specimen_length_mm: float = DEFAULT_SPECIMEN_LENGTH_MM,
) -> dict[str, Any]:
    """Classical Laminate Theory outputs adapted from Teoria_Laminado_App.

    The reference app computes Qbar for each visible sandwich layer, integrates
    the A/B/D matrices through thickness, derives equivalent engineering
    constants from A/t and 12D/t^3, and computes the elastic-gradient theory
    from either the symmetric sandwich skin formula or D* for asymmetric stacks.
    """
    theory_layers, warnings = _build_theory_layers(structure, materials, core)
    if warnings or not theory_layers:
        return {
            "available": False,
            "warnings": warnings or ["No laminate theory layers could be generated."],
            "layers": [],
        }

    try:
        full_trace = _compute_trace(theory_layers)
        top_layers = [layer for layer in theory_layers if layer.get("zone") == "top"]
        top_trace = _compute_trace(top_layers) if top_layers else None
        top_equivalent = (
            _equivalent_properties(top_trace["a_matrix"], top_trace["d_matrix"], top_trace["total_thickness_mm"])
            if top_trace and top_trace["total_thickness_mm"] > 0
            else None
        )
        equivalent = _equivalent_properties(full_trace["a_matrix"], full_trace["d_matrix"], full_trace["total_thickness_mm"])
        bending = _three_point_bending_theory(
            structure,
            full_trace,
            top_trace,
            core_thickness_mm=float(core.get("thickness_mm") or 0.0),
            specimen_length_mm=specimen_length_mm,
        )
    except Exception as exc:
        return {
            "available": False,
            "warnings": [*warnings, str(exc)],
            "layers": theory_layers,
        }

    return {
        "available": True,
        "warnings": warnings,
        "layers": full_trace["layers"],
        "trace": {
            "total_thickness_mm": full_trace["total_thickness_mm"],
            "z_interfaces_mm": full_trace["z_interfaces_mm"],
            "a_matrix": full_trace["a_matrix"],
            "b_matrix": full_trace["b_matrix"],
            "d_matrix": full_trace["d_matrix"],
            "a1_matrix": equivalent["a1_matrix"],
            "d1_matrix": equivalent["d1_matrix"],
        },
        "equivalent_properties": equivalent,
        "skin_equivalent_properties": top_equivalent,
        "elastic_gradient_theory": bending,
    }


def generate_shuffle_variants(
    payload: dict[str, Any],
    materials: Iterable[Material | dict[str, Any]],
) -> dict[str, Any]:
    catalog = [m if isinstance(m, Material) else Material.from_mapping(m) for m in materials]
    by_id: dict[str, Material] = {}
    for material in catalog:
        for key in (material.id, material.name, material.technical_id):
            if key not in (None, ""):
                by_id[str(key)] = material
        for alias in str(material.aliases or "").replace(";", ",").split(","):
            alias = alias.strip()
            if alias:
                by_id[alias] = material
    material_ids = [str(item) for item in payload.get("material_ids") or [] if str(item)]
    if not material_ids and payload.get("material_id") not in (None, ""):
        material_ids = [str(payload.get("material_id"))]
    selected_materials = []
    seen_materials: set[int] = set()
    for item in material_ids:
        material = by_id.get(item)
        if material is None:
            continue
        marker = id(material)
        if marker not in seen_materials:
            seen_materials.add(marker)
            selected_materials.append(material)
    if not selected_materials:
        raise ValueError("At least one shuffle fibre material is required")

    total = int(finite_number(payload.get("total_layers"), 0) or 0)
    zero_count = int(finite_number(payload.get("zero_plies"), 0) or 0)
    max_variants = max(1, min(int(finite_number(payload.get("max_variants"), 500) or 500), 2000))
    orientations = [normalize_orientation(item) for item in payload.get("orientations") or []]
    orientations = [item for item in orientations if item]
    non_zero_orientations = [item for item in orientations if item != "0"]
    fix_layer_two = bool(payload.get("fix_layer_two"))
    layer_one_always_rc = bool(payload.get("layer_one_always_rc"))
    core = get_core_definition(payload.get("core"))
    width = finite_number(payload.get("specimen_width_mm"), DEFAULT_SPECIMEN_WIDTH_MM) or DEFAULT_SPECIMEN_WIDTH_MM
    length = finite_number(payload.get("specimen_length_mm"), DEFAULT_SPECIMEN_LENGTH_MM) or DEFAULT_SPECIMEN_LENGTH_MM
    rc_material = next(
        (
            m
            for m in selected_materials
            if "rc" in f"{m.name} {m.technical_id} {m.aliases}".lower()
            and m.fiber_type == "bidirectional"
        ),
        None,
    )
    if layer_one_always_rc and rc_material is None:
        raise ValueError("Layer 1 always RC requires a selected bidirectional RC material")

    if total < 1:
        raise ValueError("Total carbon layers must be at least 1")
    if zero_count < 0 or zero_count > total:
        raise ValueError("Number of 0 degree plies must be between 0 and total layers")
    if zero_count and "0" not in orientations:
        raise ValueError("0 degree must be enabled when 0 degree plies are requested")
    if zero_count < total and not non_zero_orientations:
        raise ValueError("Select at least one non-0 orientation")
    if fix_layer_two and (total < 2 or zero_count < 1):
        raise ValueError("Fix one 0 degree ply in layer 2 requires at least two layers and one 0 degree ply")

    variants: list[list[str]] = []
    seen: set[str] = set()
    fixed_index = 1 if fix_layer_two else -1

    def compatible_materials(orientation: str, index: int) -> list[Material]:
        if layer_one_always_rc and index == 0:
            return [rc_material] if rc_material and orientation in BIDIRECTIONAL_ORIENTATIONS else []
        if orientation in UD_ORIENTATIONS:
            return [m for m in selected_materials if m.fiber_type == "unidirectional"]
        return [m for m in selected_materials if m.fiber_type == "bidirectional"]

    def orientation_allowed_at(index: int, orientation: str) -> bool:
        return bool(compatible_materials(orientation, index))

    def walk(index: int, sequence: list[str], zeros_left: int) -> None:
        if len(variants) >= max_variants:
            return
        if index == total:
            if zeros_left == 0:
                signature = "/".join(sequence)
                if signature not in seen:
                    seen.add(signature)
                    variants.append(sequence)
            return
        if index == fixed_index:
            if orientation_allowed_at(index, "0"):
                walk(index + 1, [*sequence, "0"], zeros_left - 1)
            return

        remaining_after = total - index - 1 - (1 if fixed_index > index else 0)
        if zeros_left > 0 and zeros_left - 1 <= remaining_after and orientation_allowed_at(index, "0"):
            walk(index + 1, [*sequence, "0"], zeros_left - 1)
        if remaining_after >= zeros_left:
            for orientation in non_zero_orientations:
                if orientation_allowed_at(index, orientation):
                    walk(index + 1, [*sequence, orientation], zeros_left)

    walk(0, [], zero_count)

    results: list[dict[str, Any]] = []
    seen_material_signatures: set[str] = set()

    def material_sequence_text(layers: list[dict[str, Any]]) -> str:
        skin = "/".join(
            f"{layer.get('material_name')}:{normalize_orientation(layer.get('orientation'))}º"
            for layer in layers
        )
        return f"[{skin}] S"

    def orientation_sequence_text(layers: list[dict[str, Any]]) -> str:
        skin = "/".join(f"{normalize_orientation(layer.get('orientation'))}º" for layer in layers)
        return f"[{skin}] S"

    def cf_code(layer: dict[str, Any]) -> str:
        name = str(layer.get("material_name") or "").strip()
        return name or "-"

    def cf_sequence_text(layers: list[dict[str, Any]]) -> str:
        return f"[{'/'.join(cf_code(layer) for layer in layers)}]"

    def material_walk(sequence: list[str], index: int, layers: list[dict[str, Any]]) -> None:
        if len(results) >= max_variants:
            return
        if index == len(sequence):
            signature = "/".join(f"{layer['material_id']}:{layer['orientation']}" for layer in layers)
            if signature in seen_material_signatures:
                return
            seen_material_signatures.add(signature)
            append_result(len(results) + 1, sequence, layers)
            return
        for ply_material in compatible_materials(sequence[index], index):
            material_walk(
                sequence,
                index + 1,
                [
                    *layers,
                    {
                        "material_id": ply_material.id,
                        "material_name": ply_material.name,
                        "orientation": sequence[index],
                    },
                ],
            )

    def append_result(index: int, sequence: list[str], top_skin: list[dict[str, Any]]) -> None:
        laminate = {
            "top_skin": top_skin,
            "bottom_skin": list(reversed(top_skin)),
            "core": core,
        }
        calculated = calculate_laminate(laminate, catalog, specimen_width_mm=width, specimen_length_mm=length)
        theory = calculated.get("laminate_theory") or {}
        bending = theory.get("elastic_gradient_theory") or {}
        results.append(
            {
                "index": index,
                "orientations": sequence,
                "laminate": laminate,
                "laminate_sequence": calculated.get("laminate_sequence"),
                "orientation_laminate_sequence": orientation_sequence_text(top_skin),
                "cf_sequence": cf_sequence_text(top_skin),
                "material_laminate_sequence": material_sequence_text(top_skin),
                "total_weight_g": calculated.get("total_weight_g"),
                "total_thickness_mm": calculated.get("total_thickness_mm"),
                "top_skin_thickness_mm": calculated.get("top_skin_thickness_mm"),
                "bottom_skin_thickness_mm": calculated.get("bottom_skin_thickness_mm"),
                "core_thickness_mm": calculated.get("core_thickness_mm"),
                "zero_percent": calculated.get("zero_percent"),
                "warping_percent": calculated.get("warping_percent"),
                "elastic_gradient_theory": bending.get("elastic_gradient_theory"),
                "ei_theory": bending.get("ei_theory"),
                "laminate_theory": theory,
                "laminate_theory_available": theory.get("available"),
                "warnings": theory.get("warnings") or [],
            }
        )

    for sequence in variants:
        if len(results) >= max_variants:
            break
        material_walk(sequence, 0, [])

    return {
        "count": len(results),
        "truncated": len(results) >= max_variants,
        "assumption": "Each generated sequence is treated as the top skin and mirrored around the selected core.",
        "variants": results,
    }


def clean_curve(points: Iterable[dict[str, Any] | tuple[float, float]]) -> list[dict[str, float]]:
    rows: list[tuple[float, float]] = []
    for point in points:
        if isinstance(point, dict):
            x = finite_number(point.get("x_mm"))
            y = finite_number(point.get("y_n"))
        else:
            x = finite_number(point[0])
            y = finite_number(point[1])
        if x is not None and y is not None:
            rows.append((x, y))
    rows.sort(key=lambda p: p[0])

    deduped: list[dict[str, float]] = []
    seen: set[float] = set()
    for x, y in rows:
        key = round(x, 12)
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"x_mm": x, "y_n": y})
    return deduped


def max_slope_pair(points: list[dict[str, float]], min_dx_mm: float = DEFAULT_MIN_SLOPE_DX_MM) -> dict[str, float]:
    if len(points) < 2:
        raise ValueError("At least two points are required to calculate slope")
    best: tuple[float, int, int] | None = None
    xs = [p["x_mm"] for p in points]
    ys = [p["y_n"] for p in points]
    n = len(points)
    for i in range(n - 1):
        xi = xs[i]
        yi = ys[i]
        for j in range(i + 1, n):
            dx = xs[j] - xi
            if dx < min_dx_mm:
                continue
            slope = (ys[j] - yi) / dx
            if best is None or slope > best[0]:
                best = (slope, i, j)
    if best is None:
        raise ValueError(f"No valid slope pair found with dx >= {min_dx_mm:.3f} mm")

    slope, i, j = best
    x1 = xs[i]
    x2 = xs[j]
    y1 = ys[i]
    y2 = ys[j]
    return {
        "x1_mm": x1,
        "x2_mm": x2,
        "y1_n": y1,
        "y2_n": y2,
        "slope_n_per_mm": slope,
        "intercept_n": y1 - slope * x1,
    }


def compute_3pb_common(
    points: Iterable[dict[str, Any] | tuple[float, float]],
    min_dx_mm: float = DEFAULT_MIN_SLOPE_DX_MM,
) -> dict[str, Any]:
    curve = clean_curve(points)
    if len(curve) < 3:
        raise ValueError("Not enough load-displacement points found")
    max_index, max_point = max(enumerate(curve), key=lambda item: item[1]["y_n"])
    ascending = curve[: max_index + 1]
    region = max_slope_pair(ascending, min_dx_mm=min_dx_mm)
    return {
        "max_force_n": max_point["y_n"],
        "max_force_x_mm": max_point["x_mm"],
        "linear_region": region,
    }


def energy_absorbed_until_displacement(
    points: Iterable[dict[str, Any] | tuple[float, float]],
    target_mm: float = 12.7,
) -> dict[str, float | bool | None]:
    curve = [point for point in clean_curve(points) if point["x_mm"] >= 0]
    if not curve:
        return {
            "energyAbsorbedJ": math.nan,
            "energy_absorbed_j": math.nan,
            "energy_absorbed_start_mm": math.nan,
            "energy_absorbed_end_mm": math.nan,
            "energy_absorbed_target_mm": target_mm,
            "energy_absorbed_started_after_zero": False,
            "energy_absorbed_truncated_before_target": True,
            "energy_absorbed_method": "excel_right_endpoint_sum",
        }

    first_x = curve[0]["x_mm"]
    last_x = curve[-1]["x_mm"]
    if first_x > target_mm:
        return {
            "energyAbsorbedJ": 0.0,
            "energy_absorbed_j": 0.0,
            "energy_absorbed_start_mm": first_x,
            "energy_absorbed_end_mm": first_x,
            "energy_absorbed_target_mm": target_mm,
            "energy_absorbed_started_after_zero": first_x > 0,
            "energy_absorbed_truncated_before_target": last_x < target_mm,
            "energy_absorbed_method": "excel_right_endpoint_sum",
        }

    endpoint_index = min(range(len(curve)), key=lambda index: abs(curve[index]["x_mm"] - target_mm))
    end_x = curve[endpoint_index]["x_mm"]
    if endpoint_index <= 0:
        return {
            "energyAbsorbedJ": 0.0,
            "energy_absorbed_j": 0.0,
            "energy_absorbed_start_mm": first_x,
            "energy_absorbed_end_mm": end_x,
            "energy_absorbed_target_mm": target_mm,
            "energy_absorbed_started_after_zero": first_x > 0,
            "energy_absorbed_truncated_before_target": last_x < target_mm,
            "energy_absorbed_method": "excel_right_endpoint_sum",
        }

    area_n_mm = 0.0
    for previous, current in zip(curve[:endpoint_index], curve[1 : endpoint_index + 1]):
        dx = current["x_mm"] - previous["x_mm"]
        if dx > 0:
            area_n_mm += dx * current["y_n"]

    energy_j = area_n_mm / 1000.0
    return {
        "energyAbsorbedJ": energy_j,
        "energy_absorbed_j": energy_j,
        "energy_absorbed_start_mm": first_x,
        "energy_absorbed_end_mm": end_x,
        "energy_absorbed_target_mm": target_mm,
        "energy_absorbed_started_after_zero": first_x > 0,
        "energy_absorbed_truncated_before_target": last_x < target_mm,
        "energy_absorbed_method": "excel_right_endpoint_sum",
    }


def second_moment_panel(core_thickness_mm: float, skin_thickness_mm: float, panel_height_mm: float) -> float:
    x5 = panel_height_mm
    x6 = skin_thickness_mm
    y5 = panel_height_mm
    y6 = skin_thickness_mm
    x8 = x5 * x6
    x9 = y5 * y6
    x10 = x6 / 2.0
    x11 = (core_thickness_mm + 2.0 * skin_thickness_mm) - 0.5 * skin_thickness_mm
    x12 = (x8 * x10 + x9 * x11) / (x8 + x9)
    z8 = (x5 * x6**3) / 12.0
    z9 = (y5 * y6**3) / 12.0
    z10 = z8 + (x8 * (x12 - x10) ** 2)
    z11 = z9 + (x9 * (x12 - x11) ** 2)
    return z10 + z11


def derive_skin_thickness(
    theoretical: dict[str, Any] | None,
    core_thickness_mm: float | None,
    real_thickness_mm: float | None,
    explicit_skin_thickness_mm: float | None = None,
) -> float:
    if explicit_skin_thickness_mm is not None and explicit_skin_thickness_mm > 0:
        return explicit_skin_thickness_mm
    if real_thickness_mm is not None and core_thickness_mm is not None:
        calculated = (real_thickness_mm - core_thickness_mm) / 2.0
        if calculated > 0:
            return calculated
    if theoretical and theoretical.get("total_thickness_mm"):
        return float(theoretical["total_thickness_mm"]) / 2.0
    return math.nan


def derive_skin_thicknesses(
    theoretical: dict[str, Any] | None,
    top_skin_thickness_mm: float | None = None,
    bottom_skin_thickness_mm: float | None = None,
    legacy_skin_thickness_mm: float | None = None,
    real_thickness_mm: float | None = None,
    core_thickness_mm: float | None = None,
) -> tuple[float, float, float]:
    top = finite_number(top_skin_thickness_mm)
    bottom = finite_number(bottom_skin_thickness_mm)
    if top is None and theoretical:
        top = finite_number(theoretical.get("top_skin_thickness_mm"))
    if bottom is None and theoretical:
        bottom = finite_number(theoretical.get("bottom_skin_thickness_mm"))

    if (top is None or bottom is None) and legacy_skin_thickness_mm is not None:
        legacy = finite_number(legacy_skin_thickness_mm)
        if legacy is not None:
            top = legacy if top is None else top
            bottom = legacy if bottom is None else bottom

    if (top is None or bottom is None) and real_thickness_mm is not None and core_thickness_mm is not None:
        equivalent = (float(real_thickness_mm) - float(core_thickness_mm)) / 2.0
        if equivalent > 0:
            top = equivalent if top is None else top
            bottom = equivalent if bottom is None else bottom

    top = float(top) if top is not None else math.nan
    bottom = float(bottom) if bottom is not None else math.nan
    equivalent = (top + bottom) / 2.0 if math.isfinite(top) and math.isfinite(bottom) else math.nan
    return top, bottom, equivalent


def compute_3pb_panel_results(
    common: dict[str, Any],
    core_thickness_mm: float,
    skin_thickness_mm: float,
    skin_total_thickness_mm: float,
    specimen_length_mm: float = DEFAULT_SPECIMEN_LENGTH_MM,
    span_mm: float = DEFAULT_SPAN_MM,
    panel_heights_mm: dict[str, Any] | None = None,
) -> dict[str, dict[str, float | str | None]]:
    max_force_n = float(common["max_force_n"])
    region = common["linear_region"]
    dx = float(region["x2_mm"]) - float(region["x1_mm"])
    slope = float(region["slope_n_per_mm"])

    probe_second_moment_mm4 = specimen_length_mm * (
        (core_thickness_mm + skin_total_thickness_mm) ** 3 - core_thickness_mm**3
    ) / 12.0
    sigma_uts_pa = (
        max_force_n
        * span_mm
        * 0.5
        * (core_thickness_mm + 2.0 * skin_thickness_mm)
        / (4.0 * probe_second_moment_mm4)
    ) * 1_000_000.0

    out: dict[str, dict[str, float | str | None]] = {}
    for panel_code in PANEL_CODES:
        obj = PANEL_CONSTANTS[panel_code]
        panel_height_mm = finite_number(
            (panel_heights_mm or {}).get(panel_code),
            obj["panel_height_mm"],
        )
        panel_second_moment_mm4 = second_moment_panel(
            core_thickness_mm, skin_thickness_mm, panel_height_mm
        )
        panel_second_moment_m4 = panel_second_moment_mm4 / 10.0**12
        e_gpa = (slope * span_mm**3 / (48.0 * probe_second_moment_mm4)) * 0.001
        if dx < DEFAULT_MIN_SLOPE_DX_MM:
            ei_gpa_m4 = math.nan
            ei_message = "Distance between x1 and x2 < 1 mm"
        else:
            ei_gpa_m4 = e_gpa * 10.0**9 * panel_second_moment_m4
            ei_message = ""

        effective_skin_area_mm2 = ((core_thickness_mm + 2.0 * skin_thickness_mm) - core_thickness_mm) * panel_height_mm
        yield_probe_n = effective_skin_area_mm2 * sigma_uts_pa / 1_000_000.0
        uts_probe_n = yield_probe_n
        max_load_midspan_probe_n = (
            4.0 * sigma_uts_pa * panel_second_moment_m4 / (0.001 * 0.5 * (core_thickness_mm + 2.0 * skin_thickness_mm))
        )
        max_deflection_probe_m = obj["max_load_target_n"] / (48.0 * ei_gpa_m4) if ei_gpa_m4 else math.nan
        energy_absorbed_j = (
            0.5 * max_load_midspan_probe_n * (max_load_midspan_probe_n / (48.0 * ei_gpa_m4))
            if ei_gpa_m4
            else math.nan
        )

        skip_strength_cs = panel_code in {"SISv", "SISh"}
        out[panel_code] = {
            "probe_second_moment_mm4": probe_second_moment_mm4,
            "core_thickness_mm": core_thickness_mm,
            "skin_thickness_mm": skin_thickness_mm,
            "skin_total_thickness_mm": skin_total_thickness_mm,
            "sigma_uts_pa": sigma_uts_pa,
            "panel_height_mm": panel_height_mm,
            "panel_second_moment_mm4": panel_second_moment_mm4,
            "panel_second_moment_m4": panel_second_moment_m4,
            "e_gpa": e_gpa,
            "ei_gpa_m4": ei_gpa_m4,
            "ei_message": ei_message,
            "ei_target_gpa_m4": obj["ei_target_gpa_m4"],
            "cs_ei": ei_gpa_m4 / obj["ei_target_gpa_m4"] if ei_gpa_m4 else math.nan,
            "yield_probe_n": yield_probe_n,
            "yield_target_n": obj["yield_target_n"],
            "cs_yield": math.nan if skip_strength_cs else yield_probe_n / obj["yield_target_n"],
            "uts_probe_n": uts_probe_n,
            "uts_target_n": obj["uts_target_n"],
            "cs_uts": math.nan if skip_strength_cs else uts_probe_n / obj["uts_target_n"],
            "max_load_midspan_probe_n": max_load_midspan_probe_n,
            "max_load_target_n": obj["max_load_target_n"],
            "cs_max_load_midspan": math.nan if skip_strength_cs else max_load_midspan_probe_n / obj["max_load_target_n"],
            "max_deflection_probe_m": max_deflection_probe_m,
            "max_deflection_target_m": obj["max_deflection_target_m"],
            "cs_max_deflection": (
                math.nan if skip_strength_cs or not math.isfinite(max_deflection_probe_m)
                else max_deflection_probe_m / obj["max_deflection_target_m"]
            ),
            "energy_absorbed_probe_j": energy_absorbed_j,
            "energy_target_j": obj["energy_target_j"],
            "cs_energy": (
                math.nan if skip_strength_cs or not math.isfinite(energy_absorbed_j)
                else energy_absorbed_j / obj["energy_target_j"]
            ),
        }
    return out


def fallback_two_separated_peaks(points: list[dict[str, float]], min_dist: float) -> list[dict[str, float]]:
    ranked = sorted(points, key=lambda p: p["y_n"], reverse=True)
    selected: list[dict[str, float]] = []
    for point in ranked:
        if all(abs(point["x_mm"] - other["x_mm"]) >= min_dist for other in selected):
            selected.append(point)
        if len(selected) >= 2:
            break
    if len(selected) < 2 and ranked:
        selected = ranked[: min(2, len(ranked))]
    return selected


def find_shear_peaks(
    points: Iterable[dict[str, Any] | tuple[float, float]],
    min_peak_distance_mm: float | None = None,
    peak_prominence_fraction: float = DEFAULT_PEAK_PROMINENCE_FRACTION,
) -> dict[str, Any]:
    curve = clean_curve(points)
    if len(curve) < 3:
        raise ValueError("Not enough load-displacement points found")
    x_min = curve[0]["x_mm"]
    x_max = curve[-1]["x_mm"]
    if min_peak_distance_mm is None:
        min_peak_distance_mm = max(1.0, 0.20 * (x_max - x_min))
    threshold = peak_prominence_fraction * max(abs(p["y_n"]) for p in curve)
    local_peaks: list[dict[str, float]] = []

    for i in range(1, len(curve) - 1):
        y_prev = curve[i - 1]["y_n"]
        y = curve[i]["y_n"]
        y_next = curve[i + 1]["y_n"]
        if y >= y_prev and y >= y_next and (y - min(y_prev, y_next)) >= threshold:
            local_peaks.append(curve[i])

    local_peaks.sort(key=lambda p: p["y_n"], reverse=True)
    separated: list[dict[str, float]] = []
    for peak in local_peaks:
        if all(abs(peak["x_mm"] - other["x_mm"]) >= min_peak_distance_mm for other in separated):
            separated.append(peak)
        if len(separated) >= 2:
            break
    if len(separated) < 2:
        separated = fallback_two_separated_peaks(curve, min_peak_distance_mm)

    top_two = sorted(separated[:2], key=lambda p: p["y_n"], reverse=True)
    high = top_two[0]
    low = top_two[1] if len(top_two) > 1 else top_two[0]
    return {
        "highest_peak_n": high["y_n"],
        "highest_peak_x_mm": high["x_mm"],
        "lowest_peak_n": low["y_n"],
        "lowest_peak_x_mm": low["x_mm"],
        "min_peak_distance_mm": min_peak_distance_mm,
    }


def compute_shear_panel_results(shear_common: dict[str, Any], skin_thickness_mm: float) -> dict[str, dict[str, float]]:
    low_peak = float(shear_common["lowest_peak_n"])
    high_peak = float(shear_common["highest_peak_n"])
    out: dict[str, dict[str, float]] = {}
    for panel_code in PANEL_CODES:
        if not skin_thickness_mm or not math.isfinite(skin_thickness_mm):
            shear_stress = math.nan
        elif panel_code in {"FBH", "FHB", "SHB", "MHBS", "SISh"}:
            shear_stress = low_peak / (math.pi * 25.0 * skin_thickness_mm)
        elif panel_code in {"FBHS", "SISv"}:
            shear_stress = high_peak / (math.pi * 25.0 * skin_thickness_mm)
        else:
            shear_stress = math.nan

        if panel_code == "FBH" and math.isfinite(shear_stress):
            perimeter_shear_probe = (OUTER_WIDTH_MM + OUTER_HEIGHT_MM) * 0.002 * (skin_thickness_mm / 1000.0) * shear_stress * 10.0**6
            perimeter_shear_target = 510000.0
            cs_perimeter_shear = perimeter_shear_probe / perimeter_shear_target
        else:
            perimeter_shear_probe = math.nan
            perimeter_shear_target = math.nan
            cs_perimeter_shear = math.nan
        out[panel_code] = {
            "shear_stress_mpa": shear_stress,
            "perimeter_shear_probe_n": perimeter_shear_probe,
            "perimeter_shear_target_n": perimeter_shear_target,
            "cs_perimeter_shear": cs_perimeter_shear,
        }
    return out


def lttb_reduce(points: Iterable[dict[str, Any]], threshold: int = 300) -> list[dict[str, float]]:
    data = clean_curve(points)
    if threshold >= len(data) or threshold <= 0:
        return data
    if threshold < 3:
        return [data[0], data[-1]]

    sampled = [data[0]]
    bucket_size = (len(data) - 2) / (threshold - 2)
    a = 0
    for i in range(threshold - 2):
        start = int(math.floor((i + 1) * bucket_size)) + 1
        end = int(math.floor((i + 2) * bucket_size)) + 1
        end = min(end, len(data))
        bucket = data[start:end] or [data[min(start, len(data) - 1)]]

        avg_start = int(math.floor((i + 2) * bucket_size)) + 1
        avg_end = int(math.floor((i + 3) * bucket_size)) + 1
        avg_end = min(avg_end, len(data))
        avg_range = data[avg_start:avg_end] or [data[-1]]
        avg_x = sum(p["x_mm"] for p in avg_range) / len(avg_range)
        avg_y = sum(p["y_n"] for p in avg_range) / len(avg_range)

        ax = data[a]["x_mm"]
        ay = data[a]["y_n"]
        best_area = -1.0
        best_point = bucket[0]
        best_index = start
        for offset, point in enumerate(bucket):
            area = abs((ax - avg_x) * (point["y_n"] - ay) - (ax - point["x_mm"]) * (avg_y - ay)) * 0.5
            if area > best_area:
                best_area = area
                best_point = point
                best_index = start + offset
        sampled.append(best_point)
        a = best_index
    sampled.append(data[-1])
    return sampled


def process_test(
    points: Iterable[dict[str, Any] | tuple[float, float]],
    test_type: str,
    theoretical: dict[str, Any] | None,
    core_thickness_mm: float | None,
    skin_thickness_mm: float | None,
    real_thickness_mm: float | None,
    top_skin_thickness_mm: float | None = None,
    bottom_skin_thickness_mm: float | None = None,
    specimen_length_mm: float = DEFAULT_SPECIMEN_LENGTH_MM,
    span_mm: float = DEFAULT_SPAN_MM,
    energy_target_mm: float = 12.7,
    panel_heights_mm: dict[str, Any] | None = None,
) -> dict[str, Any]:
    curve = clean_curve(points)
    reduced = lttb_reduce(curve, threshold=300)
    kind = str(test_type or "").upper()
    core = (
        float(core_thickness_mm)
        if core_thickness_mm is not None
        else float(theoretical.get("core_thickness_mm", math.nan)) if theoretical else math.nan
    )
    top_skin, bottom_skin, skin_each = derive_skin_thicknesses(
        theoretical,
        top_skin_thickness_mm=top_skin_thickness_mm,
        bottom_skin_thickness_mm=bottom_skin_thickness_mm,
        legacy_skin_thickness_mm=skin_thickness_mm,
        real_thickness_mm=real_thickness_mm,
        core_thickness_mm=core,
    )

    if "SHEAR" in kind:
        common = find_shear_peaks(curve)
        panel_results = compute_shear_panel_results(common, skin_each)
        selected_points = [
            {"role": "higher_peak", "x_mm": common["highest_peak_x_mm"], "y_n": common["highest_peak_n"]},
            {"role": "lower_peak", "x_mm": common["lowest_peak_x_mm"], "y_n": common["lowest_peak_n"]},
        ]
        mode = "Shear"
    else:
        common = compute_3pb_common(curve)
        if is_energy_absorbed_test(test_type):
            common.update(energy_absorbed_until_displacement(curve, target_mm=energy_target_mm))
        skin_total = (
            top_skin + bottom_skin
            if math.isfinite(top_skin) and math.isfinite(bottom_skin)
            else float(theoretical.get("total_skin_thickness_mm", math.nan)) if theoretical else math.nan
        )
        panel_results = compute_3pb_panel_results(
            common,
            core_thickness_mm=core,
            skin_thickness_mm=skin_each,
            skin_total_thickness_mm=skin_total,
            specimen_length_mm=specimen_length_mm,
            span_mm=span_mm,
            panel_heights_mm=panel_heights_mm,
        )
        region = common["linear_region"]
        selected_points = [
            {"role": "x1_y1", "x_mm": region["x1_mm"], "y_n": region["y1_n"]},
            {"role": "x2_y2", "x_mm": region["x2_mm"], "y_n": region["y2_n"]},
            {"role": "ymax", "x_mm": common["max_force_x_mm"], "y_n": common["max_force_n"]},
        ]
        mode = "3PBT"

    return {
        "mode": mode,
        "common": common,
        "panel_results": panel_results,
        "selected_points": selected_points,
        "raw_point_count": len(curve),
        "reduced_point_count": len(reduced),
        "skin_thickness_each_side_mm": skin_each,
        "top_skin_thickness_mm": top_skin,
        "bottom_skin_thickness_mm": bottom_skin,
        "core_thickness_mm": core,
        "raw_points": curve,
        "reduced_points": reduced,
    }


def safe_json(value: Any) -> Any:
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    if isinstance(value, dict):
        return {k: safe_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [safe_json(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return safe_json(asdict(value))
    return value
