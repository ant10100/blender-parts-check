# Blender Parts Check

**Catch misplaced parts before you assemble the model.**

[English](README.md) | [日本語](README.ja.md)

Blender Parts Check is a small, read-only add-on for checking separately made
parts before integration. Pick your objects, choose a symmetry plane, and review
missing named partners or differences in their world-space bounds.

It helps answer “Did this part arrive at the wrong size or position?” It checks
bounding boxes, not whether the model's shape or appearance is correct.

[Install](#install) · [First check](#first-check) · [Synthetic example](#example) ·
[Settings](#settings) · [Limits](#limits) · [Privacy](#privacy) · [Contribute](#contribute)

| At a glance | Details |
| --- | --- |
| Tested environment | Blender **5.0.1**, Windows |
| Version requirement | Manifest requires Blender **5.0+**; other versions and OSes are untested |
| Location | 3D Viewport → `N` sidebar → **Parts Check** |
| Pair naming | Exact uppercase suffixes: `Arm.L` ↔ `Arm.R` |
| Dependencies | Blender; no additional Python packages or account needed |
| Language | English and Japanese documentation; panel labels are currently English |
| License | [GPL-3.0-or-later](LICENSE) |

## When this helps

- A named counterpart is absent from the objects you are about to combine.
- A separately imported part has a different position or bounding size.
- You want scale, parent, and Mirror context alongside a bounds comparison.

The add-on evaluates the **current viewport mesh in world coordinates**, including
parent transforms and constraints. Different origins or local transforms can
still produce matching world bounds. Warnings invite review; they do not decide
whether an intentional asymmetry is wrong.

<a id="install"></a>
## Install in three steps

1. Get **`blender_parts_check-0.1.0.zip`** from the project's release assets, or
   build it from a source checkout with `python tools/build_release.py` (output:
   `dist/`). Keep the extension ZIP compressed. GitHub's automatic **Source code**
   ZIP and `blender-parts-check-source-0.1.0.zip` are for source, not installation.
2. In Blender, open **Edit → Preferences → Get Extensions → top-right menu →
   Install from Disk**. Choose the extension ZIP and enable it if needed.
3. Return to the **3D Viewport**, press **`N`**, and open **Parts Check**.

No terminal is needed when using the ready-made extension ZIP. If the tab is
missing, check that the extension is enabled and the mouse is over the 3D Viewport
when pressing `N`.

**Remove:** disable Blender Parts Check in Preferences → Add-ons / Get Extensions,
then uninstall it. It adds no object properties, startup files, or scene data.
Any JSON you exported stays in your chosen location; delete it separately if
you no longer need it.

<a id="first-check"></a>
## Your first check

1. Switch to **Object Mode**. Select both members of a pair, such as `Arm.L` and
   `Arm.R` (Shift-click to select multiple objects).
2. Open **Parts Check**. Leave **Scope** at **Selected objects**, **Plane normal**
   at **X**, and **Plane offset** at **0** for symmetry about the world YZ plane.
3. Leave both tolerances at **0.001** for the small cube example below.
4. Click **Check Parts (read only)** and read the **Last run snapshot**.

`WARNING` means a difference or uninspected item needs your attention. `INFO`
provides transform, naming, or modifier context. With no compared pairs the panel
says **No symmetry pairs inspected**; that is not a passed scene. Invalid scope,
mode, or numeric settings cancel the run with an error and clear the old result.

The snapshot does not update automatically. **Rerun after changing objects,
selection, settings, frame, or modifiers**, and before exporting a report.

<a id="example"></a>
## Try it with two cubes

Use a new scratch scene and default cubes of dimensions `(2, 2, 2)` and scale
`(1, 1, 1)`. Rename them with `F2`; enter their Location values under the `N`
sidebar's **Item** tab. Return to **Parts Check** and select both cubes.

| Step | Synthetic setup | Expected result with X / offset 0 |
| --- | --- | --- |
| 1 | `Arm.L` at `(2, 0, 0)`; `Arm.R` at `(-2, 0, 0)` | 1 pair; no bounds mismatch |
| 2 | Change only `Arm.R` Location Y to `0.2` | `WARNING: CENTER_MISMATCH` |
| 3 | Select only `Arm.L`, keeping Selected objects scope | `WARNING: MISSING_PARTNER` |

In step 2, **Difference / diagonal** is approximately **`0.05773503`**. Step 3
means the partner is absent **from the chosen scope**, even though it still
exists elsewhere in the scene.

For a reproducible five-cube example, run this from the source root in a **new
background Blender process**, with `blender` available on your command path:

```text
blender --background --factory-startup --python-exit-code 1 --python examples/run_synthetic.py
```

It replaces that process's factory scene, prints JSON, and saves no blend or
report file. It refuses interactive execution or a missing factory-startup flag.
The [complete synthetic report](examples/sample-report.json) has 2 compared
pairs and 5 mesh parts. Its findings are:

```json
[
  {"code": "CENTER_MISMATCH", "severity": "WARNING", "objects": ["part_001", "part_002"], "normalized_difference": 0.05773503},
  {"code": "MISSING_PARTNER", "severity": "WARNING", "objects": ["part_003"]}
]
```

These are synthetic examples, not a report from a personal model. See
[example details](examples/README.md) for the setup.

<a id="settings"></a>
## Choose the right scope and tolerance

| Panel setting | What to choose |
| --- | --- |
| **Scope** | Selected objects, Collection + children, or Active view layer. Both sides must be in scope. A collection object outside the active view layer is uninspected. |
| **Plane normal / Plane offset** | X, Y, or Z world axis and coordinate. X / 0 is the YZ plane; Y / 3 reflects across world Y = 3. The cursor and local object axes are not used. |
| **Absolute tolerance** | Distance in Blender units, default `0.001`. Display units such as meters are not converted automatically. |
| **Relative tolerance** | Fraction of the larger part's bounding-box diagonal, default `0.001` = `0.1%`. |
| **Exclude exact names** | Semicolon-separated names, e.g. `Badge.L;Badge.R`, for intentional asymmetry. Excluding either side suppresses that pair's symmetry check. |

For a pair, let `D` be the **larger part's world bounding-box diagonal length**.
The allowed distance is `max(absolute tolerance, relative tolerance × D)`.
Reflected-center Euclidean distance and the largest per-axis dimension difference
are each tested against it. Reported differences are divided by `D`; for
zero-diagonal point-like pairs, a nonzero difference is represented as `1`.

Only exact uppercase **`.L` / `.R` endings** are recognized. `Arm.L.001`, `_L`,
lowercase suffixes, and `LeftArm` are not inferred. `.L` is not required to be on
the positive or negative side of the plane.

Exclusions skip evaluation of that object. The nonexcluded member still receives
its own scale/context checks. For names containing `;`, use Python `Settings`
instead of the panel's exclusion field.

## Understand the findings

| Finding | Meaning |
| --- | --- |
| `MISSING_PARTNER` | The exact partner is absent from scope. Check selection, exclusions, intent, and Mirror settings before adding anything. |
| `CENTER_MISMATCH` / `SIZE_MISMATCH` | Reflected world bounding centers / world bounding dimensions differ beyond tolerance. |
| `UNAPPLIED_SCALE` | Local scale magnitude differs from 1; review it before integration. |
| `NEGATIVE_LOCAL_SCALE` / `WORLD_REFLECTION` / `PARENT_TRANSFORM` | Informational context, not geometry errors. |
| `MIRROR_PRESENT` | A Mirror modifier exists, even if disabled. It may already generate both sides; inspect its axes and viewport settings. |
| `UNPAIRED_NAME` | No supported suffix; symmetry was not checked for this object. |
| `UNCHECKED_*` | Data could not be inspected. It is not a clean comparison. |

Empty meshes, non-mesh types, collection/particle instancers, Geometry Nodes,
unavailable view-layer objects, and failed or nonfinite evaluation are uninspected.
Geometry Nodes is conservatively skipped because mesh conversion can omit
instances, even when a particular node tree only makes realized geometry.
A present but uninspectable partner is not reported as missing.

<a id="limits"></a>
## Read-only by design, limited by bounds

Inspection does **not** Apply Transform, create Mirror modifiers, rename, delete,
change selection, or save blend files. It creates and frees only temporary
evaluated meshes. Settings and result names stay in memory, not in the blend.
It registers no scene update handlers or timers. You decide what to change.

**A clean bounds comparison does not prove a correct model.**

- Different shapes can have identical centers and dimensions. Vertices, topology,
  silhouettes, collisions, intersections, watertightness, and shape equivalence
  are not checked.
- Emission, materials, textures, lighting, UVs, and rendered appearance are not
  compared. Left/right glow differences are outside the tool's scope.
- Reference images are not recognized and faithful reconstruction is not assessed.
- Results use the current frame and viewport dependency graph. Render-only
  modifiers, simulations, other animation frames, or generated instances may
  differ. Large scenes can take time to evaluate.
- The tool measures current world geometry. It does not predict how later
  reparenting, Apply Transform, or constraint changes will affect the model.

Blender's [Mirror modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/mirror.html)
generates mirrored geometry; [3D Print Toolbox](https://extensions.blender.org/add-ons/print3d-toolbox/)
analyzes meshes for printing. Parts Check focuses on named parts before
integration. This is not a claim that no similar tool exists.

<a id="privacy"></a>
## Optional JSON and privacy

After checking, **Export last snapshot JSON** explicitly writes a **new** `.json`
file. Existing files are never overwritten. Cancel the file picker to write
nothing. Review the report before sharing.

The privacy-reduced report contains run-local references such as `part_001`,
codes, severity, counts, and normalized differences. It omits object/collection
names, blend paths, usernames, timestamps, raw coordinates/dimensions, plane
offsets, and local scale values. There is no network or telemetry code.

This is **not complete anonymity**: counts, ratios, and problem patterns can
still reveal project information. The local panel shows object names, and
screenshots or Blender console output can contain private information.

<a id="contribute"></a>
## Contribute, translate, or report a problem

Small reproducible reports, clearer wording, translations, and focused code
changes are welcome. Use this repository's **Issues** for bugs and **Pull
requests** for proposed changes; include:

- Blender version and operating system;
- selected scope, plane, tolerances, and exact synthetic `.L` / `.R` names;
- reproduction steps, expected behavior, and actual findings.

Build a minimal synthetic example rather than uploading a personal blend file.
Remove private names, paths, screenshots, and credentials from public reports.
Keep English and Japanese instructions consistent, including supported versions
and limitations; add a reciprocal language link for any new translation.

For code changes, run from the source root (`blender` must be on the command path;
Python 3.13.11 was used for the standalone suite):

```text
python -m unittest discover -s tests -v
blender --background --factory-startup --python-exit-code 1 --python tests/blender_integration.py
python tools/build_release.py
python tools/audit_public.py
```

Run integration tests only in a separate factory-startup background process.
They replace its scene with synthetic objects and reject unsafe launch conditions.
The expected export-test error verifies refusal to overwrite an existing JSON.
The recorded baseline is **15 Python tests and 20 Blender integration tests**.
The source distribution includes `docs/VALIDATION.md`; also see the
[design notes](docs/DESIGN.md).
Native panel/file-picker appearance and other Blender/OS combinations are untested.

## License

Original code and synthetic examples are **GPL-3.0-or-later**; see [LICENSE](LICENSE).
Blender is a separate prerequisite and is not bundled. No endorsement by Blender
or by other projects is implied.
