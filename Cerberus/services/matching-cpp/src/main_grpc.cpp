#include <iostream>
#include <memory>

#include <grpcpp/grpcpp.h>

#include "grpc_order_service.hpp"
#include "order_service.hpp"
#include "runtime_config.hpp"

int main() {
  const std::string listen_addr = ResolveListenAddress();
  const GrpcRuntimeConfig runtime_config = BuildRuntimeConfigFromEnv();
  LogRuntimeConfig(listen_addr, runtime_config);

  OrderService order_service;
  GrpcOrderService grpc_service(order_service, runtime_config);

  grpc::ServerBuilder builder;
  ConfigureSyncServerBuilder(&builder, runtime_config);
  builder.AddListeningPort(listen_addr, grpc::InsecureServerCredentials());
  builder.RegisterService(&grpc_service);

  std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
  if (!server) {
    std::cerr << "failed to start Cerberus matching gRPC server on " << listen_addr << std::endl;
    return 1;
  }

  std::cout << "Cerberus matching gRPC server listening on " << listen_addr << std::endl;
  server->Wait();
  return 0;
}
