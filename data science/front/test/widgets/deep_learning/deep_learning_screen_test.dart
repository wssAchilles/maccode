import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/screens/deep_learning_screen.dart';
import 'package:front/services/deep_learning_gateway.dart';
import 'package:front/viewmodels/deep_learning_view_model.dart';

class _FakeDeepLearningGateway implements DeepLearningGateway {
  Map<String, dynamic>? response;
  Object? error;
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
  testWidgets('DeepLearningScreen stacks panels on narrow layouts and trains', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(500, 1200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final gateway = _FakeDeepLearningGateway()
      ..response = const {
        'metrics': {'rmse': 1.23},
      };
    final viewModel = DeepLearningViewModel(
      gateway: gateway,
      delay: (_) async {},
      clock: () => DateTime(2026, 1, 1, 12, 0, 0),
    );

    addTearDown(viewModel.dispose);

    await tester.pumpWidget(
      MaterialApp(
        home: DeepLearningScreen(
          viewModel: viewModel,
          storagePath: 'demo.csv',
        ),
      ),
    );

    expect(find.byKey(const ValueKey('deep-learning-layout-column')), findsOneWidget);
    expect(find.text('Ready to train...'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('deep-learning-run-button')));
    await tester.pump();
    await tester.pumpAndSettle();

    expect(gateway.calls, hasLength(1));
    expect(gateway.calls.first['storagePath'], 'demo.csv');
    expect(gateway.calls.first['modelType'], 'lstm');
    expect(find.textContaining('Training completed successfully!'), findsOneWidget);
    expect(find.text('Cloud training completed successfully.'), findsOneWidget);
  });

  testWidgets('DeepLearningScreen keeps wide two-column layout and shows failures', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final viewModel = DeepLearningViewModel(
      gateway: _FakeDeepLearningGateway()..error = Exception('network down'),
      delay: (_) async {},
      clock: () => DateTime(2026, 1, 1, 12, 0, 0),
    );

    addTearDown(viewModel.dispose);

    await tester.pumpWidget(
      MaterialApp(
        home: DeepLearningScreen(viewModel: viewModel),
      ),
    );

    expect(find.byKey(const ValueKey('deep-learning-layout-row')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('deep-learning-run-button')));
    await tester.pump();
    await tester.pumpAndSettle();

    expect(find.textContaining('Error: Exception: network down'), findsOneWidget);
    expect(
      find.text('Cloud training failed. Review the logs for details.'),
      findsOneWidget,
    );
  });
}
