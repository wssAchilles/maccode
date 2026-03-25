#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>
#include <algorithm>

#include <grpcpp/grpcpp.h>

#include "grpc_order_service.hpp"
#include "order_service.hpp"

namespace {

int ReadEnvInt(const char* key, int default_value, int min_value, int max_value) {
  const char* raw = std::getenv(key);
  if (raw == nullptr || *raw == '\0') {
    return default_value;
  }
  try {
    const int parsed = std::stoi(std::string(raw));
    return std::clamp(parsed, min_value, max_value);
  } catch (...) {
    return default_value;
  }
}

}  // namespace

int main() {
  const char* port_env = std::getenv("PORT");
  const std::string port = (port_env != nullptr && *port_env != '\0') ? port_env : "50051";
  const std::string listen_addr = "0.0.0.0:" + port;
  const int max_pollers = ReadEnvInt("MATCHING_GRPC_MAX_POLLERS", 8, 1, 64);
  const int min_pollers = ReadEnvInt("MATCHING_GRPC_MIN_POLLERS", std::max(1, max_pollers / 2), 1, max_pollers);
  const int num_cqs = ReadEnvInt("MATCHING_GRPC_NUM_CQS", std::max(1, max_pollers / 2), 1, max_pollers);

  OrderService order_service;
  GrpcOrderService grpc_service(order_service);

  grpc::ServerBuilder builder;
  builder.SetSyncServerOption(grpc::ServerBuilder::SyncServerOption::MIN_POLLERS, min_pollers);
  builder.SetSyncServerOption(grpc::ServerBuilder::SyncServerOption::MAX_POLLERS, max_pollers);
  builder.SetSyncServerOption(grpc::ServerBuilder::SyncServerOption::NUM_CQS, num_cqs);
  builder.AddListeningPort(listen_addr, grpc::InsecureServerCredentials());
  builder.RegisterService(&grpc_service);

  std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
  if (!server) {
    std::cerr << "failed to start Cerberus matching gRPC server on " << listen_addr << std::endl;
    return 1;
  }

  std::cout << "Cerberus matching gRPC server listening on " << listen_addr
            << " (min_pollers=" << min_pollers
            << ", max_pollers=" << max_pollers
            << ", num_cqs=" << num_cqs << ")" << std::endl;
  server->Wait();
  return 0;
}
