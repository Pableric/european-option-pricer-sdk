#!/usr/bin/env python3
import argparse
import csv
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCH_DIR = ROOT / "benchmarks" / "intel-mkl"
BUILD_DIR = BENCH_DIR / "build"
BIN = BUILD_DIR / "bench_european_mkl"

SUITES = {
    "quick": [1, 16, 128],
    "comprehensive": [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 1221, 2048, 4096, 8192],
}


def run(cmd, cwd=ROOT):
    p = subprocess.run([str(x) for x in cmd], cwd=cwd, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        print(p.stdout, end="")
        raise SystemExit(p.returncode)
    return p.stdout


def parse_result(line):
    data = {}
    for key, value in re.findall(r"(\w+)=([^ ]+)", line):
        data[key] = value
    return data


def as_float(row, key):
    try:
        return float(row[key])
    except (KeyError, ValueError):
        return None


def fmt_float(value, width=12, precision=6):
    if value is None:
        return "NA".rjust(width)
    return f"{value:.{precision}f}".rjust(width)


def fmt_ratio(value, width=10):
    if value is None:
        return "NA".rjust(width)
    return f"{value:.2f}x".rjust(width)


def fmt_text(value, width):
    return str(value).rjust(width)


def fmt_price(value, width=14):
    if value in (None, "NA"):
        return "NA".rjust(width)
    try:
        return f"{float(value):.8g}".rjust(width)
    except ValueError:
        return str(value).rjust(width)


def print_result_table(rows):
    if not rows:
        return

    print("\nDETAILED RESULTS")
    header = (
        f"{'blocks':>8} {'type':>4} {'mode':>24} {'workload':>14} "
        f"{'samples':>10} {'setup ms':>10} {'median ms':>11} "
        f"{'ns/value':>12} {'Gvalues/s':>12} {'price':>14} {'abs_err':>12}"
    )
    print(header)
    print("-" * len(header))
    for row in sorted(rows, key=lambda r: (int(r["blocks"]), r["type"], r["mode"])):
        ns = as_float(row, "ns_per_value")
        vps = as_float(row, "values_per_sec")
        gvps = vps / 1.0e9 if vps is not None else None
        setup = as_float(row, "setup_seconds")
        median = as_float(row, "median_seconds")
        err = as_float(row, "abs_err")
        print(
            f"{fmt_text(row.get('blocks', 'NA'), 8)} "
            f"{fmt_text(row.get('type', 'NA'), 4)} "
            f"{row.get('mode', 'NA'):>24} "
            f"{row.get('workload', 'unknown'):>14} "
            f"{fmt_text(row.get('samples', 'NA'), 10)} "
            f"{fmt_float(setup * 1.0e3 if setup is not None else None, width=10, precision=3)} "
            f"{fmt_float(median * 1.0e3 if median is not None else None, width=11, precision=3)} "
            f"{fmt_float(ns)} "
            f"{fmt_float(gvps)} "
            f"{fmt_price(row.get('price'))} "
            f"{fmt_float(err, precision=6)}"
        )


def print_summary(rows):
    if not rows:
        return

    print("\nCOMPARISON")
    by_case = {}
    for row in rows:
        key = (row.get("blocks"), row.get("type"))
        by_case.setdefault(key, {})[row.get("mode")] = row

    header = (
        f"{'blocks':>8} {'type':>4} {'samples':>10} "
        f"{'direct ns':>11} {'gauss-exp ns':>12} {'center ns':>10} {'hybrid ns':>11} "
        f"{'mkl-full ns':>12} {'mkl-raw ns':>10} "
        f"{'direct/mkl':>11} {'gauss/mkl':>10} {'center/mkl':>11} {'hybrid/mkl':>11} "
        f"{'center/gauss':>13} {'hybrid/gauss':>13} {'direct/raw':>11}"
    )
    print(header)
    print("-" * len(header))

    for (blocks, opt_type), modes in sorted(by_case.items(), key=lambda x: (int(x[0][0]), x[0][1])):
        sdk = modes.get("sdk-direct")
        sdk_gaussian = modes.get("sdk-gaussian-exp")
        sdk_center = modes.get("sdk-center-shared")
        sdk_hybrid = modes.get("sdk-hybrid")
        mkl_full = modes.get("mkl-sobol-gaussian-price")
        mkl_uniform = modes.get("mkl-sobol-uniform")
        samples = next(iter(modes.values())).get("samples", "NA")
        direct_ns = as_float(sdk, "ns_per_value") if sdk else None
        gaussian_ns = as_float(sdk_gaussian, "ns_per_value") if sdk_gaussian else None
        center_ns = as_float(sdk_center, "ns_per_value") if sdk_center else None
        hybrid_ns = as_float(sdk_hybrid, "ns_per_value") if sdk_hybrid else None
        mkl_full_ns = as_float(mkl_full, "ns_per_value") if mkl_full else None
        raw_ns = as_float(mkl_uniform, "ns_per_value") if mkl_uniform else None
        direct_mkl = mkl_full_ns / direct_ns if direct_ns and mkl_full_ns else None
        gaussian_mkl = mkl_full_ns / gaussian_ns if gaussian_ns and mkl_full_ns else None
        center_mkl = mkl_full_ns / center_ns if center_ns and mkl_full_ns else None
        hybrid_mkl = mkl_full_ns / hybrid_ns if hybrid_ns and mkl_full_ns else None
        center_gaussian = center_ns / gaussian_ns if gaussian_ns and center_ns else None
        hybrid_gaussian = hybrid_ns / gaussian_ns if gaussian_ns and hybrid_ns else None
        direct_raw = direct_ns / raw_ns if direct_ns and raw_ns else None

        print(
            f"{fmt_text(blocks, 8)} "
            f"{fmt_text(opt_type, 4)} "
            f"{fmt_text(samples, 10)} "
            f"{fmt_float(direct_ns, width=11)} "
            f"{fmt_float(gaussian_ns, width=12)} "
            f"{fmt_float(center_ns, width=10)} "
            f"{fmt_float(hybrid_ns, width=11)} "
            f"{fmt_float(mkl_full_ns, width=12)} "
            f"{fmt_float(raw_ns, width=10)} "
            f"{fmt_ratio(direct_mkl, width=11)} "
            f"{fmt_ratio(gaussian_mkl, width=10)} "
            f"{fmt_ratio(center_mkl, width=11)} "
            f"{fmt_ratio(hybrid_mkl, width=11)} "
            f"{fmt_ratio(center_gaussian, width=13)} "
            f"{fmt_ratio(hybrid_gaussian, width=13)} "
            f"{fmt_ratio(direct_raw, width=11)}"
        )


def build():
    run(["cmake", "-S", BENCH_DIR, "-B", BUILD_DIR, "-DCMAKE_BUILD_TYPE=Release"])
    run(["cmake", "--build", BUILD_DIR, "-j"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", type=int, nargs="+", help="explicit block counts; overrides --suite")
    ap.add_argument("--suite", choices=sorted(SUITES), default="quick")
    ap.add_argument("--iterations", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--types", nargs="+", choices=["call", "put"], default=["call", "put"])
    ap.add_argument("--modes", nargs="+", default=["sdk-direct", "sdk-gaussian-exp", "sdk-center-shared", "sdk-hybrid", "mkl-sobol-uniform", "mkl-sobol-gaussian-price"])
    ap.add_argument("--s0", type=float, default=100.0)
    ap.add_argument("--k", type=float, default=100.0)
    ap.add_argument("--r", type=float, default=0.05)
    ap.add_argument("--sigma", type=float, default=0.2)
    ap.add_argument("--t", type=float, default=1.0)
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--sde", type=Path, help="optional Intel SDE executable used to wrap benchmark runs")
    ap.add_argument("--raw", action="store_true", help="print raw RESULT lines from the benchmark executable")
    ap.add_argument("--no-build", action="store_true")
    args = ap.parse_args()
    blocks_list = args.blocks if args.blocks else SUITES[args.suite]

    if not args.no_build:
        build()

    rows = []
    for blocks in blocks_list:
        for opt_type in args.types:
            for mode in args.modes:
                cmd = [
                    BIN,
                    "--blocks", blocks,
                    "--type", opt_type,
                    "--mode", mode,
                    "--iterations", args.iterations,
                    "--warmup", args.warmup,
                    "--s0", args.s0,
                    "--k", args.k,
                    "--r", args.r,
                    "--sigma", args.sigma,
                    "--t", args.t,
                ]
                if args.sde:
                    cmd = [args.sde, "-skx", "--", *cmd]
                out = run(cmd)
                if args.raw:
                    print(out, end="")
                for line in out.splitlines():
                    if line.startswith("RESULT "):
                        rows.append(parse_result(line))

    if args.csv and rows:
        keys = sorted({k for row in rows for k in row})
        with args.csv.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)

    print_result_table(rows)
    print_summary(rows)


if __name__ == "__main__":
    main()
