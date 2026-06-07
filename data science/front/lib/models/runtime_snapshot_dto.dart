library;

import 'shell_runtime_snapshot.dart';

class RuntimeSnapshotDto {
  const RuntimeSnapshotDto({required this.snapshot});

  factory RuntimeSnapshotDto.fromJson(Map<String, dynamic> json) {
    return RuntimeSnapshotDto(snapshot: ShellRuntimeSnapshot.fromJson(json));
  }

  final ShellRuntimeSnapshot snapshot;
}
