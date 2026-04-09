/// 作业流式帧模型
library;

import 'job_record.dart';

class JobStreamFrame {
  const JobStreamFrame({required this.event, required this.data, this.eventId});

  final String event;
  final String? eventId;
  final Map<String, dynamic> data;

  String? get upstreamEventType =>
      (data['event_type'] ?? data['type'])?.toString();

  Map<String, dynamic> get payloadData {
    final payload = data['payload'];
    if (payload is Map<String, dynamic>) {
      return payload;
    }
    if (payload is Map) {
      return Map<String, dynamic>.from(payload);
    }
    return data;
  }

  bool get isSnapshot => event == 'operation.snapshot' || event == 'snapshot';
  bool get isState =>
      event == 'operation.state' ||
      (event == 'event' && upstreamEventType == 'operation.state');
  bool get isClosed => event == 'operation.closed' || event == 'closed';
  bool get isError => event == 'operation.error' || event == 'error';
  bool get isHeartbeat => event == 'heartbeat';

  bool get isJobEvent =>
      !isSnapshot && !isState && !isClosed && !isError && !isHeartbeat;

  JobRecord? get snapshot =>
      isSnapshot ? JobRecord.fromJson(payloadData) : null;

  JobEvent? get jobEvent {
    if (!isJobEvent) {
      return null;
    }
    final eventPayload = <String, dynamic>{
      ...payloadData,
      if (!payloadData.containsKey('type') && upstreamEventType != null)
        'type': upstreamEventType,
    };
    return JobEvent.fromJson(eventPayload);
  }
}
