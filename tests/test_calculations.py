from __future__ import annotations

import math
import unittest

from ses_engine.calculations import (
    DEFAULT_MATERIALS,
    Material,
    calculate_laminate,
    compute_3pb_common,
    compute_3pb_panel_results,
    energy_absorbed_until_displacement,
    is_energy_absorbed_test,
    laminate_sequence,
    lttb_reduce,
    process_test,
)


class CalculationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.materials = [
            Material(id=index + 1, **material)
            for index, material in enumerate(DEFAULT_MATERIALS)
        ]
        self.rc = self.materials[0]
        self.ud = self.materials[1]

    def test_laminate_matches_workbook_p02_03_half_stack(self) -> None:
        layers = [
            {"material_id": self.rc.id, "orientation": "+-90"},
            {"material_id": self.ud.id, "orientation": "0"},
            {"material_id": self.rc.id, "orientation": "+-45"},
        ]
        result = calculate_laminate(layers, self.materials)
        self.assertAlmostEqual(result["total_thickness_mm"], 1.16, places=6)
        self.assertAlmostEqual(result["fiber_weight_g"], 155.65, places=6)
        self.assertAlmostEqual(result["zero_percent"], 69.85 / 155.65, places=9)
        self.assertAlmostEqual(result["warping_percent"], 41.25 / 155.65, places=9)

    def test_top_core_bottom_laminate_tracks_skin_asymmetry(self) -> None:
        laminate = {
            "core": {"key": "balsa"},
            "top_skin": [
                {"material_id": self.rc.id, "orientation": "+-45"},
                {"material_id": self.ud.id, "orientation": "0"},
            ],
            "bottom_skin": [
                {"material_id": self.rc.id, "orientation": "+-45"},
                {"material_id": self.ud.id, "orientation": "90"},
            ],
        }
        result = calculate_laminate(laminate, self.materials)
        self.assertAlmostEqual(result["core_thickness_mm"], 9.5)
        self.assertAlmostEqual(result["top_skin_thickness_mm"], 0.73)
        self.assertAlmostEqual(result["bottom_skin_thickness_mm"], 0.73)
        self.assertAlmostEqual(result["total_thickness_mm"], 10.96)
        self.assertGreater(result["warping_percent"], 0)
        self.assertEqual(result["laminate_sequence"], "[+-45º/0º] Core [+-45º/90º]")

    def test_laminate_sequence_marks_empty_layers_incomplete(self) -> None:
        laminate = {
            "core": {"key": "balsa"},
            "top_skin": [{"material_id": self.rc.id, "orientation": "+-45"}],
            "bottom_skin": [{"material_id": "", "orientation": ""}],
        }
        self.assertEqual(laminate_sequence(laminate), "Incomplete laminate")

    def test_3pb_panel_formula_matches_reference_mhbs_value(self) -> None:
        common = {
            "max_force_n": 20742.53,
            "max_force_x_mm": 0.0,
            "linear_region": {
                "x1_mm": 2.025177,
                "x2_mm": 3.509643,
                "y1_n": 6160.313,
                "y2_n": 11511.62,
                "slope_n_per_mm": 3604.8700340728583,
                "intercept_n": 0.0,
            },
        }
        results = compute_3pb_panel_results(
            common,
            core_thickness_mm=20.0,
            skin_thickness_mm=1.18,
            skin_total_thickness_mm=2.36,
            specimen_length_mm=275.0,
            span_mm=400.0,
        )
        self.assertAlmostEqual(results["MHBS"]["ei_gpa_m4"], 4337.554406573872, places=6)
        self.assertAlmostEqual(results["MHBS"]["cs_ei"], 1.6184904502141315, places=9)

    def test_3pb_panel_formula_uses_car_panel_height_override(self) -> None:
        common = {
            "max_force_n": 20742.53,
            "max_force_x_mm": 0.0,
            "linear_region": {
                "x1_mm": 2.025177,
                "x2_mm": 3.509643,
                "y1_n": 6160.313,
                "y2_n": 11511.62,
                "slope_n_per_mm": 3604.8700340728583,
                "intercept_n": 0.0,
            },
        }
        baseline = compute_3pb_panel_results(
            common,
            core_thickness_mm=20.0,
            skin_thickness_mm=1.18,
            skin_total_thickness_mm=2.36,
            specimen_length_mm=275.0,
            span_mm=400.0,
        )
        adjusted = compute_3pb_panel_results(
            common,
            core_thickness_mm=20.0,
            skin_thickness_mm=1.18,
            skin_total_thickness_mm=2.36,
            specimen_length_mm=275.0,
            span_mm=400.0,
            panel_heights_mm={"MHBS": 300.0},
        )
        self.assertAlmostEqual(adjusted["MHBS"]["panel_height_mm"], 300.0)
        self.assertGreater(adjusted["MHBS"]["cs_ei"], baseline["MHBS"]["cs_ei"])

    def test_max_slope_requires_one_mm_segment(self) -> None:
        points = [
            {"x_mm": 0.0, "y_n": 0.0},
            {"x_mm": 0.5, "y_n": 5000.0},
            {"x_mm": 1.2, "y_n": 6000.0},
            {"x_mm": 2.4, "y_n": 6500.0},
        ]
        result = compute_3pb_common(points)
        region = result["linear_region"]
        self.assertGreaterEqual(region["x2_mm"] - region["x1_mm"], 1.0)

    def test_lttb_preserves_endpoints_and_budget(self) -> None:
        points = [{"x_mm": i / 10, "y_n": math.sin(i / 10)} for i in range(1000)]
        reduced = lttb_reduce(points, threshold=300)
        self.assertEqual(len(reduced), 300)
        self.assertEqual(reduced[0], points[0])
        self.assertEqual(reduced[-1], points[-1])

    def test_energy_absorbed_matches_excel_right_endpoint_sum_to_nearest_target(self) -> None:
        points = [
            {"x_mm": 20.0, "y_n": 20000.0},
            {"x_mm": 0.0, "y_n": 0.0},
            {"x_mm": 10.0, "y_n": 10000.0},
        ]
        result = energy_absorbed_until_displacement(points, target_mm=12.7)
        self.assertAlmostEqual(result["energyAbsorbedJ"], 100.0, places=6)
        self.assertAlmostEqual(result["energy_absorbed_j"], 100.0, places=6)
        self.assertAlmostEqual(result["energy_absorbed_end_mm"], 10.0)
        self.assertEqual(result["energy_absorbed_method"], "excel_right_endpoint_sum")

    def test_energy_absorbed_starts_from_first_available_point_above_zero(self) -> None:
        points = [
            {"x_mm": 2.0, "y_n": 1000.0},
            {"x_mm": 12.7, "y_n": 1000.0},
        ]
        result = energy_absorbed_until_displacement(points, target_mm=12.7)
        self.assertTrue(result["energy_absorbed_started_after_zero"])
        self.assertAlmostEqual(result["energyAbsorbedJ"], 10.7, places=6)
        self.assertAlmostEqual(result["energy_absorbed_j"], 10.7, places=6)

    def test_side_impact_test_type_calculates_energy_absorbed(self) -> None:
        points = [
            {"x_mm": 0.0, "y_n": 0.0},
            {"x_mm": 10.0, "y_n": 10000.0},
            {"x_mm": 20.0, "y_n": 20000.0},
        ]
        self.assertTrue(is_energy_absorbed_test("Vertical Side Impact Structure"))
        self.assertTrue(is_energy_absorbed_test("Three Point Bending"))
        result = process_test(
            points,
            test_type="Three Point Bending",
            theoretical={"total_skin_thickness_mm": 2.0, "core_thickness_mm": 20.0},
            core_thickness_mm=20.0,
            skin_thickness_mm=1.0,
            real_thickness_mm=22.0,
            energy_target_mm=12.7,
        )
        self.assertAlmostEqual(result["common"]["energyAbsorbedJ"], 100.0, places=6)
        self.assertAlmostEqual(result["common"]["energy_absorbed_j"], 100.0, places=6)
        self.assertEqual(result["common"]["energy_absorbed_method"], "excel_right_endpoint_sum")


if __name__ == "__main__":
    unittest.main()
