import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:front/services/api_service.dart';
import 'package:front/services/api_service_exception.dart';

void main() {
  tearDown(() {
    ApiService.resetTestingOverrides();
  });

  group('ApiService.analyzeCsv', () {
    test('includes save_to_storage=true by default', () async {
      late http.Request capturedRequest;

      ApiService.setTokenProviderForTesting(() async => 'test-token');
      ApiService.setHttpClientForTesting(
        MockClient((request) async {
          capturedRequest = request;
          return http.Response(
            jsonEncode(_successResponsePayload),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      );

      final result = await ApiService.analyzeCsv(
        storagePath: 'uploads/sample.csv',
        filename: 'sample.csv',
      );

      final body = jsonDecode(capturedRequest.body) as Map<String, dynamic>;

      expect(body['save_to_storage'], isTrue);
      expect(result.basicInfo.rows, 1);
      expect(result.preview, isNotEmpty);
    });

    test('includes save_to_storage=false when disabled', () async {
      late http.Request capturedRequest;

      ApiService.setTokenProviderForTesting(() async => 'test-token');
      ApiService.setHttpClientForTesting(
        MockClient((request) async {
          capturedRequest = request;
          return http.Response(
            jsonEncode(_successResponsePayload),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      );

      await ApiService.analyzeCsv(
        storagePath: 'uploads/sample.csv',
        filename: 'sample.csv',
        saveToStorage: false,
      );

      final body = jsonDecode(capturedRequest.body) as Map<String, dynamic>;

      expect(body['save_to_storage'], isFalse);
    });
  });

  group('ApiService error normalization', () {
    test('trainModel normalizes plain-text server errors', () async {
      ApiService.setTokenProviderForTesting(() async => 'test-token');
      ApiService.setHttpClientForTesting(
        MockClient((_) async => http.Response('upstream crash', 500)),
      );

      await expectLater(
        ApiService.trainModel(
          storagePath: 'uploads/sample.csv',
          problemType: 'classification',
        ),
        throwsA(
          isA<ApiServiceException>().having(
            (e) => e.message,
            'message',
            contains('Training failed: upstream crash'),
          ),
        ),
      );
    });

    test('askRagQuestion surfaces backend message when success=false', () async {
      ApiService.setTokenProviderForTesting(() async => 'test-token');
      ApiService.setHttpClientForTesting(
        MockClient(
          (_) async => http.Response(
            jsonEncode(const {
              'success': false,
              'message': 'quota exceeded',
            }),
            200,
            headers: {'content-type': 'application/json'},
          ),
        ),
      );

      await expectLater(
        ApiService.askRagQuestion(question: 'hello'),
        throwsA(
          isA<ApiServiceException>().having(
            (e) => e.message,
            'message',
            contains('quota exceeded'),
          ),
        ),
      );
    });

    test('runOptimization maps license failures even when body is plain text', () async {
      ApiService.setTokenProviderForTesting(() async => 'test-token');
      ApiService.setHttpClientForTesting(
        MockClient((_) async => http.Response('license expired', 500)),
      );

      await expectLater(
        ApiService.runOptimization(),
        throwsA(
          isA<ApiServiceException>().having(
            (e) => e.message,
            'message',
            contains('许可证错误'),
          ),
        ),
      );
    });
  });

  test(
    'throws unauthenticated error when test token provider returns null',
    () async {
      ApiService.setTokenProviderForTesting(() async => null);
      ApiService.setHttpClientForTesting(
        MockClient((_) async => http.Response('{}', 200)),
      );

      await expectLater(
        ApiService.getUserProfile(),
        throwsA(
          isA<ApiServiceException>().having(
            (e) => e.message,
            'message',
            contains('User not authenticated'),
          ),
        ),
      );
    },
  );
}

const Map<String, dynamic> _successResponsePayload = {
  'success': true,
  'analysis_result': {
    'basic_info': {
      'rows': 1,
      'columns': 1,
      'column_names': ['value'],
      'column_types': {'value': 'int64'},
    },
    'preview': [
      {'value': 42},
    ],
  },
};
