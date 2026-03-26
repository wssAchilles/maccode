#include "grpc_order_service.hpp"

#include <iostream>
#include <sstream>

#include "grpc_request_logging.hpp"

namespace {

std::string TrimAscii(std::string value) {
  const auto begin = value.find_first_not_of(" \t\r\n");
  if (begin == std::string::npos) {
    return "";
  }
  const auto end = value.find_last_not_of(" \t\r\n");
  return value.substr(begin, end - begin + 1);
}

}  // namespace

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

std::string GrpcOrderService::DegradedReasonForRpc(const char* rpc_name) const {
  const std::string base = DegradedStatusText();
  if (rpc_name == nullptr || *rpc_name == '\0') {
    return base;
  }
  std::ostringstream oss;
  oss << base << "; rpc=" << rpc_name;
  return oss.str();
}

grpc::Status GrpcOrderService::BuildDegradedUnavailable(grpc::ServerContext* context,
                                                        const char* rpc_name) const {
  const std::string reason = DegradedReasonForRpc(rpc_name);
  MarkDegraded(context, reason);
  const std::string request_id = TrimAscii(ExtractRequestId(context));
  if (request_id.empty()) {
    std::clog << "[matching-grpc] degraded_reject rpc=" << (rpc_name ? rpc_name : "") << std::endl;
  } else {
    std::clog << "[matching-grpc] degraded_reject rpc=" << (rpc_name ? rpc_name : "")
              << " request_id=" << request_id << std::endl;
  }
  return grpc::Status(grpc::StatusCode::UNAVAILABLE, reason);
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

void GrpcOrderService::MarkBackpressure(grpc::ServerContext* context,
                                        const std::string& reason) const {
  if (context == nullptr) {
    return;
  }
  context->AddTrailingMetadata("x-cerberus-backpressure", "true");
  if (!reason.empty()) {
    context->AddTrailingMetadata("x-cerberus-backpressure-reason", reason);
  }
}
