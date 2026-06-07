/// SSE 解析器
library;

import 'dart:convert';

import '../models/job_stream_frame.dart';

Stream<JobStreamFrame> parseOperationSse(Stream<List<int>> byteStream) async* {
  String? currentEvent;
  String? currentId;
  final dataLines = <String>[];

  await for (final line
      in byteStream.transform(utf8.decoder).transform(const LineSplitter())) {
    if (line.isEmpty) {
      final frame = _flushFrame(
        currentEvent: currentEvent,
        currentId: currentId,
        dataLines: dataLines,
      );
      if (frame != null) {
        yield frame;
      }
      currentEvent = null;
      currentId = null;
      dataLines.clear();
      continue;
    }

    if (line.startsWith(':')) {
      continue;
    }

    if (line.startsWith('event:')) {
      currentEvent = line.substring('event:'.length).trim();
      continue;
    }
    if (line.startsWith('id:')) {
      currentId = line.substring('id:'.length).trim();
      continue;
    }
    if (line.startsWith('data:')) {
      dataLines.add(line.substring('data:'.length).trimLeft());
    }
  }

  final frame = _flushFrame(
    currentEvent: currentEvent,
    currentId: currentId,
    dataLines: dataLines,
  );
  if (frame != null) {
    yield frame;
  }
}

JobStreamFrame? _flushFrame({
  required String? currentEvent,
  required String? currentId,
  required List<String> dataLines,
}) {
  if ((currentEvent == null || currentEvent.isEmpty) && dataLines.isEmpty) {
    return null;
  }

  final rawData = dataLines.join('\n').trim();
  final payload = rawData.isEmpty
      ? const <String, dynamic>{}
      : _decodePayload(rawData);

  return JobStreamFrame(
    event: currentEvent == null || currentEvent.isEmpty
        ? 'operation.event'
        : currentEvent,
    eventId: currentId,
    data: payload,
  );
}

Map<String, dynamic> _decodePayload(String rawData) {
  final decoded = jsonDecode(rawData);
  if (decoded is Map<String, dynamic>) {
    return decoded;
  }
  if (decoded is Map) {
    return Map<String, dynamic>.from(decoded);
  }
  return <String, dynamic>{'value': decoded};
}
