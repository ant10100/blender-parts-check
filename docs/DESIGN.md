# Design and review notes

Version 0.1.0 is deliberately small: explicit `.L`/`.R` naming and evaluated
world-space axis-aligned bounding boxes. It has no repair engine or reference
image pipeline. The public interface is a manual run, scoped selection, optional
privacy-reduced report, and explicit uninspected findings.

## Architecture

- `core.py`: immutable snapshots, settings validation, exact naming, bounds and
  scale checks, and an allowlisted report serializer. Standard library only.
- `adapter.py`: gathers targets and evaluated mesh vertices. It transforms every
  vertex by the evaluated world matrix, computes a tight world AABB, and frees
  the temporary mesh in `finally`. It does not use local origins as centers or
  transform the eight corners of a local AABB as an approximation.
- `ui.py`: WindowManager settings with `SKIP_SAVE`, transient local results, an
  explicit check operator, and an explicit new-file-only JSON export operator.
  No update handlers, timers, custom object properties, or network access.

The data path is Blender → snapshot → pure check → transient panel / allowlisted
JSON. No result field is written back to Blender objects. Settings affect only
the current session. A result is a last-run snapshot and can become stale.

## Interpretation choices

Missing names are warnings because scope, exclusions, intentional asymmetry and
Mirror can explain them. A Mirror modifier's presence is context, not proof that
it generates the desired partner. The narrow name rule avoids pretending to
understand duplicate numbering or naming conventions not explicitly supported.

Negative scales and parent transforms are information. Geometry comparison uses
current evaluated world coordinates; a locally unusual transform is not itself
a geometry mismatch. This does not simulate future parenting changes.

The pair tolerance uses `max(abs, rel * larger_part_diagonal)`. The center test
uses Euclidean distance; the dimension test uses the largest absolute per-axis
dimension difference. A mismatch's normalized difference divides by the larger
diagonal; for zero-diagonal pairs a nonzero difference is 1. Tolerance and raw
coordinates are not exported.

## Uninspected data

Non-mesh types, empty evaluated meshes, instance generators, particle systems,
Geometry Nodes, unavailable view-layer objects, and failed evaluation have
explicit uninspected findings. Geometry Nodes is conservatively skipped even
if all its geometry happens to be realized. Present-but-uninspected partners
suppress misleading missing-partner findings. No inspected pairs is visibly
different from a clean comparison of inspected pairs.

## Hard limits

Identical bounding centers/dimensions do not imply identical geometry. Internal
shape, silhouette, topology, interpenetration, materials and glow can differ
without changing the bounds. Current viewport evaluation is not render
evaluation. Instances and future scene edits are not covered.

The panel shows local object names in memory. JSON omits names and raw dimensions
but is only privacy-reduced: counts and normalized differences can still carry
project information. Output uses fresh sequential references, not hashes of
private names. It contains no link back to a local object. Export will not
overwrite an existing file, even if a file picker would allow it.

## Existing features and sources

The parent investigation identified Blender's built-in Mirror as geometry
generation and 3D Print Toolbox as printing-oriented mesh analysis. This project
therefore focuses on multi-part pre-integration checks rather than reimplementing
either workflow. No exhaustive novelty claim is made.

- [Mirror manual](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/mirror.html)
- [3D Print Toolbox](https://extensions.blender.org/add-ons/print3d-toolbox/)
- [Dependency graph API](https://docs.blender.org/api/current/bpy.types.Depsgraph.html)
- [Object API](https://docs.blender.org/api/current/bpy.types.Object.html)

The Mirror result is also tested directly in the installed Blender. No upstream
code or third-party add-on has been copied into the product. The GPLv3 text is
the unmodified standard license text; its standard public organizational
copyright/contact terms are not private user information.

## Verification

Pure tests exercise naming, scope-related missing logic, tolerances, exclusions,
transform context, validation, and report privacy. Separate headless Blender
tests build factory-startup synthetic meshes and exercise evaluated geometry,
parents, Mirror, scope, empty/unsupported objects, and scene fingerprints.
Registration/unregistration and explicit export are tested in that process.

Tests do not connect to a running Blender process, use private models, or install
the extension into the user's preferences. Native panel/file-picker appearance
has not been visually tested; registration and operator execution have been.
