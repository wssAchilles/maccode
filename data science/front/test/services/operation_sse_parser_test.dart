import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';

import 'package:front/services/operation_sse_parser.dart';

void main() {
  test('parseOperationSse decodes snapshot and event frames', () async {
    final raw = [
      'event: operation.snapshot',
      'id: snapshot-0',
      'data: {"job_id":"op-1","type":"analysis","status":"running","progress":10,"requested_by":"tester","attempt_count":1,"max_attempts":3}',
      '',
      'event: step.progress',
      'id: event-1',
      'data: {"type":"step.progress","phase":"prepare_dataset","status":"running","message":"Preparing dataset","progress":25}',
      '',
    ].join('\n');

    final frames = await parseOperationSse(
      Stream<List<int>>.fromIterable([utf8.encode(raw)]),
    ).toList();

    expect(frames, hasLength(2));
    expect(frames.first.event, 'operation.snapshot');
    expect(frames.first.snapshot?.jobId, 'op-1');
    expect(frames.last.event, 'step.progress');
    expect(frames.last.jobEvent?.phase, 'prepare_dataset');
  });

  test('parseOperationSse preserves normalized orchestrator taxonomy', () async {
    final raw = [
      'event: snapshot',
      'id: snapshot-0',
      'data: {"frame_type":"snapshot","correlation_id":"cp-1","operation_id":"op-1","event_type":"operation.snapshot","payload":{"job_id":"op-1","type":"analysis","status":"running","progress":10,"requested_by":"tester","attempt_count":1,"max_attempts":3}}',
      '',
      'event: event',
      'id: state-1',
      'data: {"frame_type":"event","correlation_id":"cp-1","operation_id":"op-1","event_type":"operation.state","payload":{"status":"running","progress":55,"current_step":{"phase":"generate_report","tool_name":"generate_report","status":"running","progress":55,"message":"Generating report"}}}',
      '',
    ].join('\n');

    final frames = await parseOperationSse(
      Stream<List<int>>.fromIterable([utf8.encode(raw)]),
    ).toList();

    expect(frames, hasLength(2));
    expect(frames.first.event, 'snapshot');
    expect(frames.first.snapshot?.jobId, 'op-1');
    expect(frames.last.event, 'event');
    expect(frames.last.isState, isTrue);
    expect(frames.last.payloadData['progress'], 55);
  });
}
