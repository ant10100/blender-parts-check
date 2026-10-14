# Blender Parts Check

Read-only checks for explicitly named parts before integrating a Blender model.

[日本語](README.ja.md) · GPL-3.0-or-later · No external Python dependencies

An offset part, a wrong import scale, or an absent named partner is easy to overlook
when separate pieces are assembled. This small add-on compares **evaluated mesh
world-space bounding centers and dimensions**, and gives context about scale,
parents, and Mirror modifiers. It never repairs a scene automatically.

## What it checks

- Exact uppercase suffix pairs: `Arm.L` ↔ `Arm.R`. `Arm.L.001`, `_L`, lowercase
  suffixes, and words such as `LeftArm` are not inferred.
- A partner absent **from the chosen scope** is a review warning, never proof of
  a missing part. A Mirror modifier may already generate both sides; its presence
  is shown even if disabled. Inspect its axes and settings yourself.
- Reflect the world bounding center across world X, Y, or Z at a chosen offset,
  then compare Euclidean center distance and the largest dimension difference.
- Scale magnitude other than one is a warning. Negative local scale, reflected
  world transforms, and parent transforms are informational context.

There are no automatic Apply Transform, Mirror, Rename, Delete, selection, or
blend-file Save operations. Inspection allocates and clears only temporary
evaluated meshes. Run settings and result names are kept in memory, not saved in
the blend file. JSON export is a separate, explicit action and refuses to
overwrite an existing file.

## Install and remove

Tested on **Blender 5.0.1 / Windows**. The manifest requires Blender 5.0 or later;
other versions and operating systems have not been tested.

1. Download the **extension ZIP** (`blender_parts_check-0.1.0.zip`), not the source
   ZIP. Do not extract it.
2. In Blender: Edit → Preferences → Get Extensions → top-right menu → Install
   from Disk. Choose the ZIP and enable Blender Parts Check if needed.
3. Open the 3D Viewport sidebar (`N`) → **Parts Check**.

To remove it, find Blender Parts Check in Preferences → Add-ons / Get Extensions
and choose Disable, then Uninstall. It does not add object properties, handlers,
startup files, or scene data. Exported JSON files stay wherever you chose to save
them; remove those yourself if no longer needed.

## Use before integration

1. Use **Object Mode**. Choose Selected objects, Collection + children, or Active
   view layer. A collection object outside the active view layer is uninspected.
2. Set the plane normal and offset (e.g. X and 0 means the world YZ plane).
   The plane uses world axes, not an object's origin, local axis, or cursor.
3. Choose absolute tolerance in **Blender units** and relative tolerance as a
   fraction (`0.001` means `0.1%`). These are not display-unit labels.
4. Enter intentional exceptions under Exclude exact names, separated by `;`.
   Excluding either member suppresses symmetry checks for that pair. The
   nonexcluded member still receives its own scale/context checks. Names that
   contain `;` cannot be entered through this field; use Python `Settings`.
5. Click **Check Parts (read only)**. This is a snapshot: rerun after any scene,
   selection, scope, settings, frame, or modifier change.
6. Optionally export the last snapshot to a new `.json` filename. Review it before
   sharing. The local panel shows names; the report does not contain them.

For each pair, let `D` be the larger of the two world bounding-box diagonal
lengths. Allowed difference = `max(absolute tolerance, relative tolerance × D)`.
The center distance and maximum per-axis dimension difference are tested
separately against that distance. Shared differences are divided by `D`; for
zero-diagonal point-like pairs a nonzero difference is represented as 1. There
is no semantic rule that `.L` must be on the positive or negative side.

Example: two cubes of dimensions `(2, 2, 2)` centered at `(2, 0, 0)` and
`(-2, 0, 0)` pass the bounds comparison. Moving the second cube to `(-2, 0.2, 0)`
produces `CENTER_MISMATCH`. Its normalized difference is about `0.05773503`.
See [synthetic examples](examples/README.md).

## Read findings correctly

`WARNING` means review the measured difference or uninspected item; it does not
establish artistic intent. `INFO` describes a transform, modifier, or naming
limitation. Invalid inputs cancel the run with an error and clear the old result.
Zero checked pairs is explicitly shown, rather than presented as a passed scene.

Empty meshes, unsupported object types, collection/particle instancers, and
Geometry Nodes objects are **uninspected**. Geometry Nodes is conservatively
skipped because evaluated mesh conversion may omit instances, even when a
particular node tree only makes ordinary geometry. A present but uninspectable
partner is not reported as absent. Excluded objects are not evaluated.

## Limits

- **Same bounds can hide different shapes.** This is not a vertex, topology,
  silhouette, collision, intersection, watertightness, or mesh-equivalence test.
- It does not compare emission, materials, textures, lighting, UVs, or rendered
  appearance, and cannot detect left/right glow differences.
- It does not read reference images or promise faithful reconstruction.
- Evaluated geometry uses the current frame and viewport dependency graph.
  Render-only modifiers, different animation frames, simulation states, and
  generated instances can differ. Full scene evaluation may be expensive.
- It considers current world geometry, including parents and constraints. It
  does not predict what reparenting, applying a transform, or changing a
  constraint later would do. Different local origins/transforms can legitimately
  yield identical world bounds.
- This is a snapshot, not a continuously updating validator. A clean bounds
  comparison is not a guarantee that integration is correct.

## Reports and privacy

The privacy-reduced JSON uses run-local `part_001` references, problem codes,
severity, counts, and normalized differences. An allowlist omits object and
collection names, blend paths, usernames, timestamps, raw coordinates, dimensions,
plane offsets, and local scale values. There is no telemetry or network code.
It is **not a promise of complete anonymity**: counts, relative proportions and
problem patterns may still reveal information about a project. Screenshots of
the local panel and Blender's own console may contain private information.

## Development

```text
python -m unittest discover -s tests -v
blender --background --factory-startup --python-exit-code 1 --python tests/blender_integration.py
python tools/build_release.py
python tools/audit_public.py
```

Use a separate headless process. The integration tests replace its factory scene
with synthetic meshes; do not run them in your working Blender session. No
personal model or image is needed. Tests check scene fingerprints before and
after inspection and explicit export. The expected error message in the export
test verifies refusal to overwrite an existing report.

## Relationship to existing tools

Blender's [Mirror modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/mirror.html)
generates mirrored geometry. [3D Print Toolbox](https://extensions.blender.org/add-ons/print3d-toolbox/)
provides printing-oriented mesh analysis. Parts Check's narrow purpose is an
explicitly named, multi-part pre-integration bounds check. This is a scope
distinction, not a claim that no similar tool exists. See [design notes](docs/DESIGN.md).

## License

Original code and synthetic examples: GPL-3.0-or-later. See [LICENSE](LICENSE).
Blender is a separate prerequisite, not included in either ZIP.
