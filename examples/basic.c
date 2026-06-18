#include "european_pricer.h"

#include <stdio.h>

int main(void) {
    european_price_request_t req = {
        .s0 = 100.0f,
        .k = 100.0f,
        .r = 0.05f,
        .sigma = 0.2f,
        .t = 1.0f,
        .num_blocks = 128,
        .type = EUROPEAN_CALL,
        .mode = EUROPEAN_MODE_DIRECT_PAYOFF,
    };

    european_price_result_t out;
    const int rc = price_european(&req, &out);
    if (rc != 0) {
        fprintf(stderr, "price_european failed: rc=%d\n", rc);
        return 1;
    }

    const double analytic = black_scholes_price(&req);
    printf("price=%.12g analytic=%.12g abs_err=%.6g samples=%llu\n",
           out.price,
           analytic,
           out.price > analytic ? out.price - analytic : analytic - out.price,
           (unsigned long long)out.samples);
    printf("setup_seconds=%.9f kernel_seconds=%.9f\n",
           out.coeff_setup_seconds,
           out.kernel_seconds);
    return 0;
}

