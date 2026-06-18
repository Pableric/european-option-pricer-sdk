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

The benchmark reports full pricing modes separately from `mkl-sobol-uniform`,
which is raw Sobol uniform generation only and does not produce a price.

Run a broader sweep:

```sh
python3 scripts/run_mkl_compare.py --suite comprehensive --iterations 5 --warmup 2
```

Print raw benchmark lines as well as the summary tables:

```sh
python3 scripts/run_mkl_compare.py --blocks 128 --raw
```

On a machine without native AVX-512, wrap the benchmark with Intel SDE:

```sh
python3 scripts/run_mkl_compare.py --blocks 1 --iterations 1 --warmup 0 --sde /opt/intel-sde/sde64
```
