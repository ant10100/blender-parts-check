# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender snapshot adapter. Only temporary evaluated meshes are allocated."""
from dataclasses import replace
import math

from .core import Finding, Part, Settings, inspect_parts


def inspect_scene(context, *, scope="SELECTED", collection=None, settings=None):
    if context.mode != "OBJECT":
        raise ValueError("Switch to Object Mode before checking")
    settings = settings or Settings()
    inspect_parts([], settings)  # Validate before touching evaluated geometry.
    if scope == "SELECTED":
        targets = tuple(context.selected_objects)
    elif scope == "VIEW_LAYER":
        targets = tuple(context.view_layer.objects)
    elif scope == "COLLECTION" and collection is not None:
        targets = tuple(collection.all_objects)
    else:
        raise ValueError("Choose selected objects, the view layer, or a collection")
    depsgraph = context.evaluated_depsgraph_get()
    parts, findings, unchecked = [], [], set()
    excluded_count = 0
    for obj in sorted(targets, key=lambda o: o.name):
        if obj.name in settings.excluded:
            excluded_count += 1
            continue
        reason = None
        if obj.name not in context.view_layer.objects:
            reason = "UNCHECKED_VIEW_LAYER"
        elif obj.instance_type != "NONE" or obj.is_instancer:
            reason = "UNCHECKED_INSTANCE"
        elif obj.type != "MESH":
            reason = "UNCHECKED_TYPE"
        elif any(m.type == "NODES" for m in obj.modifiers):
            # to_mesh can omit generated instances. Never silently accept them.
            reason = "UNCHECKED_GEOMETRY_NODES"
        elif len(obj.particle_systems):
            reason = "UNCHECKED_INSTANCE"
        if reason:
            unchecked.add(obj.name)
            findings.append(Finding(reason, "WARNING", (obj.name,)))
            continue
        evaluated = None
        try:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            if mesh is None or not len(mesh.vertices):
                unchecked.add(obj.name)
                findings.append(Finding("UNCHECKED_EMPTY", "WARNING", (obj.name,)))
                continue
            minimum = [float("inf")] * 3
            maximum = [float("-inf")] * 3
            for vertex in mesh.vertices:
                point = evaluated.matrix_world @ vertex.co
                if not all(math.isfinite(value) for value in point):
                    raise ValueError("Nonfinite evaluated coordinates")
                for axis in range(3):
                    minimum[axis] = min(minimum[axis], point[axis])
                    maximum[axis] = max(maximum[axis], point[axis])
            parts.append(Part(obj.name, tuple(minimum), tuple(maximum), tuple(obj.scale),
                              evaluated.matrix_world.to_3x3().determinant() < 0,
                              obj.parent is not None, tuple(m.type for m in obj.modifiers)))
        except (RuntimeError, ValueError, OverflowError):
            unchecked.add(obj.name)
            findings.append(Finding("UNCHECKED_EVALUATION", "WARNING", (obj.name,)))
        finally:
            if evaluated is not None:
                evaluated.to_mesh_clear()
    # A present but uninspectable partner is not a missing partner.
    effective = replace(settings, excluded=settings.excluded | frozenset(unchecked))
    result = inspect_parts(parts, effective)
    return replace(result, findings=result.findings + tuple(findings),
                   excluded_parts=excluded_count, unchecked_parts=len(unchecked))
