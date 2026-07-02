import unittest

from ses_engine.excel_io import extract_load_displacement_info


class ExcelIoTests(unittest.TestCase):
    def test_excel_style_kn_force_headers_are_converted_to_newtons(self) -> None:
        rows = [
            ["", "Energy(J)", 132.1, "", "", 9.9, "mm deflection"],
            ["", "", "", "", "", "", ""],
            ["", "F (kN)", "s (mm)"],
            ["", 1.0, 0.0],
            ["", 2.0, 1.5],
            ["", 3.0, 2.0],
        ]
        info = extract_load_displacement_info(rows)
        self.assertEqual(info["load_multiplier"], 1000.0)
        self.assertEqual(info["energy_target_mm"], 9.9)
        self.assertEqual(info["points"][0], {"x_mm": 0.0, "y_n": 1000.0})
        self.assertEqual(info["points"][2], {"x_mm": 2.0, "y_n": 3000.0})

    def test_post_processing_force_headers_are_kept_as_newtons(self) -> None:
        rows = [
            ["Force [N]", "Displacement [mm]"],
            [100.0, 0.0],
            [200.0, 1.0],
            [300.0, 2.0],
        ]
        info = extract_load_displacement_info(rows)
        self.assertEqual(info["load_multiplier"], 1.0)
        self.assertEqual(info["points"][0], {"x_mm": 0.0, "y_n": 100.0})
        self.assertEqual(info["points"][2], {"x_mm": 2.0, "y_n": 300.0})


if __name__ == "__main__":
    unittest.main()
