#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>

#include <grpcpp/grpcpp.h>

#include "grpc_order_service.hpp"
#include "order_service.hpp"

int main() {
  const char* port_env = std::getenv("PORT");
  const std::string port = (port_env != nullptr && *port_env != '\0') ? port_env : "50051";
  const std::string listen_addr = "0.0.0.0:" + port;

  OrderService order_service;
  GrpcOrderService grpc_service(order_service);

  grpc::ServerBuilder builder;
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
