/// 深度学习页面 ViewModel
library;

import 'package:flutter/foundation.dart';

import '../services/deep_learning_gateway.dart';

class DeepLearningViewModel extends ChangeNotifier {
  DeepLearningViewModel({
    DeepLearningGateway? gateway,
    Future<void> Function(Duration)? delay,
    DateTime Function()? clock,
  }) : _gateway = gateway ?? ApiDeepLearningGateway(),
       _delay = delay ?? Future<void>.delayed,
       _clock = clock ?? DateTime.now;

  final DeepLearningGateway _gateway;
  final Future<void> Function(Duration) _delay;
  final DateTime Function() _clock;

  bool _isTraining = false;
  String _trainLogs = '';
  bool _isDisposed = false;

  bool get isTraining => _isTraining;
  String get trainLogs => _trainLogs;

  Future<bool> startTraining({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    String? targetColumn,
  }) async {
    if (_isTraining) {
      return false;
    }

    _isTraining = true;
    _trainLogs = 'Initializing training environment on Cloud Run...\n';
    _notifySafely();

    _appendLog('Allocating resources (4 CPU, 8GB RAM)...');
    await _delay(const Duration(milliseconds: 800));
    _appendLog('Loading heavy libraries (TensorFlow 2.15.0)...');

    try {
      final result = await _gateway.trainModel(
        storagePath: storagePath,
        modelType: modelType,
        epochs: epochs,
        batchSize: batchSize,
        windowSize: windowSize,
        targetColumn: targetColumn,
      );

      _appendLog('Training completed successfully!');
      _appendLog('Metrics: ${result['metrics']}');
      return true;
    } catch (e) {
      _appendLog('Error: $e');
      return false;
    } finally {
      _isTraining = false;
      _notifySafely();
    }
  }

  void _appendLog(String log) {
    final timestamp = _clock().toIso8601String().substring(11, 19);
    _trainLogs += '[$timestamp] $log\n';
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
