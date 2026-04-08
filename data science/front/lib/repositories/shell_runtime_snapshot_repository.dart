library;

import 'dart:async';

import '../models/shell_runtime_snapshot.dart';
import '../services/api_service.dart';

abstract class ShellRuntimeSnapshotRepository {
  Future<ShellRuntimeSnapshot> getSnapshot({bool force = false});
}

class ApiShellRuntimeSnapshotRepository
    implements ShellRuntimeSnapshotRepository {
  const ApiShellRuntimeSnapshotRepository();

  static ShellRuntimeSnapshot? _cachedSnapshot;
  static DateTime? _cachedAt;
  static Future<ShellRuntimeSnapshot>? _inFlight;
  static const Duration _cacheTtl = Duration(seconds: 20);

  @override
  Future<ShellRuntimeSnapshot> getSnapshot({bool force = false}) async {
    if (!force) {
      final now = DateTime.now();
      if (_cachedSnapshot != null &&
          _cachedAt != null &&
          now.difference(_cachedAt!) < _cacheTtl) {
        return _cachedSnapshot!;
      }
      final inflight = _inFlight;
      if (inflight != null) {
        return inflight;
      }
    }

    final request = _loadSnapshot(force: force);
    _inFlight = request;
    try {
      return await request;
    } finally {
      if (identical(_inFlight, request)) {
        _inFlight = null;
      }
    }
  }

  Future<ShellRuntimeSnapshot> _loadSnapshot({required bool force}) async {
    final payload = await ApiService.getRuntimeSnapshot(fresh: force);
    final snapshot = ShellRuntimeSnapshot.fromJson(payload);
    _cachedSnapshot = snapshot;
    _cachedAt = DateTime.now();
    return snapshot;
  }
}
