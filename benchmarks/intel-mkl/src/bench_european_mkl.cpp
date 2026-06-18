#include "european_pricer.h"

#include <mkl.h>
#include <mkl_vsl.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <string>
#include <vector>

static constexpr std::uint64_t kBlockSize = 8192;

struct Config {
    std::uint64_t blocks = 128;
    int iterations = 5;
    int warmup = 2;
    std::string type = "call";
    std::string mode = "sdk-direct";
    float s0 = 100.0f;
    float k = 100.0f;
    float r = 0.05f;
    float sigma = 0.2f;
    float t = 1.0f;
};

static double now_seconds() {
    using clock = std::chrono::steady_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

static void die_usage(const char* prog) {
    std::fprintf(stderr,
        "usage: %s --blocks N --type call|put --mode MODE [--iterations N] [--warmup N] [--s0 v --k v --r v --sigma v --t v]\n",
        prog);
    std::exit(2);
}

static Config parse_args(int argc, char** argv) {
    Config c;
    for (int i = 1; i < argc; ++i) {
        auto need = [&]() -> const char* {
            if (i + 1 >= argc) die_usage(argv[0]);
            return argv[++i];
        };
        if (std::strcmp(argv[i], "--blocks") == 0) c.blocks = std::strtoull(need(), nullptr, 10);
        else if (std::strcmp(argv[i], "--iterations") == 0) c.iterations = std::atoi(need());
        else if (std::strcmp(argv[i], "--warmup") == 0) c.warmup = std::atoi(need());
        else if (std::strcmp(argv[i], "--type") == 0) c.type = need();
        else if (std::strcmp(argv[i], "--mode") == 0) c.mode = need();
        else if (std::strcmp(argv[i], "--s0") == 0) c.s0 = std::strtof(need(), nullptr);
        else if (std::strcmp(argv[i], "--k") == 0) c.k = std::strtof(need(), nullptr);
        else if (std::strcmp(argv[i], "--r") == 0) c.r = std::strtof(need(), nullptr);
        else if (std::strcmp(argv[i], "--sigma") == 0) c.sigma = std::strtof(need(), nullptr);
        else if (std::strcmp(argv[i], "--t") == 0) c.t = std::strtof(need(), nullptr);
        else die_usage(argv[0]);
    }
    if (c.blocks == 0 || c.iterations <= 0 || c.warmup < 0) die_usage(argv[0]);
    if (c.type != "call" && c.type != "put") die_usage(argv[0]);
    return c;
}

static void check_mkl(int rc, const char* what) {
    if (rc != VSL_STATUS_OK) {
        std::fprintf(stderr, "MKL error: %s failed rc=%d\n", what, rc);
        std::exit(1);
    }
}

static double normal_cdf(double x) {
    return 0.5 * std::erfc(-x / std::sqrt(2.0));
}

static double analytic_price(const Config& c) {
    const double s0 = c.s0;
    const double k = c.k;
    const double r = c.r;
    const double sigma = c.sigma;
    const double t = c.t;
    const double df = std::exp(-r * t);
    if (sigma == 0.0) {
        const double fwd = s0 * std::exp(r * t);
        const double payoff = c.type == "call" ? std::max(fwd - k, 0.0) : std::max(k - fwd, 0.0);
        return df * payoff;
    }
    const double vol = sigma * std::sqrt(t);
    const double d1 = (std::log(s0 / k) + (r + 0.5 * sigma * sigma) * t) / vol;
    const double d2 = d1 - vol;
    if (c.type == "call") return s0 * normal_cdf(d1) - k * df * normal_cdf(d2);
    return k * df * normal_cdf(-d2) - s0 * normal_cdf(-d1);
}

static double price_from_gaussian(const Config& c, const std::vector<float>& z) {
    const double s0 = c.s0;
    const double k = c.k;
    const double r = c.r;
    const double sigma = c.sigma;
    const double t = c.t;
    const double mu = (r - 0.5 * sigma * sigma) * t;
    const double vol = sigma * std::sqrt(t);
    const double df = std::exp(-r * t);
    double sum = 0.0;
    for (float zi_f : z) {
        const double st = s0 * std::exp(mu + vol * static_cast<double>(zi_f));
        const double payoff = c.type == "call" ? std::max(st - k, 0.0) : std::max(k - st, 0.0);
        sum += df * payoff;
    }
    return sum / static_cast<double>(z.size());
}

static double run_sdk(const Config& c, european_pricing_mode_t mode, double* setup_seconds) {
    european_price_request_t req{};
    req.s0 = c.s0;
    req.k = c.k;
    req.r = c.r;
    req.sigma = c.sigma;
    req.t = c.t;
    req.num_blocks = c.blocks;
    req.type = c.type == "call" ? EUROPEAN_CALL : EUROPEAN_PUT;
    req.mode = mode;

    european_price_result_t out{};
    const int rc = price_european(&req, &out);
    if (rc != 0) {
        std::fprintf(stderr, "price_european failed rc=%d\n", rc);
        std::exit(1);
    }
    *setup_seconds = out.coeff_setup_seconds;
    return out.price;
}

static double run_mkl_uniform(const Config& c, std::vector<float>& out) {
    (void)c;
    VSLStreamStatePtr stream = nullptr;
    check_mkl(vslNewStream(&stream, VSL_BRNG_SOBOL, 1), "vslNewStream uniform");
    const double t0 = now_seconds();
    check_mkl(vsRngUniform(VSL_RNG_METHOD_UNIFORM_STD, stream, static_cast<MKL_INT>(out.size()), out.data(), 0.0f, 1.0f), "vsRngUniform");
    const double t1 = now_seconds();
    check_mkl(vslDeleteStream(&stream), "vslDeleteStream uniform");
    volatile float sink = out.front() + out.back();
    (void)sink;
    return t1 - t0;
}

static double run_mkl_gaussian_price(const Config& c, std::vector<float>& z, double* price) {
    VSLStreamStatePtr stream = nullptr;
    check_mkl(vslNewStream(&stream, VSL_BRNG_SOBOL, 1), "vslNewStream gaussian");
    const double t0 = now_seconds();
    check_mkl(vsRngGaussian(VSL_RNG_METHOD_GAUSSIAN_ICDF, stream, static_cast<MKL_INT>(z.size()), z.data(), 0.0f, 1.0f), "vsRngGaussian ICDF");
    *price = price_from_gaussian(c, z);
    const double t1 = now_seconds();
    check_mkl(vslDeleteStream(&stream), "vslDeleteStream gaussian");
    return t1 - t0;
}

static void print_result(const Config& c, const char* mode, double price, double analytic,
                         double median_seconds, double setup_seconds) {
    const double samples = static_cast<double>(c.blocks * kBlockSize);
    const double values_per_sec = samples / median_seconds;
    const double ns_per_value = median_seconds * 1.0e9 / samples;
    std::printf("RESULT mode=%s type=%s blocks=%llu samples=%llu price=%.12g analytic=%.12g abs_err=%.6g setup_seconds=%.9f median_seconds=%.9f values_per_sec=%.6f ns_per_value=%.6f\n",
        mode,
        c.type.c_str(),
        static_cast<unsigned long long>(c.blocks),
        static_cast<unsigned long long>(c.blocks * kBlockSize),
        price,
        analytic,
        std::fabs(price - analytic),
        setup_seconds,
        median_seconds,
        values_per_sec,
        ns_per_value);
}

int main(int argc, char** argv) {
    const Config c = parse_args(argc, argv);
    const std::uint64_t samples = c.blocks * kBlockSize;
    if (samples > static_cast<std::uint64_t>(std::numeric_limits<MKL_INT>::max())) {
        std::fprintf(stderr, "sample count exceeds MKL_INT limit for this benchmark\n");
        return 1;
    }

    const double analytic = analytic_price(c);
    std::vector<double> times;
    times.reserve(static_cast<std::size_t>(c.iterations));
    double price = 0.0;
    double setup_seconds = 0.0;

    if (c.mode == "sdk-direct" || c.mode == "sdk-gaussian-exp" || c.mode == "sdk-buffer") {
        european_pricing_mode_t mode = EUROPEAN_MODE_DIRECT_PAYOFF;
        if (c.mode == "sdk-gaussian-exp") mode = EUROPEAN_MODE_GAUSSIAN_EXP;
        if (c.mode == "sdk-buffer") mode = EUROPEAN_MODE_BUFFER_REFERENCE;
        for (int i = 0; i < c.warmup; ++i) price = run_sdk(c, mode, &setup_seconds);
        for (int i = 0; i < c.iterations; ++i) {
            const double t0 = now_seconds();
            price = run_sdk(c, mode, &setup_seconds);
            const double t1 = now_seconds();
            times.push_back(t1 - t0);
        }
    } else if (c.mode == "mkl-sobol-uniform") {
        std::vector<float> out(static_cast<std::size_t>(samples));
        for (int i = 0; i < c.warmup; ++i) run_mkl_uniform(c, out);
        for (int i = 0; i < c.iterations; ++i) times.push_back(run_mkl_uniform(c, out));
        price = 0.0;
    } else if (c.mode == "mkl-sobol-gaussian-price") {
        std::vector<float> z(static_cast<std::size_t>(samples));
        for (int i = 0; i < c.warmup; ++i) run_mkl_gaussian_price(c, z, &price);
        for (int i = 0; i < c.iterations; ++i) times.push_back(run_mkl_gaussian_price(c, z, &price));
    } else {
        die_usage(argv[0]);
    }

    std::sort(times.begin(), times.end());
    const double median = times[times.size() / 2];
    print_result(c, c.mode.c_str(), price, analytic, median, setup_seconds);
    return 0;
}
