#pragma once

#include <string>

#include <grpcpp/grpcpp.h>

#include "grpc_order_service.hpp"

std::string ResolveListenAddress();
GrpcRuntimeConfig BuildRuntimeConfigFromEnv();
void ConfigureSyncServerBuilder(grpc::ServerBuilder* builder, const GrpcRuntimeConfig& cfg);
void LogRuntimeConfig(const std::string& listen_addr, const GrpcRuntimeConfig& cfg);
