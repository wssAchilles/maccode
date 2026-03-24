#include "grpc_order_service.hpp"

#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <sstream>

GrpcOrderService::GrpcOrderService(OrderService& service)
    : service_(service),
      started_at_(std::chrono::steady_clock::now()),
      service_version_([] {
        const char* raw = std::getenv("CERBERUS_MATCHING_VERSION");
        if (raw == nullptr || *raw == '\0') {
          return std::string("0.1.0");
        }
        return std::string(raw);
      }()) {}

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
