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
}
