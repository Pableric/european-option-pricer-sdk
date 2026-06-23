cmake_minimum_required(VERSION 3.18)
project(european_option_pricer_mkl_bench LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

set(SDK_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." CACHE PATH "Path to SDK root")
set(SDK_INCLUDE_DIR "${SDK_ROOT}/include")
set(SDK_LIBRARY "${SDK_ROOT}/lib/libeuropean_pricer.so")

if(NOT EXISTS "${SDK_INCLUDE_DIR}/european_pricer.h")
  message(FATAL_ERROR "Missing SDK public header: ${SDK_INCLUDE_DIR}/european_pricer.h")
endif()

if(NOT EXISTS "${SDK_LIBRARY}")
  message(FATAL_ERROR "Missing SDK shared library: ${SDK_LIBRARY}")
endif()

if(DEFINED ENV{MKLROOT} AND EXISTS "$ENV{MKLROOT}")
  file(TO_CMAKE_PATH "$ENV{MKLROOT}" MKL_ROOT)
elseif(EXISTS "/opt/intel/oneapi/mkl/latest")
  set(MKL_ROOT "/opt/intel/oneapi/mkl/latest")
else()
  message(FATAL_ERROR "Intel oneMKL was not found. Source setvars.sh or set MKLROOT.")
endif()

set(MKL_INCLUDE_DIR "${MKL_ROOT}/include")
find_library(MKL_RT_LIBRARY NAMES mkl_rt PATHS "${MKL_ROOT}/lib/intel64" NO_DEFAULT_PATH)

if(NOT EXISTS "${MKL_INCLUDE_DIR}/mkl.h")
  message(FATAL_ERROR "Missing oneMKL header: ${MKL_INCLUDE_DIR}/mkl.h")
endif()

if(NOT MKL_RT_LIBRARY)
  message(FATAL_ERROR "Missing oneMKL runtime library under ${MKL_ROOT}/lib/intel64")
endif()

add_executable(bench_european_mkl src/bench_european_mkl.cpp)
target_include_directories(bench_european_mkl PRIVATE "${SDK_INCLUDE_DIR}" "${MKL_INCLUDE_DIR}")
target_link_libraries(bench_european_mkl PRIVATE "${SDK_LIBRARY}" "${MKL_RT_LIBRARY}" dl pthread m)
target_compile_options(bench_european_mkl PRIVATE -O3 -Wall -Wextra -Wpedantic)
set_target_properties(bench_european_mkl PROPERTIES
  BUILD_RPATH "${SDK_ROOT}/lib;${MKL_ROOT}/lib/intel64"
  INSTALL_RPATH "${SDK_ROOT}/lib;${MKL_ROOT}/lib/intel64")

enable_testing()
add_test(NAME smoke_direct
  COMMAND bench_european_mkl --blocks 1 --type call --mode sdk-direct --iterations 2 --warmup 1)
add_test(NAME smoke_gaussian_exp
  COMMAND bench_european_mkl --blocks 1 --type call --mode sdk-gaussian-exp --iterations 2 --warmup 1)
add_test(NAME smoke_hybrid
  COMMAND bench_european_mkl --blocks 1 --type call --mode sdk-hybrid --iterations 2 --warmup 1)
add_test(NAME smoke_mkl_full
  COMMAND bench_european_mkl --blocks 1 --type call --mode mkl-sobol-gaussian-price --iterations 2 --warmup 1)
