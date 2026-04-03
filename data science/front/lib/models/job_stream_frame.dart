/// 作业流式帧模型
library;

import 'job_record.dart';

class JobStreamFrame {
  const JobStreamFrame({
    required this.event,
    required this.data,
    this.eventId,
  });

  final String event;
  final String? eventId;
  final Map<String, dynamic> data;

  bool get isSnapshot => event == 'operation.snapshot';
  bool get isState => event == 'operation.state';
  bool get isClosed => event == 'operation.closed';
  bool get isError => event == 'operation.error';

  bool get isJobEvent => !isSnapshot && !isState && !isClosed && !isError;

  JobRecord? get snapshot => isSnapshot ? JobRecord.fromJson(data) : null;

  JobEvent? get jobEvent => isJobEvent ? JobEvent.fromJson(data) : null;
}
