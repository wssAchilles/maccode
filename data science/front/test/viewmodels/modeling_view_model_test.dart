import 'dart:async';

import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/optimization_result.dart';
import 'package:front/services/optimization_gateway.dart';
import 'package:front/viewmodels/modeling_view_model.dart';

class _FakeOptimizationGateway implements OptimizationGateway {
  OptimizationResponse? response;
  Object? error;
  Completer<OptimizationResponse>? completer;
  final List<Map<String, dynamic>> calls = <Map<String, dynamic>>[];

  @override
  Future<OptimizationResponse> runOptimization({
    double initialSoc = 0.5,
    DateTime? targetDate,
    double? temperatureAdjust,
    double? batteryCapacity,
    double? batteryPower,
  }) async {
    calls.add({
      'initialSoc': initialSoc,
      'targetDate': targetDate,
      'temperatureAdjust': temperatureAdjust,
      'batteryCapacity': batteryCapacity,
      'batteryPower': batteryPower,
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

OptimizationResponse _buildResponse({
  required bool success,
  double savings = 100,
  String? message,
  String? error,
}) {
  return OptimizationResponse.fromJson({
    'success': success,
    ...?message == null ? null : <String, dynamic>{'message': message},
    ...?error == null ? null : <String, dynamic>{'error': error},
    'optimization': <String, dynamic>{
      'status': success ? 'Optimal' : 'Failed',
      'chart_data': <dynamic>[],
      'summary': <String, dynamic>{'savings': savings},
      'strategy': <String, dynamic>{},
    },
  });
}

void main() {
  test('runOptimization stores successful result and clears error', () async {
    final gateway = _FakeOptimizationGateway()
      ..response = _buildResponse(success: true, savings: 123.4);
    final viewModel = ModelingViewModel(gateway: gateway);

    final result = await viewModel.runOptimization(
      initialSoc: 0.6,
      batteryCapacity: 500,
      batteryPower: 200,
      temperatureAdjust: 1.5,
    );

    expect(result, isNotNull);
    expect(result!.isSuccess, isTrue);
    expect(viewModel.result, isNotNull);
    expect(viewModel.errorMessage, isNull);
    expect(viewModel.isLoading, isFalse);
    expect(gateway.calls.length, 1);
    expect(gateway.calls.first['initialSoc'], 0.6);

    viewModel.dispose();
  });

  test('runOptimization exposes backend failure message', () async {
    final gateway = _FakeOptimizationGateway()
      ..response = _buildResponse(success: false, message: 'solver failed');
    final viewModel = ModelingViewModel(gateway: gateway);

    final result = await viewModel.runOptimization(initialSoc: 0.5);

    expect(result, isNotNull);
    expect(result!.isSuccess, isFalse);
    expect(viewModel.result, isNotNull);
    expect(viewModel.errorMessage, contains('solver failed'));

    viewModel.dispose();
  });

  test('runOptimization captures exception as errorMessage', () async {
    final gateway = _FakeOptimizationGateway()..error = Exception('network');
    final viewModel = ModelingViewModel(gateway: gateway);

    final result = await viewModel.runOptimization(initialSoc: 0.5);

    expect(result, isNull);
    expect(viewModel.result, isNull);
    expect(viewModel.errorMessage, contains('network'));
    expect(viewModel.isLoading, isFalse);

    viewModel.dispose();
  });

  test('saveForComparison keeps previous successful result', () async {
    final gateway = _FakeOptimizationGateway()
      ..response = _buildResponse(success: true, savings: 100);
    final viewModel = ModelingViewModel(gateway: gateway);

    await viewModel.runOptimization(initialSoc: 0.5);

    gateway.response = _buildResponse(success: true, savings: 150);
    await viewModel.runOptimization(initialSoc: 0.55, saveForComparison: true);

    expect(viewModel.previousResult, isNotNull);
    expect(viewModel.previousResult!.optimization!.summary.savings, 100);
    expect(viewModel.result!.optimization!.summary.savings, 150);

    viewModel.dispose();
  });

  test('runOptimization exposes loading during in-flight request', () async {
    final completer = Completer<OptimizationResponse>();
    final gateway = _FakeOptimizationGateway()..completer = completer;
    final viewModel = ModelingViewModel(gateway: gateway);

    final pending = viewModel.runOptimization(initialSoc: 0.5);
    expect(viewModel.isLoading, isTrue);

    completer.complete(_buildResponse(success: true, savings: 99));
    final result = await pending;

    expect(result, isNotNull);
    expect(viewModel.isLoading, isFalse);

    viewModel.dispose();
  });
}
