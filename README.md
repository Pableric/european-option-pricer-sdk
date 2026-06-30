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
python3 scripts/run_mkl_compare.py \
  --blocks 1 2 4 8 16 32 64 128 \
  --types call put \
  --modes sdk-gaussian-exp mkl-sobol-uniform mkl-sobol-gaussian-price \
  --iterations 5 \
  --warmup 2 \
  --raw
```

The benchmark compares the production SDK Gaussian pricing kernel
(`sdk-gaussian-exp`) against oneMKL full Sobol Gaussian pricing
(`mkl-sobol-gaussian-price`) and raw oneMKL Sobol uniform generation
(`mkl-sobol-uniform`). The raw Sobol mode does not produce a price.

Run a broader sweep:

```sh
python3 scripts/run_mkl_compare.py \
  --suite comprehensive \
  --modes sdk-gaussian-exp mkl-sobol-uniform mkl-sobol-gaussian-price \
  --iterations 5 \
  --warmup 2
```

Print raw benchmark lines as well as the summary tables:

```sh
python3 scripts/run_mkl_compare.py \
  --blocks 128 \
  --modes sdk-gaussian-exp mkl-sobol-uniform mkl-sobol-gaussian-price \
  --raw
```

Run only the SDK Gaussian kernel:

```sh
python3 scripts/run_mkl_compare.py --blocks 128 --modes sdk-gaussian-exp
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

Latest selected results for the production Gaussian path. `vs MKL full` is
`mkl-sobol-gaussian-price / sdk-gaussian-exp`. `vs MKL raw` is
`mkl-sobol-uniform / sdk-gaussian-exp`; raw MKL Sobol is a generator-only
baseline, not a pricing baseline.

```text
type  blocks  samples     sdk gauss ns  mkl full ns  mkl raw ns  vs MKL full  vs MKL raw
call       1       8,192      0.188354     4.901245    0.097168       26.02x       0.52x
put        1       8,192      0.193237     4.446167    0.100586       23.01x       0.52x
call       2      16,384      0.168030     4.624756    0.112976       27.52x       0.67x
put        2      16,384      0.167725     4.293579    0.100159       25.60x       0.60x
call       4      32,768      0.162750     4.657501    0.096985       28.62x       0.60x
put        4      32,768      0.135895     4.366455    0.101440       32.13x       0.75x
call       8      65,536      0.122375     4.851883    0.097824       39.65x       0.80x
put        8      65,536      0.132751     4.304596    0.097382       32.43x       0.73x
call      16     131,072      0.127625     4.574944    0.097542       35.85x       0.76x
put       16     131,072      0.145645     4.245560    0.093956       29.15x       0.65x
call      32     262,144      0.121628     4.369350    0.090355       35.92x       0.74x
put       32     262,144      0.118477     4.115322    0.096710       34.74x       0.82x
call      64     524,288      0.121040     4.493906    0.124441       37.13x       1.03x
put       64     524,288      0.117683     4.257366    0.125456       36.18x       1.07x
call     128   1,048,576      0.135514     4.428988    0.175249       32.68x       1.29x
put      128   1,048,576      0.117492     4.421417    0.182332       37.63x       1.55x
```

The one-block case is included deliberately. The Gaussian path is already much
faster than oneMKL full pricing at small batches, while larger batches show the
intended steady-state behavior. At 64 and 128 blocks, full SDK Gaussian pricing
is also faster than raw oneMKL Sobol uniform generation alone in this snapshot.

`mkl-sobol-uniform` is a raw generator baseline, not a pricing baseline.
