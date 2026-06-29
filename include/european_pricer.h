#ifndef EUROPEAN_PRICER_H
#define EUROPEAN_PRICER_H

#include <stdint.h>

#define EUROPEAN_SOBOL_BLOCK_SIZE 8192u

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    EUROPEAN_CALL = 0,
    EUROPEAN_PUT = 1
} european_option_type_t;

typedef enum {
    EUROPEAN_MODE_BUFFER_REFERENCE = 0,
    EUROPEAN_MODE_GAUSSIAN_EXP = 1,
    EUROPEAN_MODE_DIRECT_PAYOFF = 2,
    EUROPEAN_MODE_HYBRID = 3,
    EUROPEAN_MODE_HYBRID_DIRECT_TAIL = 4,
    EUROPEAN_MODE_GAUSSIAN_SPLIT_TAIL = 5,
    EUROPEAN_MODE_GAUSSIAN_CENTER_SHARED = 6
} european_pricing_mode_t;

typedef struct {
    float s0;
    float k;
    float r;
    float sigma;
    float t;
    uint64_t num_blocks;
    european_option_type_t type;
    european_pricing_mode_t mode;
} european_price_request_t;

typedef struct {
    double price;
    double payoff_sum;
    uint64_t samples;
    double coeff_setup_seconds;
    double kernel_seconds;
} european_price_result_t;

int price_european(const european_price_request_t* req, european_price_result_t* out);
double black_scholes_price(const european_price_request_t* req);

#ifdef __cplusplus
}
#endif

#endif
