"""Synthetic scenes only. Run in a separate --background --factory-startup process."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import blender_parts_check as addon
from blender_parts_check.adapter import inspect_scene
from blender_parts_check.core import Settings, report_dict


def cube(name, x=2, y=0, z=0):
    mesh = bpy.data.meshes.new("SyntheticMesh")
    mesh.from_pydata([(a, b, c) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)], [],
                     [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
                      (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (x, y, z)
    return obj


def fingerprint():
    """Scene content and selection, including mesh/material/modifier/parent state."""
    objects = []
    for o in bpy.data.objects:
        objects.append((o.name, o.type, tuple(tuple(r) for r in o.matrix_world),
                        tuple(tuple(r) for r in o.matrix_parent_inverse),
                        o.parent.name if o.parent else None, o.select_get(), o.hide_get(),
                        o.hide_render, tuple((m.name, m.type, m.show_viewport) for m in o.modifiers),
                        tuple(m.name if m else None for m in o.data.materials) if o.type == "MESH" else (),
                        tuple(tuple(v.co) for v in o.data.vertices) if o.type == "MESH" else ()))
    state = (objects, bpy.context.scene.frame_current, bpy.context.mode,
             bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
             bpy.data.filepath, bpy.data.is_dirty,
             tuple((c.name, tuple(o.name for o in c.objects)) for c in bpy.data.collections),
             tuple(bpy.data.meshes.keys()), tuple(bpy.data.materials.keys()))
    return hashlib.sha256(repr(state).encode()).hexdigest()


class BlenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        addon.register()

    @classmethod
    def tearDownClass(cls):
        addon.unregister()

    def setUp(self):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for collection in list(bpy.data.collections):
            bpy.data.collections.remove(collection)

    def run_check(self, **kw):
        bpy.context.view_layer.update()
        before = fingerprint()
        result = inspect_scene(bpy.context, scope="VIEW_LAYER", **kw)
        self.assertEqual(fingerprint(), before, "Checker changed the scene")
        return result

    def codes(self, result):
        return [f.code for f in result.findings]

    def test_normal_pair(self):
        cube("Arm.L")
        cube("Arm.R", -2)
        result = self.run_check()
        self.assertEqual(result.checked_pairs, 1)
        self.assertEqual(result.findings, ())

    def test_missing_partner(self):
        cube("Arm.L")
        result = self.run_check()
        self.assertEqual([(f.code, f.severity) for f in result.findings], [("MISSING_PARTNER", "WARNING")])

    def test_misaligned_pair(self):
        cube("Arm.L")
        cube("Arm.R", -2, 0.2)
        self.assertIn("CENTER_MISMATCH", self.codes(self.run_check()))

    def test_size_mismatch(self):
        cube("Arm.L")
        cube("Arm.R", -2).scale.y = 1.2
        self.assertIn("SIZE_MISMATCH", self.codes(self.run_check()))

    def test_parent_and_one_applied_mesh_same_world_bounds(self):
        left, right = cube("Arm.L"), cube("Arm.R", -2)
        parent = bpy.data.objects.new("SyntheticParent", None)
        bpy.context.scene.collection.objects.link(parent)
        parent.scale = (2, 3, 4)
        left.parent = parent
        left.location = (1, 0, 0)
        left.scale = (0.5, 1 / 3, 0.25)
        # A different local representation with the same world-space geometry.
        right.data.transform(Matrix.Scale(2, 4))
        right.scale = (0.5, 0.5, 0.5)
        result = self.run_check(settings=Settings(excluded=frozenset({parent.name})))
        self.assertEqual(result.checked_pairs, 1)
        self.assertNotIn("CENTER_MISMATCH", self.codes(result))
        self.assertNotIn("SIZE_MISMATCH", self.codes(result))
        self.assertIn("PARENT_TRANSFORM", self.codes(result))

    def test_excluding_either_member(self):
        cube("Arm.L")
        cube("Arm.R", -6)
        result = self.run_check(settings=Settings(excluded=frozenset({"Arm.R"})))
        self.assertEqual(result.checked_pairs, 0)
        self.assertNotIn("CENTER_MISMATCH", self.codes(result))

    def test_mirror_evaluated_geometry_and_warning_context(self):
        left = cube("Arm.L", 0)
        left.data.transform(Matrix.Translation((2, 0, 0)))
        left.modifiers.new("SyntheticMirror", "MIRROR")
        right = cube("Arm.R", 0)
        # Two cubes at +/-2 in one base mesh: same evaluated bounds as Mirror.
        for v in right.data.vertices:
            v.co.x *= 3
        result = self.run_check()
        self.assertNotIn("SIZE_MISMATCH", self.codes(result))
        self.assertNotIn("CENTER_MISMATCH", self.codes(result))
        bpy.data.objects.remove(right, do_unlink=True)
        result = self.run_check()
        missing = next(f for f in result.findings if f.code == "MISSING_PARTNER")
        self.assertTrue(missing.metrics["mirror_present"])
        self.assertEqual(missing.severity, "WARNING")

    def test_offset_on_y_axis(self):
        cube("Arm.L", 0, 5)
        cube("Arm.R", 0, 1)
        result = self.run_check(settings=Settings(axis="Y", plane=3))
        self.assertNotIn("CENTER_MISMATCH", self.codes(result))

    def test_offset_on_z_axis(self):
        cube("Arm.L", 0, 0, 7)
        cube("Arm.R", 0, 0, 3)
        result = self.run_check(settings=Settings(axis="Z", plane=5))
        self.assertNotIn("CENTER_MISMATCH", self.codes(result))

    def test_different_origins_same_world_geometry(self):
        left = cube("Arm.L")
        cube("Arm.R", -2)
        left.data.transform(Matrix.Translation((5, 0, 0)))
        left.location.x -= 5
        result = self.run_check()
        self.assertEqual(result.checked_pairs, 1)
        self.assertNotIn("CENTER_MISMATCH", self.codes(result))
        self.assertNotIn("SIZE_MISMATCH", self.codes(result))

    def test_geometry_nodes_is_unchecked(self):
        cube("Arm.L").modifiers.new("SyntheticNodes", "NODES")
        result = self.run_check()
        self.assertEqual(result.unchecked_parts, 1)
        self.assertIn("UNCHECKED_GEOMETRY_NODES", self.codes(result))

    def test_nonfinite_vertex_is_unchecked(self):
        left = cube("Arm.L")
        left.data.vertices[0].co.x = float("nan")
        cube("Arm.R", -2)
        result = self.run_check()
        self.assertEqual(result.checked_pairs, 0)
        self.assertIn("UNCHECKED_EVALUATION", self.codes(result))

    def test_same_bounds_different_shape_is_documented_limit(self):
        cube("Arm.L")
        right = cube("Arm.R", -2)
        right.data.vertices[0].co = (-0.1, -0.1, -0.1)
        # Other vertices preserve every min/max, while this shape is different.
        result = self.run_check()
        self.assertEqual(result.checked_pairs, 1)
        self.assertNotIn("SIZE_MISMATCH", self.codes(result))
        self.assertNotIn("CENTER_MISMATCH", self.codes(result))

    def test_selection_scope_does_not_search_other_objects(self):
        left, right = cube("Arm.L"), cube("Arm.R", -2)
        left.select_set(True)
        right.select_set(False)
        bpy.context.view_layer.update()
        result = inspect_scene(bpy.context)
        self.assertIn("MISSING_PARTNER", self.codes(result))

    def test_collection_scope_with_children(self):
        group = bpy.data.collections.new("SyntheticGroup")
        child = bpy.data.collections.new("SyntheticChild")
        bpy.context.scene.collection.children.link(group)
        group.children.link(child)
        for obj in (cube("Arm.L"), cube("Arm.R", -2)):
            child.objects.link(obj)
            bpy.context.scene.collection.objects.unlink(obj)
        cube("Other.L", 10)
        bpy.context.view_layer.update()
        result = inspect_scene(bpy.context, scope="COLLECTION", collection=group)
        self.assertEqual(result.included_parts, 2)
        self.assertEqual(result.checked_pairs, 1)

    def test_empty_mesh_is_unchecked(self):
        empty = bpy.data.objects.new("Empty.L", bpy.data.meshes.new("SyntheticEmpty"))
        bpy.context.scene.collection.objects.link(empty)
        result = self.run_check()
        self.assertEqual(result.unchecked_parts, 1)
        self.assertIn("UNCHECKED_EMPTY", self.codes(result))

    def test_collection_instance_is_unchecked(self):
        group = bpy.data.collections.new("SyntheticInstanceSource")
        obj = bpy.data.objects.new("Instance.L", None)
        bpy.context.scene.collection.objects.link(obj)
        obj.instance_type = "COLLECTION"
        obj.instance_collection = group
        result = self.run_check()
        self.assertEqual(result.unchecked_parts, 1)
        self.assertIn("UNCHECKED_INSTANCE", self.codes(result))

    def test_negative_scale_is_information(self):
        cube("Arm.L").scale.x = -1
        cube("Arm.R", -2)
        result = self.run_check()
        self.assertNotIn("CENTER_MISMATCH", self.codes(result))
        self.assertEqual(next(f.severity for f in result.findings if f.code == "NEGATIVE_LOCAL_SCALE"), "INFO")

    def test_operator_and_export_do_not_mutate_scene(self):
        left = cube("SyntheticSecret.L")
        left.select_set(True)
        bpy.context.view_layer.objects.active = left
        bpy.context.view_layer.update()
        before = fingerprint()
        self.assertEqual(bpy.ops.parts_check.run(), {"FINISHED"})
        self.assertEqual(fingerprint(), before)
        directory = Path(__file__).resolve().parents[1] / ".test-output"
        directory.mkdir(exist_ok=True)
        target = directory / "report.json"
        try:
            self.assertEqual(bpy.ops.parts_check.export(filepath=str(target)), {"FINISHED"})
            report = json.loads(target.read_text(encoding="utf-8"))
            self.assertNotIn(left.name, target.read_text(encoding="utf-8"))
            self.assertEqual(report["privacy"], "reduced")
            original = target.read_bytes()
            with self.assertRaises(RuntimeError):
                bpy.ops.parts_check.export(filepath=str(target))
            self.assertEqual(target.read_bytes(), original)
        finally:
            target.unlink(missing_ok=True)
        self.assertEqual(fingerprint(), before)

    def test_unchecked_partner_does_not_claim_missing(self):
        cube("Arm.L")
        mesh = bpy.data.meshes.new("SyntheticEmpty")
        right = bpy.data.objects.new("Arm.R", mesh)
        bpy.context.scene.collection.objects.link(right)
        result = self.run_check()
        self.assertEqual(result.checked_pairs, 0)
        self.assertNotIn("MISSING_PARTNER", self.codes(result))
        self.assertIn("UNCHECKED_EMPTY", self.codes(result))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BlenderTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
