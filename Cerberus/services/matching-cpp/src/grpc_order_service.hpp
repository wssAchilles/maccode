#pragma once

#include <atomic>
#include <chrono>
#include <cstdint>
#include <deque>
#include <mutex>
#include <string>

#include <grpcpp/grpcpp.h>

#include "cerberus/order/v1/order.grpc.pb.h"
#include "order_service.hpp"

class GrpcOrderService final : public cerberus::order::v1::OrderService::Service {
 public:
  explicit GrpcOrderService(OrderService& service);

  grpc::Status SubmitOrder(grpc::ServerContext* context,
                           const cerberus::order::v1::SubmitOrderRequest* request,
                           cerberus::order::v1::SubmitOrderResponse* response) override;

  grpc::Status CancelOrder(grpc::ServerContext* context,
                           const cerberus::order::v1::CancelOrderRequest* request,
                           cerberus::order::v1::CancelOrderResponse* response) override;

  grpc::Status GetOrder(grpc::ServerContext* context,
                        const cerberus::order::v1::GetOrderRequest* request,
                        cerberus::order::v1::GetOrderResponse* response) override;

  grpc::Status GetOrderBook(
      grpc::ServerContext* context, const cerberus::order::v1::GetOrderBookRequest* request,
      cerberus::order::v1::GetOrderBookResponse* response) override;

  grpc::Status StreamExecutions(
      grpc::ServerContext* context,
      const cerberus::order::v1::StreamExecutionsRequest* request,
      grpc::ServerWriter<cerberus::order::v1::StreamExecutionsResponse>* writer) override;

  grpc::Status Health(grpc::ServerContext* context, const cerberus::order::v1::HealthRequest* request,
                      cerberus::order::v1::HealthResponse* response) override;

  grpc::Status GetServiceStats(
      grpc::ServerContext* context, const cerberus::order::v1::GetServiceStatsRequest* request,
      cerberus::order::v1::GetServiceStatsResponse* response) override;

 private:
  static Side ToDomainSide(cerberus::order::v1::Side side, bool& ok);
  static cerberus::order::v1::Side ToProtoSide(Side side);
  static cerberus::order::v1::OrderStatus ToProtoStatus(OrderStatus status);
  static void FillNowTimestamp(google::protobuf::Timestamp* ts);
  std::string NextGeneratedOrderId(const std::string& account_id);
  bool IsDegraded() const;
  std::string DegradedStatusText() const;
  std::string EffectiveSchemaVersion(const std::string& requested_schema) const;
  std::string EffectiveCorrelationId(
      grpc::ServerContext* context, const std::string& requested_correlation_id) const;
  void FillResponseContext(grpc::ServerContext* context, const std::string& requested_schema,
                           const std::string& requested_correlation_id,
                           std::string* response_schema,
                           std::string* response_correlation) const;
  void MarkDegraded(grpc::ServerContext* context, const std::string& reason) const;
  grpc::Status FinalizeSubmitStatus(
      grpc::Status status, bool accepted,
      const std::chrono::steady_clock::time_point& started_at);
  void RecordSubmitLatencyMs(std::uint64_t latency_ms);
  double SubmitOrderLatencyP95Ms() const;
  double SubmitOrderThroughputRps() const;
  std::uint64_t UptimeSeconds() const;

  OrderService& service_;
  std::mutex mu_;
  std::atomic_uint64_t next_sequence_{1};
  std::atomic_uint64_t next_generated_order_id_{1};
  std::chrono::steady_clock::time_point started_at_;
  std::string service_version_;
  bool force_degraded_{false};
  std::string degraded_reason_;
  std::string schema_version_;
  std::size_t execution_stream_limit_{500};
  std::size_t submit_latency_window_size_{1024};
  std::atomic_uint64_t submit_order_requests_total_{0};
  std::atomic_uint64_t submit_order_errors_total_{0};
  std::atomic_uint64_t submit_order_rejections_total_{0};
  mutable std::mutex submit_latency_mu_;
  std::deque<std::uint64_t> submit_latency_samples_ms_;
};
