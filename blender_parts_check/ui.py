# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit run/export UI. Settings live in WindowManager with SKIP_SAVE."""
import json

import bpy
from bpy.props import EnumProperty, FloatProperty, PointerProperty, StringProperty

from .adapter import inspect_scene
from .core import Settings, report_dict

_last_result = None

MESSAGES = {
    "MISSING_PARTNER": "Partner absent from scope; review intent and Mirror stack",
    "CENTER_MISMATCH": "Reflected world bounding centers differ",
    "SIZE_MISMATCH": "World bounding dimensions differ",
    "NEGATIVE_LOCAL_SCALE": "Negative local scale; may be intentional",
    "UNAPPLIED_SCALE": "Local scale magnitude differs from 1; review before integration",
    "WORLD_REFLECTION": "World transform has a reflection; may be intentional",
    "PARENT_TRANSFORM": "Parent included in evaluated world geometry",
    "MIRROR_PRESENT": "Mirror in stack; inspect enabled axes and viewport settings",
    "UNPAIRED_NAME": "No exact .L/.R suffix; symmetry not checked",
    "UNCHECKED_VIEW_LAYER": "Not in active view layer; uninspected",
    "UNCHECKED_INSTANCE": "Instance generator unsupported; uninspected",
    "UNCHECKED_TYPE": "Only mesh objects supported; uninspected",
    "UNCHECKED_GEOMETRY_NODES": "Geometry Nodes may contain instances; uninspected",
    "UNCHECKED_EMPTY": "No evaluated vertices; uninspected",
    "UNCHECKED_EVALUATION": "Evaluation failed; uninspected",
}


class PARTSCHECK_Settings(bpy.types.PropertyGroup):
    scope: EnumProperty(name="Scope", items=[("SELECTED", "Selected objects", "Only selected objects"),
        ("COLLECTION", "Collection + children", "Collection objects and all child collections"),
        ("VIEW_LAYER", "Active view layer", "All objects in the active view layer")], options={"SKIP_SAVE"})
    collection: PointerProperty(name="Collection", type=bpy.types.Collection, options={"SKIP_SAVE"})
    axis: EnumProperty(name="Plane normal", items=[(a, a, a + " world axis") for a in "XYZ"], options={"SKIP_SAVE"})
    plane: FloatProperty(name="Plane offset", default=0, description="World coordinate along the plane normal, in Blender units", options={"SKIP_SAVE"})
    absolute: FloatProperty(name="Absolute tolerance", default=0.001, min=0, precision=6, options={"SKIP_SAVE"})
    relative: FloatProperty(name="Relative tolerance", default=0.001, min=0, precision=6,
        description="Fraction of the larger part bounding-box diagonal (0.001 = 0.1%)", options={"SKIP_SAVE"})
    exclusions: StringProperty(name="Exclude exact names", default="",
        description="Semicolon-separated exact object names. Excluding either side suppresses pair comparison", options={"SKIP_SAVE"})


class PARTSCHECK_OT_Run(bpy.types.Operator):
    bl_idname = "parts_check.run"
    bl_label = "Check Parts (read only)"
    bl_description = "Inspect geometry without changing, selecting or saving scene objects"

    def execute(self, context):
        global _last_result
        _last_result = None
        s = context.window_manager.parts_check
        settings = Settings(axis=s.axis, plane=s.plane, tolerance=s.absolute,
                            relative_tolerance=s.relative,
                            excluded=frozenset(n.strip() for n in s.exclusions.split(";") if n.strip()))
        try:
            _last_result = inspect_scene(context, scope=s.scope, collection=s.collection, settings=settings)
        except (ValueError, RuntimeError, OverflowError):
            self.report({"ERROR"}, "Check could not run. Use Object Mode, a valid scope and finite settings.")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Checked {_last_result.checked_pairs} pairs; {_last_result.unchecked_parts} uninspected objects")
        return {"FINISHED"}


class PARTSCHECK_OT_Export(bpy.types.Operator):
    bl_idname = "parts_check.export"
    bl_label = "Export last snapshot JSON"
    bl_description = "Explicitly write a privacy-reduced report; names, paths and raw dimensions are omitted"

    filepath: StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})
    filter_glob: StringProperty(default="*.json", options={"HIDDEN", "SKIP_SAVE"})
    check_existing: bpy.props.BoolProperty(default=True, options={"HIDDEN", "SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        return _last_result is not None

    def invoke(self, context, event):
        self.filepath = "parts-check-report.json"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            # Never append a suffix to a potentially sensitive existing filename.
            if not self.filepath.lower().endswith(".json"):
                self.report({"ERROR"}, "Choose a .json report filename")
                return {"CANCELLED"}
            with open(self.filepath, "x", encoding="utf-8", newline="\n") as target:
                json.dump(report_dict(_last_result), target, indent=2, allow_nan=False)
                target.write("\n")
        except (OSError, ValueError):
            self.report({"ERROR"}, "Report could not be written")
            return {"CANCELLED"}
        self.report({"INFO"}, "Privacy-reduced snapshot exported; review before sharing")
        return {"FINISHED"}


class PARTSCHECK_PT_Panel(bpy.types.Panel):
    bl_label = "Blender Parts Check"
    bl_idname = "PARTSCHECK_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Parts Check"

    def draw(self, context):
        layout = self.layout
        s = context.window_manager.parts_check
        layout.label(text="World bounds only; read only", icon="INFO")
        layout.prop(s, "scope")
        if s.scope == "COLLECTION":
            layout.prop(s, "collection")
        layout.prop(s, "axis")
        layout.prop(s, "plane")
        layout.prop(s, "absolute")
        layout.prop(s, "relative")
        layout.prop(s, "exclusions")
        layout.operator("parts_check.run")
        if _last_result is None:
            return
        result = _last_result
        box = layout.box()
        box.label(text="Last run snapshot; rerun after edits")
        box.label(text=f"Pairs: {result.checked_pairs} | Mesh parts: {result.included_parts}")
        box.label(text=f"Excluded: {result.excluded_parts} | Uninspected: {result.unchecked_parts}")
        if not result.checked_pairs:
            box.label(text="No symmetry pairs inspected", icon="ERROR")
        elif not result.findings:
            box.label(text="No issues in the bounds checks", icon="CHECKMARK")
        for f in result.findings:
            row = box.box()
            row.label(text=f.severity + ": " + f.code, icon="ERROR" if f.severity == "WARNING" else "INFO")
            row.label(text=", ".join(f.objects))
            row.label(text=MESSAGES[f.code])
            if f.code == "MISSING_PARTNER" and f.metrics.get("mirror_present"):
                row.label(text="Mirror modifier present; it may generate both sides")
            if "normalized_difference" in f.metrics:
                row.label(text=f"Difference / diagonal: {f.metrics['normalized_difference']:.6g}")
        layout.operator("parts_check.export")
        layout.label(text="JSON omits names, paths and raw dimensions")


CLASSES = (PARTSCHECK_Settings, PARTSCHECK_OT_Run, PARTSCHECK_OT_Export, PARTSCHECK_PT_Panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.parts_check = PointerProperty(type=PARTSCHECK_Settings, options={"SKIP_SAVE"})


def unregister():
    global _last_result
    _last_result = None
    del bpy.types.WindowManager.parts_check
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
