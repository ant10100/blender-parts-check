# Validation record — candidate 0.1.0

Executed on 2026-10-14 with CPython 3.13.11 and Blender 5.0.1 on Windows.
Blender executable build hash: `a3db93c5b259`. No new software was installed.

| Check | Result |
| --- | --- |
| Pure Python unit suite | 15 tests passed |
| Factory-startup headless Blender suite | 20 tests passed |
| Synthetic demonstration | 2 checked pairs, 1 center warning, 1 absent-partner warning |
| Inspector and explicit export scene fingerprints | unchanged |
| Existing JSON overwrite | refused, contents unchanged |

The Blender suite covers normal pairs, absent partners, position and size
differences, evaluated Mirror geometry, Mirror presence context, parent scaling,
different origins/local representations with identical world bounds, exclusions,
selected and nested collection scopes, Y/Z offset planes, negative scale,
uninspectable empty meshes/instances/Geometry Nodes, and present-but-uninspectable
partners and nonfinite evaluated vertices. It also demonstrates the documented
same-bounds/different-shape limit.

`test_operator_and_export_do_not_mutate_scene` intentionally calls export a
second time with the same filename. The resulting `Report could not be written`
message is expected; the test asserts rejection and unchanged original bytes.

Commands, run from the source root:

```text
python -m unittest discover -s tests -v
blender --background --factory-startup --python-exit-code 1 --python tests/blender_integration.py
blender --background --factory-startup --python-exit-code 1 --python examples/run_synthetic.py
```

All synthetic scenes exist only in independent background processes. No running
Blender UI, existing model, personal image, working scene, or user preferences are
used by these tests. The test report file is created under `.test-output` and
removed. No blend files are saved. Public archives exclude temporary outputs,
bytecode, local console traces and Git metadata.

The native panel and file picker have not had visual UI testing. Registration,
unregistration and the real Blender operators have been exercised headlessly.
Other Blender versions and operating systems are untested. Independent candidate
review is still required before publication; these local tests are not a
substitute for that review.
