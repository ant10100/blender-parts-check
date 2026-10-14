# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure Python checks. No Blender, filesystem, telemetry, or scene mutations."""
from dataclasses import dataclass, field
import math


@dataclass(frozen=True)
class Part:
    name: str
    minimum: tuple
    maximum: tuple
    scale: tuple = (1.0, 1.0, 1.0)
    world_mirrored: bool = False
    has_parent: bool = False
    modifiers: tuple = ()


@dataclass(frozen=True)
class Settings:
    axis: str = "X"
    plane: float = 0.0
    tolerance: float = 0.001
    relative_tolerance: float = 0.001
    excluded: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    objects: tuple
    metrics: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Result:
    findings: tuple
    checked_pairs: int
    included_parts: int
    excluded_parts: int
    unpaired_parts: int
    unchecked_parts: int = 0


def opposite_name(name):
    """Only exact uppercase .L/.R suffixes; never infer Blender duplicate names."""
    if name.endswith(".L"):
        return name[:-2] + ".R"
    if name.endswith(".R"):
        return name[:-2] + ".L"
    return None


def inspect_parts(parts, settings=None):
    settings = settings or Settings()
    if settings.axis not in {"X", "Y", "Z"}:
        raise ValueError("Axis must be X, Y or Z")
    for value in (settings.plane, settings.tolerance, settings.relative_tolerance):
        if not math.isfinite(value):
            raise ValueError("Settings must be finite")
    if settings.tolerance < 0 or settings.relative_tolerance < 0:
        raise ValueError("Tolerances must be nonnegative")
    parts = tuple(parts)
    by_name = {p.name: p for p in parts}
    if len(by_name) != len(parts):
        raise ValueError("Part names must be unique")
    for p in parts:
        if any(len(v) != 3 for v in (p.minimum, p.maximum, p.scale)):
            raise ValueError("Expected three coordinates")
        if not all(math.isfinite(v) for vector in (p.minimum, p.maximum, p.scale) for v in vector):
            raise ValueError("Part values must be finite")
        if any(lo > hi for lo, hi in zip(p.minimum, p.maximum)):
            raise ValueError("Invalid bounds")
    included = {n: p for n, p in by_name.items() if n not in settings.excluded}
    findings, seen = [], set()
    checked_pairs = unpaired_parts = 0
    axis = "XYZ".index(settings.axis)
    for name in sorted(included):
        p = included[name]
        if any(s < 0 for s in p.scale):
            findings.append(Finding("NEGATIVE_LOCAL_SCALE", "INFO", (name,)))
        if any(abs(abs(s) - 1) > 1e-6 for s in p.scale):
            findings.append(Finding("UNAPPLIED_SCALE", "WARNING", (name,)))
        if p.world_mirrored:
            findings.append(Finding("WORLD_REFLECTION", "INFO", (name,)))
        if p.has_parent:
            findings.append(Finding("PARENT_TRANSFORM", "INFO", (name,)))
        if "MIRROR" in p.modifiers:
            findings.append(Finding("MIRROR_PRESENT", "INFO", (name,)))
        other_name = opposite_name(name)
        if other_name is None:
            unpaired_parts += 1
            findings.append(Finding("UNPAIRED_NAME", "INFO", (name,)))
            continue
        if other_name in settings.excluded:
            continue
        if other_name not in included:
            findings.append(Finding("MISSING_PARTNER", "WARNING", (name,),
                                    {"mirror_present": "MIRROR" in p.modifiers}))
            continue
        pair = tuple(sorted((name, other_name)))
        if pair in seen:
            continue
        seen.add(pair)
        q = included[other_name]
        pd = tuple(hi - lo for lo, hi in zip(p.minimum, p.maximum))
        qd = tuple(hi - lo for lo, hi in zip(q.minimum, q.maximum))
        pc = tuple(lo / 2 + hi / 2 for lo, hi in zip(p.minimum, p.maximum))
        qc = tuple(lo / 2 + hi / 2 for lo, hi in zip(q.minimum, q.maximum))
        reflected = list(pc)
        reflected[axis] = 2 * settings.plane - reflected[axis]
        diagonal = max(math.hypot(*pd), math.hypot(*qd))
        allowed = max(settings.tolerance, settings.relative_tolerance * diagonal)
        center_delta = math.dist(reflected, qc)
        size_delta = max(abs(a - b) for a, b in zip(pd, qd))
        if not all(math.isfinite(v) for v in (diagonal, allowed, center_delta, size_delta)):
            raise ValueError("Geometry exceeds numeric range")
        checked_pairs += 1
        # Normalize by the larger part diagonal, not by a user-selected tolerance.
        # Point-like bounds have no length for normalization; expose only 0/1.
        denominator = diagonal or max(center_delta, size_delta, 1e-300)
        if center_delta > allowed:
            findings.append(Finding("CENTER_MISMATCH", "WARNING", pair,
                                    {"normalized_difference": center_delta / denominator}))
        if size_delta > allowed:
            findings.append(Finding("SIZE_MISMATCH", "WARNING", pair,
                                    {"normalized_difference": size_delta / denominator}))
    return Result(tuple(findings), checked_pairs, len(included),
                  len(parts) - len(included), unpaired_parts)


def report_dict(result):
    """Privacy-reduced allowlist report; never serialize arbitrary objects/metrics."""
    identifiers = {}
    output = []
    for finding in result.findings:
        refs = []
        for name in finding.objects:
            if name not in identifiers:
                identifiers[name] = f"part_{len(identifiers) + 1:03d}"
            refs.append(identifiers[name])
        row = {"code": finding.code, "severity": finding.severity, "objects": refs}
        value = finding.metrics.get("normalized_difference")
        if value is not None and math.isfinite(value):
            row["normalized_difference"] = round(value, 8)
        output.append(row)
    return {"schema_version": 1, "tool_version": "0.1.0",
            "privacy": "reduced", "checked_pairs": result.checked_pairs,
            "included_parts": result.included_parts, "excluded_parts": result.excluded_parts,
            "unpaired_parts": result.unpaired_parts, "unchecked_parts": result.unchecked_parts,
            "findings": output}
