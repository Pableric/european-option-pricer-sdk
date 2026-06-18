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


if __name__ == "__main__":
    main()
