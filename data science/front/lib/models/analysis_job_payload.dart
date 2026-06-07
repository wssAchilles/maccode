library;

import 'job_record.dart';

class AnalysisJobPayload {
  const AnalysisJobPayload({required this.job});

  factory AnalysisJobPayload.fromJson(Map<String, dynamic> json) {
    return AnalysisJobPayload(job: JobRecord.fromJson(json));
  }

  final JobRecord job;
}
