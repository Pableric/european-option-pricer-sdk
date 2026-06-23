# European Option Pricer SDK

Alpha binary SDK for dimension-1 Sobol European option pricing.

The optimized implementation is distributed as a prebuilt Linux x86-64 shared
library. ABI, numerical behavior, packaging, and benchmark tooling may change.

## Build

```sh
make
```

## Run Example

```sh
make run
```

## Benchmark vs oneMKL

```sh
source /opt/intel/oneapi/setvars.sh
python3 scripts/run_mkl_compare.py --blocks 128 --iterations 5 --warmup 2
```

The benchmark reports the SDK pricing kernels, `sdk-direct`,
`sdk-gaussian-exp`, and experimental `sdk-hybrid`, separately from
`mkl-sobol-uniform`, which is raw Sobol uniform generation only and does not
produce a price.

Run a broader sweep:

```sh
python3 scripts/run_mkl_compare.py --suite comprehensive --iterations 5 --warmup 2
```

Print raw benchmark lines as well as the summary tables:

```sh
python3 scripts/run_mkl_compare.py --blocks 128 --raw
```

Run only one SDK kernel:

```sh
python3 scripts/run_mkl_compare.py --blocks 128 --modes sdk-direct
python3 scripts/run_mkl_compare.py --blocks 128 --modes sdk-gaussian-exp
python3 scripts/run_mkl_compare.py --blocks 128 --modes sdk-hybrid
```

On a machine without native AVX-512, wrap the benchmark with Intel SDE:

```sh
python3 scripts/run_mkl_compare.py --blocks 1 --iterations 1 --warmup 0 --sde /opt/intel-sde/sde64
```

## Benchmark Snapshot

Run on an AWS EC2 instance. Exact instance type and CPU model were not captured
in this snapshot.

Contract:

```text
S0=100 K=100 r=0.05 sigma=0.2 T=1
```

Latest selected results after the direct setup-fusion update. `vs MKL full`
compares `sdk-direct` against `mkl-sobol-gaussian-price`. `vs MKL Sobol`
compares full SDK pricing against raw MKL Sobol uniform generation only.

```text
type  blocks  samples     sdk ns/value  mkl full ns  mkl sobol ns  vs MKL full  vs MKL Sobol  sdk abs_err
call       1       8,192      5.158569     5.453491      0.109009        1.06x         0.02x    0.007818
put        1       8,192      4.906128     5.233032      0.111816        1.07x         0.02x    0.008435
call      16     131,072      0.512672     5.213966      0.109398       10.17x         0.21x    0.000602
put       16     131,072      0.466377     4.983978      0.110336       10.69x         0.24x    0.000509
call     128   1,048,576      0.195749     5.255865      0.185479       26.85x         0.95x    0.000089
put      128   1,048,576      0.191312     5.011817      0.187770       26.20x         0.98x    0.000060
```

The one-block case is included deliberately. After setup fusion it is already
competitive with oneMKL full pricing, while larger batches show the intended
steady-state behavior.

`mkl-sobol-uniform` is a raw generator baseline, not a pricing baseline.
