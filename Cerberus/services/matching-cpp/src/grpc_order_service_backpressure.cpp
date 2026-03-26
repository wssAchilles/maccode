#include "grpc_order_service.hpp"

#include <algorithm>
#include <chrono>
#include <sstream>
#include <thread>

void GrpcOrderService::BackpressureRetryPause() const {
  if (backpressure_retry_sleep_ms_ == 0) {
    std::this_thread::yield();
    return;
  }
  std::this_thread::sleep_for(std::chrono::milliseconds(backpressure_retry_sleep_ms_));
}

grpc::Status GrpcOrderService::AcquireInflightPermit(grpc::ServerContext* context, const char* rpc_name,
                                                      std::optional<InflightPermit>* permit) {
  if (permit == nullptr) {
    return grpc::Status(grpc::StatusCode::INTERNAL, "inflight permit container is null");
  }

  const auto started_at = std::chrono::steady_clock::now();
  const std::uint64_t limit =
      static_cast<std::uint64_t>(std::max<std::size_t>(max_inflight_requests_, 1));
  bool waited = false;

  while (true) {
    std::uint64_t inflight_now = inflight_requests_.load(std::memory_order_relaxed);
    while (inflight_now < limit) {
      const std::uint64_t next = inflight_now + 1;
      if (inflight_requests_.compare_exchange_weak(inflight_now, next, std::memory_order_acq_rel,
                                                   std::memory_order_relaxed)) {
        ObserveInflightPeak(next);
        if (waited) {
          const auto waited_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                                     std::chrono::steady_clock::now() - started_at)
                                     .count();
          backpressure_wait_ms_total_.fetch_add(
              static_cast<std::uint64_t>(std::max<std::int64_t>(waited_ms, 0)),
              std::memory_order_relaxed);
        }
        *permit = InflightPermit(this);
        return grpc::Status::OK;
      }
    }

    if (context != nullptr && context->IsCancelled()) {
      return grpc::Status(grpc::StatusCode::CANCELLED, "request cancelled while waiting for capacity");
    }

    const auto waited_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                               std::chrono::steady_clock::now() - started_at)
                               .count();
    const auto waited_ms_u64 = static_cast<std::uint64_t>(std::max<std::int64_t>(waited_ms, 0));
    const bool timed_out =
        inflight_acquire_timeout_ms_ > 0 && waited_ms_u64 >= inflight_acquire_timeout_ms_;
    const bool reject_immediately = inflight_acquire_timeout_ms_ == 0;
    if (reject_immediately || timed_out) {
      backpressure_rejections_total_.fetch_add(1, std::memory_order_relaxed);
      if (timed_out) {
        backpressure_wait_timeouts_total_.fetch_add(1, std::memory_order_relaxed);
      }
      if (waited_ms_u64 > 0) {
        backpressure_wait_ms_total_.fetch_add(waited_ms_u64, std::memory_order_relaxed);
      }
      std::ostringstream reason;
      reason << "backpressure limit reached (max_inflight=" << limit
             << ", acquire_timeout_ms=" << inflight_acquire_timeout_ms_;
      if (rpc_name != nullptr && *rpc_name != '\0') {
        reason << ", rpc=" << rpc_name;
      }
      reason << ")";
      const auto reason_text = reason.str();
      MarkBackpressure(context, reason_text);
      return grpc::Status(grpc::StatusCode::RESOURCE_EXHAUSTED, reason_text);
    }

    if (!waited) {
      backpressure_waits_total_.fetch_add(1, std::memory_order_relaxed);
      waited = true;
    }
    BackpressureRetryPause();
  }
}

void GrpcOrderService::ReleaseInflightPermit() {
  std::uint64_t current = inflight_requests_.load(std::memory_order_relaxed);
  while (current > 0) {
    const std::uint64_t next = current - 1;
    if (inflight_requests_.compare_exchange_weak(current, next, std::memory_order_acq_rel,
                                                 std::memory_order_relaxed)) {
      return;
    }
  }
}

void GrpcOrderService::ObserveInflightPeak(std::uint64_t inflight_after_acquire) {
  std::uint64_t peak = inflight_requests_peak_.load(std::memory_order_relaxed);
  while (inflight_after_acquire > peak) {
    if (inflight_requests_peak_.compare_exchange_weak(peak, inflight_after_acquire,
                                                      std::memory_order_relaxed,
                                                      std::memory_order_relaxed)) {
      return;
    }
  }
}
