#include "grpc_order_service.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <sstream>
#include <thread>
#include <vector>

#include "grpc_request_logging.hpp"

namespace {

std::string ReadEnvString(const char* key) {
  const char* raw = std::getenv(key);
  if (raw == nullptr || *raw == '\0') {
    return "";
  }
  return std::string(raw);
}

bool ReadEnvBool(const char* key, bool default_value) {
  const std::string raw = ReadEnvString(key);
  if (raw.empty()) {
    return default_value;
  }
  if (raw == "1" || raw == "true" || raw == "TRUE" || raw == "yes" || raw == "on") {
    return true;
  }
  if (raw == "0" || raw == "false" || raw == "FALSE" || raw == "no" || raw == "off") {
    return false;
  }
  return default_value;
}

std::string TrimAscii(std::string value) {
  const auto begin = value.find_first_not_of(" \t\r\n");
  if (begin == std::string::npos) {
    return "";
  }
  const auto end = value.find_last_not_of(" \t\r\n");
  return value.substr(begin, end - begin + 1);
}

}  // namespace

GrpcOrderService::GrpcOrderService(OrderService& service, GrpcRuntimeConfig runtime_config)
    : service_(service),
      started_at_(std::chrono::steady_clock::now()),
      service_version_([] {
        const char* raw = std::getenv("CERBERUS_MATCHING_VERSION");
        if (raw == nullptr || *raw == '\0') {
          return std::string("0.1.0");
        }
        return std::string(raw);
      }()),
      force_degraded_(ReadEnvBool("MATCHING_FORCE_DEGRADED", false)),
      degraded_reason_([] {
        const std::string raw = ReadEnvString("MATCHING_DEGRADED_REASON");
        if (raw.empty()) {
          return std::string("manual override");
        }
        return raw;
      }()),
      schema_version_([] {
        const std::string raw = TrimAscii(ReadEnvString("CERBERUS_EVENT_SCHEMA_VERSION"));
        if (raw.empty()) {
          return std::string("v1");
        }
        return raw;
      }()),
      grpc_min_pollers_(std::max(runtime_config.min_pollers, 1)),
      grpc_max_pollers_(std::max(runtime_config.max_pollers, 1)),
      grpc_num_cqs_(std::max(runtime_config.num_cqs, 1)),
      execution_stream_limit_(std::max<std::size_t>(runtime_config.execution_stream_limit, 1)),
      submit_latency_window_size_(std::max<std::size_t>(runtime_config.submit_latency_window_size, 1)),
      max_inflight_requests_(std::max<std::size_t>(runtime_config.max_inflight_requests, 1)),
      inflight_acquire_timeout_ms_(runtime_config.inflight_acquire_timeout_ms) {
  grpc_max_pollers_ = std::max(grpc_max_pollers_, 1);
  grpc_min_pollers_ = std::clamp(grpc_min_pollers_, 1, grpc_max_pollers_);
  grpc_num_cqs_ = std::clamp(grpc_num_cqs_, 1, grpc_max_pollers_);
}

Side GrpcOrderService::ToDomainSide(cerberus::order::v1::Side side, bool& ok) {
  ok = true;
  switch (side) {
    case cerberus::order::v1::SIDE_BUY:
      return Side::Buy;
    case cerberus::order::v1::SIDE_SELL:
      return Side::Sell;
    case cerberus::order::v1::SIDE_UNSPECIFIED:
    default:
      ok = false;
      return Side::Buy;
  }
}

cerberus::order::v1::Side GrpcOrderService::ToProtoSide(Side side) {
  switch (side) {
    case Side::Buy:
      return cerberus::order::v1::SIDE_BUY;
    case Side::Sell:
      return cerberus::order::v1::SIDE_SELL;
    default:
      return cerberus::order::v1::SIDE_UNSPECIFIED;
  }
}

cerberus::order::v1::OrderStatus GrpcOrderService::ToProtoStatus(OrderStatus status) {
  switch (status) {
    case OrderStatus::New:
      return cerberus::order::v1::ORDER_STATUS_NEW;
    case OrderStatus::PartiallyFilled:
      return cerberus::order::v1::ORDER_STATUS_PARTIALLY_FILLED;
    case OrderStatus::Filled:
      return cerberus::order::v1::ORDER_STATUS_FILLED;
    case OrderStatus::Canceled:
      return cerberus::order::v1::ORDER_STATUS_CANCELED;
    case OrderStatus::Rejected:
      return cerberus::order::v1::ORDER_STATUS_REJECTED;
    default:
      return cerberus::order::v1::ORDER_STATUS_UNSPECIFIED;
  }
}

void GrpcOrderService::FillNowTimestamp(google::protobuf::Timestamp* ts) {
  const auto now = std::chrono::system_clock::now().time_since_epoch();
  const auto seconds = std::chrono::duration_cast<std::chrono::seconds>(now);
  const auto nanos = std::chrono::duration_cast<std::chrono::nanoseconds>(now - seconds);
  ts->set_seconds(seconds.count());
  ts->set_nanos(static_cast<int>(nanos.count()));
}

std::string GrpcOrderService::NextGeneratedOrderId(const std::string& account_id) {
  const std::uint64_t next = next_generated_order_id_.fetch_add(1);
  std::ostringstream oss;
  oss << account_id << "-ord-" << std::setfill('0') << std::setw(10) << next;
  return oss.str();
}

bool GrpcOrderService::IsDegraded() const {
  return force_degraded_;
}

std::string GrpcOrderService::DegradedStatusText() const {
  std::ostringstream oss;
  oss << "degraded";
  if (!degraded_reason_.empty()) {
    oss << ":" << degraded_reason_;
  }
  return oss.str();
}

std::string GrpcOrderService::EffectiveSchemaVersion(const std::string& requested_schema) const {
  const std::string normalized = TrimAscii(requested_schema);
  if (!normalized.empty()) {
    return normalized;
  }
  return schema_version_;
}

std::string GrpcOrderService::EffectiveCorrelationId(
    grpc::ServerContext* context, const std::string& requested_correlation_id) const {
  const std::string normalized = TrimAscii(requested_correlation_id);
  if (!normalized.empty()) {
    return normalized;
  }
  return TrimAscii(ExtractRequestId(context));
}

void GrpcOrderService::FillResponseContext(grpc::ServerContext* context,
                                           const std::string& requested_schema,
                                           const std::string& requested_correlation_id,
                                           std::string* response_schema,
                                           std::string* response_correlation) const {
  if (response_schema != nullptr) {
    *response_schema = EffectiveSchemaVersion(requested_schema);
  }
  if (response_correlation != nullptr) {
    *response_correlation = EffectiveCorrelationId(context, requested_correlation_id);
  }
}

void GrpcOrderService::MarkDegraded(grpc::ServerContext* context, const std::string& reason) const {
  if (context == nullptr) {
    return;
  }
  context->AddTrailingMetadata("x-cerberus-degraded", "true");
  if (!reason.empty()) {
    context->AddTrailingMetadata("x-cerberus-degraded-reason", reason);
  }
}

void GrpcOrderService::MarkBackpressure(grpc::ServerContext* context, const std::string& reason) const {
  if (context == nullptr) {
    return;
  }
  context->AddTrailingMetadata("x-cerberus-backpressure", "true");
  if (!reason.empty()) {
    context->AddTrailingMetadata("x-cerberus-backpressure-reason", reason);
  }
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
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
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
