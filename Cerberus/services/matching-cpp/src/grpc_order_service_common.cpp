#include "grpc_order_service.hpp"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <sstream>

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
      submit_latency_window_size_(std::max<std::size_t>(runtime_config.submit_latency_window_size,
                                                        1)),
      max_inflight_requests_(std::max<std::size_t>(runtime_config.max_inflight_requests, 1)),
      inflight_acquire_timeout_ms_(runtime_config.inflight_acquire_timeout_ms),
      backpressure_retry_sleep_ms_(runtime_config.backpressure_retry_sleep_ms) {
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
