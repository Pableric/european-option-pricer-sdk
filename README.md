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
call       1       8,192      0.320556     5.459473    0.107300       17.03x       0.33x
put        1       8,192      0.312866     5.229248    0.109985       16.71x       0.35x
call       2      16,384      0.246765     5.349609    0.113464       21.68x       0.46x
put        2      16,384      0.245300     5.103455    0.130554       20.80x       0.53x
call       4      32,768      0.202271     5.244476    0.114899       25.93x       0.57x
put        4      32,768      0.203888     5.004608    0.107574       24.55x       0.53x
call       8      65,536      0.179428     5.119690    0.110840       28.53x       0.62x
put        8      65,536      0.180267     4.988266    0.110199       27.67x       0.61x
call      16     131,072      0.168640     5.269676    0.109154       31.25x       0.65x
put       16     131,072      0.168541     4.940216    0.109978       29.31x       0.65x
call      32     262,144      0.163387     5.227467    0.112938       31.99x       0.69x
put       32     262,144      0.163303     4.933392    0.107868       30.21x       0.66x
call      64     524,288      0.160809     5.182238    0.130350       32.23x       0.81x
put       64     524,288      0.160677     4.847273    0.139717       30.17x       0.87x
call     128   1,048,576      0.159328     5.242552    0.188510       32.90x       1.18x
put      128   1,048,576      0.159221     5.006371    0.195764       31.44x       1.23x
```

The one-block case is included deliberately. The Gaussian path is already much
faster than oneMKL full pricing at small batches, while larger batches show the
intended steady-state behavior. At 128 blocks, full SDK Gaussian pricing is also
faster than raw oneMKL Sobol uniform generation alone.

`mkl-sobol-uniform` is a raw generator baseline, not a pricing baseline.
