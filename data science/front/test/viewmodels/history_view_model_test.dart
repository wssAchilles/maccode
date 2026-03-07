import 'dart:async';

import 'package:flutter_test/flutter_test.dart';

import 'package:front/services/history_gateway.dart';
import 'package:front/viewmodels/history_view_model.dart';

class _FakeHistoryGateway implements HistoryGateway {
  List<Map<String, dynamic>> historyPayload = const [];
  Object? getHistoryError;
  Object? deleteError;
  final List<String> deletedIds = <String>[];
  Completer<void>? deleteCompleter;

  @override
  Future<List<Map<String, dynamic>>> getUserHistory({int limit = 50}) async {
    if (getHistoryError != null) {
      throw getHistoryError!;
    }
    return historyPayload;
  }

  @override
  Future<void> deleteHistoryRecord(String recordId) async {
    deletedIds.add(recordId);

    final completer = deleteCompleter;
    if (completer != null) {
      await completer.future;
      return;
    }

    if (deleteError != null) {
      throw deleteError!;
    }
  }
}

void main() {
  test('loadHistory populates records when gateway succeeds', () async {
    final gateway = _FakeHistoryGateway()
      ..historyPayload = const [
        {
          'id': 'r1',
          'filename': 'energy.csv',
          'quality_score': 82.5,
          'created_at': '2026-03-06T08:00:00Z',
        },
      ];

    final viewModel = HistoryViewModel(gateway: gateway);

    await viewModel.loadHistory();

    expect(viewModel.isLoading, isFalse);
    expect(viewModel.errorMessage, isNull);
    expect(viewModel.records.length, 1);
    expect(viewModel.records.first.id, 'r1');
    expect(viewModel.records.first.filename, 'energy.csv');
    expect(viewModel.records.first.qualityScore, 82.5);

    viewModel.dispose();
  });

  test('loadHistory exposes error when gateway fails', () async {
    final gateway = _FakeHistoryGateway()..getHistoryError = Exception('boom');
    final viewModel = HistoryViewModel(gateway: gateway);

    await viewModel.loadHistory();

    expect(viewModel.isLoading, isFalse);
    expect(viewModel.records, isEmpty);
    expect(viewModel.errorMessage, contains('加载失败'));

    viewModel.dispose();
  });

  test('deleteRecord removes record on success', () async {
    final gateway = _FakeHistoryGateway()
      ..historyPayload = const [
        {'id': 'r1', 'filename': 'a.csv'},
        {'id': 'r2', 'filename': 'b.csv'},
      ];
    final viewModel = HistoryViewModel(gateway: gateway);

    await viewModel.loadHistory();
    final success = await viewModel.deleteRecord('r1');

    expect(success, isTrue);
    expect(gateway.deletedIds, ['r1']);
    expect(viewModel.records.map((e) => e.id), ['r2']);
    expect(viewModel.errorMessage, isNull);

    viewModel.dispose();
  });

  test('deleteRecord returns false and keeps records on failure', () async {
    final gateway = _FakeHistoryGateway()
      ..historyPayload = const [
        {'id': 'r1', 'filename': 'a.csv'},
      ]
      ..deleteError = Exception('cannot delete');
    final viewModel = HistoryViewModel(gateway: gateway);

    await viewModel.loadHistory();
    final success = await viewModel.deleteRecord('r1');

    expect(success, isFalse);
    expect(viewModel.records.length, 1);
    expect(viewModel.errorMessage, contains('删除失败'));

    viewModel.dispose();
  });

  test(
    'deleteRecord exposes deleting state while request is in-flight',
    () async {
      final completer = Completer<void>();
      final gateway = _FakeHistoryGateway()
        ..historyPayload = const [
          {'id': 'r1', 'filename': 'a.csv'},
        ]
        ..deleteCompleter = completer;
      final viewModel = HistoryViewModel(gateway: gateway);

      await viewModel.loadHistory();

      final deleteFuture = viewModel.deleteRecord('r1');
      expect(viewModel.isDeleting('r1'), isTrue);

      completer.complete();
      final success = await deleteFuture;

      expect(success, isTrue);
      expect(viewModel.isDeleting('r1'), isFalse);

      viewModel.dispose();
    },
  );
}
