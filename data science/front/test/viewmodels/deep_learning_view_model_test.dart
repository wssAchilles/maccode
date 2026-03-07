import 'dart:async';

import 'package:flutter_test/flutter_test.dart';

import 'package:front/services/deep_learning_gateway.dart';
import 'package:front/viewmodels/deep_learning_view_model.dart';

class _FakeDeepLearningGateway implements DeepLearningGateway {
  Map<String, dynamic>? response;
  Object? error;
  Completer<Map<String, dynamic>>? completer;
  final List<Map<String, dynamic>> calls = <Map<String, dynamic>>[];

  @override
  Future<Map<String, dynamic>> trainModel({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    String? targetColumn,
  }) async {
    calls.add({
      'storagePath': storagePath,
      'modelType': modelType,
      'epochs': epochs,
      'batchSize': batchSize,
      'windowSize': windowSize,
      'targetColumn': targetColumn,
    });

    final pending = completer;
    if (pending != null) {
      return pending.future;
    }

    if (error != null) {
      throw error!;
    }

    if (response == null) {
      throw StateError('No fake response configured');
    }

    return response!;
  }
}

void main() {
  test('startTraining appends success logs and returns true', () async {
    final gateway = _FakeDeepLearningGateway()
      ..response = const {
        'metrics': {'rmse': 1.23},
      };

    final viewModel = DeepLearningViewModel(
      gateway: gateway,
      delay: (_) async {},
      clock: () => DateTime(2026, 1, 1, 12, 0, 0),
    );

    final success = await viewModel.startTraining(
      storagePath: 'demo.csv',
      modelType: 'lstm',
      epochs: 50,
      batchSize: 32,
      windowSize: 24,
      targetColumn: 'Load',
    );

    expect(success, isTrue);
    expect(viewModel.isTraining, isFalse);
    expect(gateway.calls.length, 1);
    expect(gateway.calls.first['storagePath'], 'demo.csv');
    expect(viewModel.trainLogs, contains('Initializing training environment'));
    expect(viewModel.trainLogs, contains('Training completed successfully!'));
    expect(viewModel.trainLogs, contains('Metrics: {rmse: 1.23}'));

    viewModel.dispose();
  });

  test(
    'startTraining appends error log and returns false on failure',
    () async {
      final gateway = _FakeDeepLearningGateway()..error = Exception('network');

      final viewModel = DeepLearningViewModel(
        gateway: gateway,
        delay: (_) async {},
        clock: () => DateTime(2026, 1, 1, 12, 0, 0),
      );

      final success = await viewModel.startTraining(
        storagePath: 'demo.csv',
        modelType: 'gru',
        epochs: 30,
        batchSize: 16,
        windowSize: 12,
      );

      expect(success, isFalse);
      expect(viewModel.isTraining, isFalse);
      expect(viewModel.trainLogs, contains('Error: Exception: network'));

      viewModel.dispose();
    },
  );

  test(
    'startTraining keeps isTraining true while request is in-flight',
    () async {
      final completer = Completer<Map<String, dynamic>>();
      final gateway = _FakeDeepLearningGateway()..completer = completer;

      final viewModel = DeepLearningViewModel(
        gateway: gateway,
        delay: (_) async {},
        clock: () => DateTime(2026, 1, 1, 12, 0, 0),
      );

      final pending = viewModel.startTraining(
        storagePath: 'demo.csv',
        modelType: 'lstm',
        epochs: 50,
        batchSize: 32,
        windowSize: 24,
      );

      expect(viewModel.isTraining, isTrue);

      completer.complete(const {'metrics': 'ok'});
      final success = await pending;

      expect(success, isTrue);
      expect(viewModel.isTraining, isFalse);

      viewModel.dispose();
    },
  );
}
