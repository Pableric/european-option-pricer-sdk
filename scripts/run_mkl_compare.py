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


def print_summary(rows):
    if not rows:
        return

    print("\nSUMMARY")
    by_case = {}
    for row in rows:
        key = (row.get("blocks"), row.get("type"))
        by_case.setdefault(key, {})[row.get("mode")] = row

    for (blocks, opt_type), modes in sorted(by_case.items(), key=lambda x: (int(x[0][0]), x[0][1])):
        sdk = modes.get("sdk-direct")
        mkl_full = modes.get("mkl-sobol-gaussian-price")
        mkl_uniform = modes.get("mkl-sobol-uniform")
        print(f"  blocks={blocks} type={opt_type}")

        if sdk and mkl_full:
            sdk_ns = as_float(sdk, "ns_per_value")
            mkl_ns = as_float(mkl_full, "ns_per_value")
            if sdk_ns and mkl_ns:
                print(f"    pricing: sdk-direct {sdk_ns:.6f} ns/value vs mkl-full {mkl_ns:.6f} ns/value = {mkl_ns / sdk_ns:.2f}x faster")

        if sdk and mkl_uniform:
            sdk_ns = as_float(sdk, "ns_per_value")
            raw_ns = as_float(mkl_uniform, "ns_per_value")
            if sdk_ns and raw_ns:
                print(f"    context: sdk full pricing is {sdk_ns / raw_ns:.2f}x the cost of MKL raw Sobol uniform generation")

        for mode, row in sorted(modes.items()):
            ns = as_float(row, "ns_per_value")
            workload = row.get("workload", "unknown")
            price = row.get("price", "NA")
            err = row.get("abs_err", "NA")
            print(f"    {mode}: workload={workload} ns/value={ns:.6f} price={price} abs_err={err}")


def build():
    run(["cmake", "-S", BENCH_DIR, "-B", BUILD_DIR, "-DCMAKE_BUILD_TYPE=Release"])
    run(["cmake", "--build", BUILD_DIR, "-j"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", type=int, nargs="+", default=[1, 16, 128])
    ap.add_argument("--iterations", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--types", nargs="+", choices=["call", "put"], default=["call", "put"])
    ap.add_argument("--modes", nargs="+", default=["sdk-direct", "mkl-sobol-uniform", "mkl-sobol-gaussian-price"])
    ap.add_argument("--s0", type=float, default=100.0)
    ap.add_argument("--k", type=float, default=100.0)
    ap.add_argument("--r", type=float, default=0.05)
    ap.add_argument("--sigma", type=float, default=0.2)
    ap.add_argument("--t", type=float, default=1.0)
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--sde", type=Path, help="optional Intel SDE executable used to wrap benchmark runs")
    ap.add_argument("--no-build", action="store_true")
    args = ap.parse_args()

    if not args.no_build:
        build()

    rows = []
    for blocks in args.blocks:
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

    print_summary(rows)


if __name__ == "__main__":
    main()
