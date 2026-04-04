#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

namespace {

double nan_value() {
    return std::numeric_limits<double>::quiet_NaN();
}

bool has_non_finite(const std::vector<double>& values) {
    for (double value : values) {
        if (!std::isfinite(value)) {
            return true;
        }
    }
    return false;
}

double sample_stddev(const std::vector<double>& values) {
    const auto count = values.size();
    if (count < 2 || has_non_finite(values)) {
        return nan_value();
    }
    double mean = 0.0;
    for (double value : values) {
        mean += value;
    }
    mean /= static_cast<double>(count);

    double variance = 0.0;
    for (double value : values) {
        const double diff = value - mean;
        variance += diff * diff;
    }
    variance /= static_cast<double>(count - 1);
    return std::sqrt(variance);
}

double quantile(std::vector<double> values, double q) {
    if (values.empty() || has_non_finite(values)) {
        return nan_value();
    }
    std::sort(values.begin(), values.end());
    const double raw_index = q * static_cast<double>(values.size() - 1);
    const auto lower = static_cast<std::size_t>(std::floor(raw_index));
    const auto upper = static_cast<std::size_t>(std::ceil(raw_index));
    if (lower == upper) {
        return values[lower];
    }
    const double weight = raw_index - static_cast<double>(lower);
    return values[lower] + ((values[upper] - values[lower]) * weight);
}

std::vector<double> slice_window(const std::vector<double>& values, std::size_t end_exclusive, std::size_t width) {
    if (end_exclusive < width) {
        return {};
    }
    return std::vector<double>(
        values.begin() + static_cast<long>(end_exclusive - width),
        values.begin() + static_cast<long>(end_exclusive)
    );
}

py::dict compute_load_features(const std::vector<double>& site_load) {
    const auto size = site_load.size();
    std::vector<double> lag_1h(size, nan_value());
    std::vector<double> lag_24h(size, nan_value());
    std::vector<double> lag_168h(size, nan_value());
    std::vector<double> rolling_mean_6h(size, nan_value());
    std::vector<double> rolling_std_6h(size, nan_value());
    std::vector<double> rolling_mean_24h(size, nan_value());
    std::vector<double> quantile_95_24h(size, nan_value());
    std::vector<double> quantile_05_24h(size, nan_value());
    std::vector<double> volatility_24h(size, nan_value());
    std::vector<double> load_change_1h(size, nan_value());
    std::vector<double> load_change_pct_1h(size, nan_value());

    for (std::size_t index = 0; index < size; ++index) {
        if (index >= 1) {
            lag_1h[index] = site_load[index - 1];
            if (std::isfinite(site_load[index]) && std::isfinite(site_load[index - 1])) {
                load_change_1h[index] = site_load[index] - site_load[index - 1];
                if (site_load[index - 1] != 0.0) {
                    load_change_pct_1h[index] = ((site_load[index] / site_load[index - 1]) - 1.0) * 100.0;
                }
            }
        }
        if (index >= 24) {
            lag_24h[index] = site_load[index - 24];
        }
        if (index >= 168) {
            lag_168h[index] = site_load[index - 168];
        }

        const auto window_6h = slice_window(site_load, index, 6);
        if (!window_6h.empty() && !has_non_finite(window_6h)) {
            double mean = 0.0;
            for (double value : window_6h) {
                mean += value;
            }
            mean /= static_cast<double>(window_6h.size());
            rolling_mean_6h[index] = mean;
            rolling_std_6h[index] = sample_stddev(window_6h);
        }

        const auto window_24h = slice_window(site_load, index, 24);
        if (!window_24h.empty() && !has_non_finite(window_24h)) {
            double mean = 0.0;
            for (double value : window_24h) {
                mean += value;
            }
            mean /= static_cast<double>(window_24h.size());
            const double stddev = sample_stddev(window_24h);
            rolling_mean_24h[index] = mean;
            quantile_95_24h[index] = quantile(window_24h, 0.95);
            quantile_05_24h[index] = quantile(window_24h, 0.05);
            if (std::isfinite(mean) && mean != 0.0) {
                volatility_24h[index] = stddev / mean;
            }
        }
    }

    py::dict result;
    result["Lag_1h"] = lag_1h;
    result["Lag_24h"] = lag_24h;
    result["Lag_168h"] = lag_168h;
    result["Rolling_Mean_6h"] = rolling_mean_6h;
    result["Rolling_Std_6h"] = rolling_std_6h;
    result["Rolling_Mean_24h"] = rolling_mean_24h;
    result["Quantile_95_24h"] = quantile_95_24h;
    result["Quantile_05_24h"] = quantile_05_24h;
    result["Volatility_24h"] = volatility_24h;
    result["Load_Change_1h"] = load_change_1h;
    result["Load_Change_Pct_1h"] = load_change_pct_1h;
    return result;
}

}  // namespace

PYBIND11_MODULE(rolling_features_native, module) {
    module.doc() = "Optional rolling feature kernel for the industrial data science runtime";
    module.def("compute_load_features", &compute_load_features);
}

