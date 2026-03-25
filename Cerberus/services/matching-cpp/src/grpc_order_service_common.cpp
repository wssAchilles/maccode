#include "grpc_order_service.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <sstream>
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

std::size_t ReadEnvSize(const char* key, std::size_t default_value) {
  const std::string raw = ReadEnvString(key);
  if (raw.empty()) {
    return default_value;
  }
  try {
    const auto parsed = static_cast<std::size_t>(std::stoull(raw));
    return parsed > 0 ? parsed : default_value;
  } catch (...) {
    return default_value;
  }
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

GrpcOrderService::GrpcOrderService(OrderService& service)
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
      execution_stream_limit_(ReadEnvSize("MATCHING_EXECUTION_STREAM_LIMIT", 500)),
      submit_latency_window_size_(ReadEnvSize("MATCHING_SUBMIT_LATENCY_WINDOW_SIZE", 1024)) {}

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
