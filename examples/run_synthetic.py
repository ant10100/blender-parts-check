# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic demonstration; never run inside an interactive Blender session."""
import json
from pathlib import Path
import sys

import bpy

if not bpy.app.background or "--factory-startup" not in sys.argv:
    raise SystemExit("Use a new --background --factory-startup Blender process")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blender_parts_check.adapter import inspect_scene
from blender_parts_check.core import report_dict

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

for name, x, y, z in [("Arm.L", 2, 0, 0), ("Arm.R", -2, 0, 0),
                       ("Leg.L", 2, 0, -4), ("Leg.R", -2, 0.2, -4),
                       ("Panel.L", 2, 0, 4)]:
    bpy.ops.mesh.primitive_cube_add(size=2, location=(x, y, z))
    bpy.context.object.name = name

bpy.context.view_layer.update()
print(json.dumps(report_dict(inspect_scene(bpy.context, scope="VIEW_LAYER")), indent=2, allow_nan=False))
