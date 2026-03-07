/// 能源优化网关接口
library;

import '../models/optimization_result.dart';
import 'api_client.dart';

abstract class OptimizationGateway {
  Future<OptimizationResponse> runOptimization({
    double initialSoc = 0.5,
    DateTime? targetDate,
    double? temperatureAdjust,
    double? batteryCapacity,
    double? batteryPower,
  });
}

class ApiOptimizationGateway implements OptimizationGateway {
  ApiOptimizationGateway({ApiClient? apiClient})
    : _apiClient = apiClient ?? const DefaultApiClient();

  final ApiClient _apiClient;

  @override
  Future<OptimizationResponse> runOptimization({
    double initialSoc = 0.5,
    DateTime? targetDate,
    double? temperatureAdjust,
    double? batteryCapacity,
    double? batteryPower,
  }) {
    return _apiClient.runOptimization(
      initialSoc: initialSoc,
      targetDate: targetDate,
      temperatureAdjust: temperatureAdjust,
      batteryCapacity: batteryCapacity,
      batteryPower: batteryPower,
    );
  }
}
