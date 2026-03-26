#include "grpc_order_service.hpp"

#include <algorithm>
#include <cmath>
#include <vector>

grpc::Status GrpcOrderService::FinalizeSubmitStatus(
    grpc::Status status, bool accepted, const std::chrono::steady_clock::time_point& started_at) {
  const auto elapsed = std::chrono::steady_clock::now() - started_at;
  const auto latency_ms =
      static_cast<std::uint64_t>(std::max<std::int64_t>(
          std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count(), 0));
  submit_order_requests_total_.fetch_add(1);
  RecordSubmitLatencyMs(latency_ms);
  if (!status.ok()) {
    submit_order_errors_total_.fetch_add(1);
  }
  if (!accepted) {
    submit_order_rejections_total_.fetch_add(1);
  }
  return status;
}

void GrpcOrderService::RecordSubmitLatencyMs(std::uint64_t latency_ms) {
  std::scoped_lock<std::mutex> lock(submit_latency_mu_);
  submit_latency_samples_ms_.push_back(latency_ms);
  const auto limit = std::max<std::size_t>(submit_latency_window_size_, 1);
  while (submit_latency_samples_ms_.size() > limit) {
    submit_latency_samples_ms_.pop_front();
  }
}

double GrpcOrderService::SubmitOrderLatencyP95Ms() const {
  std::vector<std::uint64_t> samples;
  {
    std::scoped_lock<std::mutex> lock(submit_latency_mu_);
    if (submit_latency_samples_ms_.empty()) {
      return 0.0;
    }
    samples.assign(submit_latency_samples_ms_.begin(), submit_latency_samples_ms_.end());
  }
  std::sort(samples.begin(), samples.end());
  const auto idx = static_cast<std::size_t>(std::ceil(samples.size() * 0.95));
  const auto pos = std::min(samples.size() - 1, idx == 0 ? 0 : idx - 1);
  return static_cast<double>(samples[pos]);
}

double GrpcOrderService::SubmitOrderThroughputRps() const {
  const auto uptime_seconds = static_cast<double>(UptimeSeconds());
  if (uptime_seconds <= 0.0) {
    return 0.0;
  }
  return static_cast<double>(submit_order_requests_total_.load()) / uptime_seconds;
}

std::uint64_t GrpcOrderService::UptimeSeconds() const {
  const auto uptime =
      std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - started_at_)
          .count();
  return static_cast<std::uint64_t>(std::max<std::int64_t>(uptime, 0));
}
