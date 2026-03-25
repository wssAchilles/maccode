#pragma once

#include <iostream>
#include <string>

#include <grpcpp/grpcpp.h>

inline std::string ExtractRequestId(const grpc::ServerContext* context) {
  if (context == nullptr) {
    return "";
  }
  const auto& metadata = context->client_metadata();
  const auto it = metadata.find("x-request-id");
  if (it == metadata.end()) {
    return "";
  }
  return std::string(it->second.data(), it->second.size());
}

inline void LogRequestStart(const char* method, const grpc::ServerContext* context) {
  const std::string request_id = ExtractRequestId(context);
  if (request_id.empty()) {
    std::clog << "[matching-grpc] method=" << method << std::endl;
    return;
  }
  std::clog << "[matching-grpc] method=" << method << " request_id=" << request_id << std::endl;
}

inline void EchoRequestId(grpc::ServerContext* context) {
  if (context == nullptr) {
    return;
  }
  const std::string request_id = ExtractRequestId(context);
  if (request_id.empty()) {
    return;
  }
  context->AddInitialMetadata("x-request-id", request_id);
}
