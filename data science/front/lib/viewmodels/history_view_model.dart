/// 历史记录页面 ViewModel
library;

import 'package:flutter/foundation.dart';

import '../models/history_record.dart';
import '../services/history_gateway.dart';

class HistoryViewModel extends ChangeNotifier {
  HistoryViewModel({HistoryGateway? gateway})
    : _gateway = gateway ?? ApiHistoryGateway();

  final HistoryGateway _gateway;

  List<HistoryRecord> _records = const [];
  bool _isLoading = false;
  String? _errorMessage;
  final Set<String> _deletingRecordIds = <String>{};
  bool _isDisposed = false;

  List<HistoryRecord> get records => List.unmodifiable(_records);
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  bool isDeleting(String recordId) => _deletingRecordIds.contains(recordId);

  Future<void> initialize() => loadHistory();

  Future<void> loadHistory({int limit = 50}) async {
    _isLoading = true;
    _errorMessage = null;
    _notifySafely();

    try {
      final rawRecords = await _gateway.getUserHistory(limit: limit);
      _records = rawRecords.map(HistoryRecord.fromJson).toList();
    } catch (e) {
      _errorMessage = '加载失败: $e';
    } finally {
      _isLoading = false;
      _notifySafely();
    }
  }

  Future<bool> deleteRecord(String recordId) async {
    if (recordId.isEmpty || _deletingRecordIds.contains(recordId)) {
      return false;
    }

    _deletingRecordIds.add(recordId);
    _errorMessage = null;
    _notifySafely();

    try {
      await _gateway.deleteHistoryRecord(recordId);
      _records = _records.where((record) => record.id != recordId).toList();
      return true;
    } catch (e) {
      _errorMessage = '删除失败: $e';
      return false;
    } finally {
      _deletingRecordIds.remove(recordId);
      _notifySafely();
    }
  }

  void clearError() {
    _errorMessage = null;
    _notifySafely();
  }

  void _notifySafely() {
    if (!_isDisposed) {
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    super.dispose();
  }
}
