/// 数据漂移检测仓储
library;

import '../models/data_drift_report.dart';
import '../services/data_analysis_gateway.dart';

abstract class DataDriftRepository {
  Future<DataDriftReport> detectDrift({
    required String referencePath,
    required String currentPath,
    required List<String> features,
  });
}

class GatewayDataDriftRepository implements DataDriftRepository {
  GatewayDataDriftRepository({DataAnalysisGateway? gateway})
    : _gateway = gateway ?? ApiDataAnalysisGateway();

  final DataAnalysisGateway _gateway;

  @override
  Future<DataDriftReport> detectDrift({
    required String referencePath,
    required String currentPath,
    required List<String> features,
  }) async {
    final payload = await _gateway.detectDataDrift(
      referencePath: referencePath,
      currentPath: currentPath,
      features: features,
    );
    return DataDriftReport.fromJson(payload);
  }
}
