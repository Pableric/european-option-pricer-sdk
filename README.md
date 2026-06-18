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

## Benchmark Snapshot

Run on an AWS EC2 instance. Exact instance type and CPU model were not captured
in this snapshot.

Contract:

```text
S0=100 K=100 r=0.05 sigma=0.2 T=1
```

Selected results. `vs MKL full` compares `sdk-direct` against
`mkl-sobol-gaussian-price`. `vs MKL Sobol` compares full SDK pricing against raw
MKL Sobol uniform generation only.

```text
type  blocks  samples     sdk ns/value  mkl full ns  mkl sobol ns  vs MKL full  vs MKL Sobol  sdk abs_err
call       1       8,192     10.023682     5.451050      0.109009        0.54x         0.01x    0.007816
put        1       8,192      9.969727     5.200562      0.109131        0.52x         0.01x    0.008436
call     128   1,048,576      0.233498     5.257521      0.188629       22.52x         0.81x    0.000087
put      128   1,048,576      0.227925     5.016124      0.187053       22.01x         0.82x    0.000062
call    1221  10,002,432      0.159627     5.331564      0.201620       33.40x         1.26x    0.000087
put     1221  10,002,432      0.163024     5.083920      0.192128       31.19x         1.18x    0.000014
call    8192  67,108,864      0.150344     5.383434      0.344888       35.81x         2.29x    0.004804
put     8192  67,108,864      0.148991     5.051132      0.349008       33.90x         2.34x    0.001430
```

The one-block case is included deliberately: it is not the strong case for this
kernel. The optimized path is designed for block batches where setup and fixed
entry overhead are amortized.

`mkl-sobol-uniform` is a raw generator baseline, not a pricing baseline.

