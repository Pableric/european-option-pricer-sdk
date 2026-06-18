#!/usr/bin/env python3
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_SUFFIXES = {".s", ".S", ".o", ".pyc"}
FORBIDDEN_NAMES = {
    "private",
    "sobol_european_avx512.s",
    "sobol_european_direct_avx512.s",
    "sobol_gaussian_avx512.s",
    "generate_european_coeffs.py",
    "sde-error.txt",
    "sde-align-checker-out.txt",
}
FORBIDDEN_SUBSTRINGS = (
    "gaussian_linear_coeff_values",
    "gaussian_scheduled_coeff_values",
    "gaussian_tail_coeff_values",
    "gaussian_first_patch_values",
    "gaussian_range_schedule",
    "european_exp_table",
    "european_direct_center",
)


def main() -> int:
    bad = []
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        parts = set(rel.parts)
        if ".git" in parts or "build" in parts:
            continue
        if p.name in FORBIDDEN_NAMES or parts.intersection(FORBIDDEN_NAMES):
            bad.append(rel)
            continue
        if p.suffix in FORBIDDEN_SUFFIXES:
            bad.append(rel)
            continue
        if any(s in p.name for s in FORBIDDEN_SUBSTRINGS):
            bad.append(rel)

    if bad:
        print("Private/generated artifacts found:")
        for p in bad:
            print(f"  {p}")
        return 1
    print("check-private: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

