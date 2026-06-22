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

    print("\nRESULT TABLE")
    header = (
        f"{'blocks':>8} {'type':>4} {'mode':>24} {'workload':>14} "
        f"{'samples':>10} {'ns/value':>12} {'Gvalues/s':>12} "
        f"{'price':>14} {'abs_err':>12}"
    )
    print(header)
    print("-" * len(header))
    for row in sorted(rows, key=lambda r: (int(r["blocks"]), r["type"], r["mode"])):
        ns = as_float(row, "ns_per_value")
        vps = as_float(row, "values_per_sec")
        gvps = vps / 1.0e9 if vps is not None else None
        err = as_float(row, "abs_err")
        print(
            f"{fmt_text(row.get('blocks', 'NA'), 8)} "
            f"{fmt_text(row.get('type', 'NA'), 4)} "
            f"{row.get('mode', 'NA'):>24} "
            f"{row.get('workload', 'unknown'):>14} "
            f"{fmt_text(row.get('samples', 'NA'), 10)} "
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

    for (blocks, opt_type), modes in sorted(by_case.items(), key=lambda x: (int(x[0][0]), x[0][1])):
        sdk = modes.get("sdk-direct")
        sdk_gaussian = modes.get("sdk-gaussian-exp")
        mkl_full = modes.get("mkl-sobol-gaussian-price")
        mkl_uniform = modes.get("mkl-sobol-uniform")
        samples = next(iter(modes.values())).get("samples", "NA")
        print(f"  blocks={blocks} samples={samples} type={opt_type}")

        if sdk and mkl_full:
            sdk_ns = as_float(sdk, "ns_per_value")
            mkl_ns = as_float(mkl_full, "ns_per_value")
            if sdk_ns and mkl_ns:
                print(f"    pricing speedup: sdk-direct {sdk_ns:.6f} ns/value vs mkl-full {mkl_ns:.6f} ns/value = {mkl_ns / sdk_ns:.2f}x")

        if sdk_gaussian and mkl_full:
            sdk_ns = as_float(sdk_gaussian, "ns_per_value")
            mkl_ns = as_float(mkl_full, "ns_per_value")
            if sdk_ns and mkl_ns:
                print(f"    pricing speedup: sdk-gaussian-exp {sdk_ns:.6f} ns/value vs mkl-full {mkl_ns:.6f} ns/value = {mkl_ns / sdk_ns:.2f}x")

        if sdk and sdk_gaussian:
            direct_ns = as_float(sdk, "ns_per_value")
            gaussian_ns = as_float(sdk_gaussian, "ns_per_value")
            if direct_ns and gaussian_ns:
                print(f"    internal comparison: sdk-direct {direct_ns:.6f} ns/value vs sdk-gaussian-exp {gaussian_ns:.6f} ns/value = {gaussian_ns / direct_ns:.2f}x")

        if sdk and mkl_uniform:
            sdk_ns = as_float(sdk, "ns_per_value")
            raw_ns = as_float(mkl_uniform, "ns_per_value")
            if sdk_ns and raw_ns:
                print(f"    raw context: sdk full pricing is {sdk_ns / raw_ns:.2f}x the cost of MKL raw Sobol uniform generation")


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
    ap.add_argument("--modes", nargs="+", default=["sdk-direct", "sdk-gaussian-exp", "mkl-sobol-uniform", "mkl-sobol-gaussian-price"])
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
