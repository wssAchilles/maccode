library;

import 'job_record.dart';

class OperationActionResult {
  const OperationActionResult({required this.operation});

  factory OperationActionResult.fromJson(Map<String, dynamic> json) {
    return OperationActionResult(operation: JobRecord.fromJson(json));
  }

  final JobRecord operation;
}
