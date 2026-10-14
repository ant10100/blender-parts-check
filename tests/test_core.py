"""Behavioral tests run without Blender or third-party packages."""
import json
import math
import unittest

from blender_parts_check.core import Part, Settings, inspect_parts, opposite_name, report_dict


def part(name, x=2, y=0, dims=(2, 2, 2), **kw):
    center = (x, y, 0)
    lo = tuple(c - d / 2 for c, d in zip(center, dims))
    hi = tuple(c + d / 2 for c, d in zip(center, dims))
    return Part(name, lo, hi, **kw)


class CoreTests(unittest.TestCase):
    def codes(self, parts, **settings):
        return [f.code for f in inspect_parts(parts, Settings(**settings)).findings]

    def test_explicit_naming_only(self):
        for a, b in [("Arm.L", "Arm.R"), ("Arm.R", "Arm.L")]:
            self.assertEqual(opposite_name(a), b)
        for name in ["LeftArm", "L", "Arm.LOD", "Arm.L.01", "Arm.L.001", "Arm_L", "Arm.l"]:
            self.assertIsNone(opposite_name(name))

    def test_normal_pair(self):
        result = inspect_parts([part("Arm.L"), part("Arm.R", -2)])
        self.assertEqual(result.checked_pairs, 1)
        self.assertEqual(result.findings, ())

    def test_missing_is_warning_even_without_mirror(self):
        result = inspect_parts([part("Arm.L")])
        self.assertEqual(result.findings[0].code, "MISSING_PARTNER")
        self.assertEqual(result.findings[0].severity, "WARNING")

    def test_mirror_context_is_not_missing_error(self):
        result = inspect_parts([part("Arm.L", modifiers=("MIRROR",))])
        missing = next(f for f in result.findings if f.code == "MISSING_PARTNER")
        self.assertTrue(missing.metrics["mirror_present"])
        self.assertEqual(missing.severity, "WARNING")

    def test_center_and_dimensions_are_separate(self):
        self.assertIn("CENTER_MISMATCH", self.codes([part("A.L"), part("A.R", -3)]))
        codes = self.codes([part("A.L"), part("A.R", -2, dims=(3, 2, 2))])
        self.assertIn("SIZE_MISMATCH", codes)
        self.assertNotIn("CENTER_MISMATCH", codes)

    def test_plane_axis_offset_and_tolerance(self):
        self.assertNotIn("CENTER_MISMATCH", self.codes(
            [part("A.L", 0, 5), part("A.R", 0, 1)], axis="Y", plane=3))
        self.assertNotIn("CENTER_MISMATCH", self.codes(
            [part("A.L"), part("A.R", -2.0001)], tolerance=0.001))

    def test_excluding_either_partner_suppresses_pair_warning(self):
        self.assertNotIn("MISSING_PARTNER", self.codes([part("A.L")], excluded=frozenset({"A.R"})))
        result = inspect_parts([part("A.L"), part("A.R", -4)],
                               Settings(excluded=frozenset({"A.R"})))
        self.assertEqual(result.checked_pairs, 0)
        self.assertNotIn("CENTER_MISMATCH", [f.code for f in result.findings])

    def test_scale_warnings(self):
        codes = self.codes([part("A.L", scale=(-1, 2, 1), world_mirrored=True)])
        self.assertIn("NEGATIVE_LOCAL_SCALE", codes)
        self.assertIn("UNAPPLIED_SCALE", codes)
        self.assertIn("WORLD_REFLECTION", codes)
        result = inspect_parts([part("A.L", scale=(-1, 1, 1))])
        self.assertEqual(next(f.severity for f in result.findings if f.code == "NEGATIVE_LOCAL_SCALE"), "INFO")

    def test_relative_tolerance_uses_larger_part_diagonal(self):
        codes = self.codes([part("A.L"), part("A.R", -2.02)],
                           tolerance=0.001, relative_tolerance=0.01)
        self.assertNotIn("CENTER_MISMATCH", codes)

    def test_parent_is_context_not_error(self):
        result = inspect_parts([part("A.L", has_parent=True), part("A.R", -2)])
        self.assertEqual(result.checked_pairs, 1)
        self.assertEqual([(f.code, f.severity) for f in result.findings], [("PARENT_TRANSFORM", "INFO")])

    def test_invalid_settings_and_duplicate_names_rejected(self):
        for settings in [Settings(axis="Q"), Settings(tolerance=-1),
                         Settings(tolerance=math.nan), Settings(plane=math.inf),
                         Settings(relative_tolerance=-1)]:
            with self.assertRaises(ValueError):
                inspect_parts([], settings)
        with self.assertRaises(ValueError):
            inspect_parts([part("A.L"), part("A.L")])

    def test_nonfinite_and_inverted_bounds_do_not_pass(self):
        with self.assertRaises(ValueError):
            inspect_parts([Part("A.L", (math.nan, 0, 0), (1, 1, 1))])
        with self.assertRaises(ValueError):
            inspect_parts([Part("A.L", (2, 0, 0), (1, 1, 1))])

    def test_report_has_no_names_paths_or_stable_identifiers(self):
        secret = "private-project.L"
        result = inspect_parts([part(secret)])
        report = report_dict(result)
        encoded = json.dumps(report, allow_nan=False)
        self.assertNotIn(secret, encoded)
        self.assertNotIn("private-project.R", encoded)
        self.assertNotIn("path", encoded.lower())
        self.assertEqual(report["findings"][0]["objects"], ["part_001"])
        self.assertNotIn("name", encoded.lower())

    def test_shared_report_only_exports_normalized_differences(self):
        report = report_dict(inspect_parts([part("A.L"), part("A.R", -4)]))
        encoded = json.dumps(report)
        for key in ["bounds", "center", "dimensions", "tolerance", "plane", "scale"]:
            self.assertNotIn('"' + key + '"', encoded)
        finding = next(f for f in report["findings"] if f["code"] == "CENTER_MISMATCH")
        self.assertGreater(finding["normalized_difference"], 0)

    def test_zero_diagonal_report_does_not_export_distance(self):
        report = report_dict(inspect_parts([
            Part("Point.L", (3, 0, 0), (3, 0, 0)),
            Part("Point.R", (-4, 0, 0), (-4, 0, 0))]))
        finding = next(f for f in report["findings"] if f["code"] == "CENTER_MISMATCH")
        self.assertEqual(finding["normalized_difference"], 1)


if __name__ == "__main__":
    unittest.main()
