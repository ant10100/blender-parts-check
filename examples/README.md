# Synthetic examples / 合成例

All examples use newly created cubes, not personal models or reference images.

Run from the source directory in a **new factory-startup background process**:

```text
blender --background --factory-startup --python-exit-code 1 --python examples/run_synthetic.py
```

The script refuses to run in an interactive Blender session or without the
factory-startup flag. It replaces only that process's factory scene. It prints a
privacy-reduced JSON report, does not save a `.blend`, and does not write output
files. `sample-report.json` is the same synthetic result.

このスクリプトは新しい独立したバックグラウンドプロセス専用です。工場出荷状態の
シーンを合成立方体に置換し、個人情報を抑えた JSON を標準出力へ表示します。
作業中の Blender に貼り付けないでください。blend ファイルや報告ファイルは保存しません。

| Synthetic pair | Setup | Expected finding |
| --- | --- | --- |
| Arm.L / Arm.R | centers ±2, same dimensions | no bounds mismatch |
| Leg.L / Leg.R | mirrored X, right Y offset +0.2 | CENTER_MISMATCH |
| Panel.L | absent Panel.R | MISSING_PARTNER warning |

The omitted absolute coordinates in the shared sample cannot be recovered by a
name-to-reference lookup. Counts and normalized differences remain visible.
This is privacy reduction, not a complete anonymity guarantee.
