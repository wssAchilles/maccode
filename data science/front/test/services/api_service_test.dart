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

    test(
      'askRagQuestion surfaces backend message when success=false',
      () async {
        ApiService.setTokenProviderForTesting(() async => 'test-token');
        ApiService.setHttpClientForTesting(
          MockClient(
            (_) async => http.Response(
              jsonEncode(const {'success': false, 'message': 'quota exceeded'}),
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
      },
    );

    test('askRagQuestion unwraps nested result payload from backend', () async {
      ApiService.setTokenProviderForTesting(() async => 'test-token');
      ApiService.setHttpClientForTesting(
        MockClient(
          (_) async => http.Response(
            jsonEncode(const {
              'success': true,
              'collection': 'ops-knowledge',
              'result': {
                'answer': 'resolved',
                'context': [
                  {'filename': 'doc.txt'},
                ],
              },
            }),
            200,
            headers: {'content-type': 'application/json'},
          ),
        ),
      );

      final result = await ApiService.askRagQuestion(question: 'hello');

      expect(result['answer'], 'resolved');
      expect(result['collection'], 'ops-knowledge');
      expect(result['context'], isA<List<dynamic>>());
    });

    test(
      'runOptimization maps license failures even when body is plain text',
      () async {
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
      },
    );
  });

  group('ApiService operations API', () {
    test(
      'createOperation posts control-plane payload to operations endpoint',
      () async {
        late http.Request capturedRequest;

        ApiService.setTokenProviderForTesting(() async => 'test-token');
        ApiService.setHttpClientForTesting(
          MockClient((request) async {
            capturedRequest = request;
            return http.Response(
              jsonEncode(const {
                'success': true,
                'data': {
                  'job_id': 'op-1',
                  'operation_id': 'op-1',
                  'type': 'analysis',
                  'status': 'queued',
                  'progress': 0,
                  'requested_by': 'tester',
                  'attempt_count': 0,
                  'max_attempts': 3,
                },
              }),
              200,
              headers: {'content-type': 'application/json'},
            );
          }),
        );

        final result = await ApiService.createOperation(
          type: 'analysis',
          input: const {'storage_path': 'uploads/data.csv'},
          controlTaskId: 'analysis_manual',
          approvalPolicy: const {'required': false, 'mode': 'auto'},
          metadata: const {'source': 'test'},
        );

        final body = jsonDecode(capturedRequest.body) as Map<String, dynamic>;

        expect(capturedRequest.url.path, '/api/operations');
        expect(body['type'], 'analysis');
        expect(body['input']['storage_path'], 'uploads/data.csv');
        expect(body['control_task_id'], 'analysis_manual');
        expect(body['approval_policy']['mode'], 'auto');
        expect(body['metadata']['source'], 'test');
        expect(result['operation_id'], 'op-1');
      },
    );

    test(
      'getOperationEvents unwraps event list from operations endpoint',
      () async {
        ApiService.setTokenProviderForTesting(() async => 'test-token');
        ApiService.setHttpClientForTesting(
          MockClient(
            (_) async => http.Response(
              jsonEncode(const {
                'success': true,
                'data': {
                  'events': [
                    {
                      'type': 'step.started',
                      'phase': 'prepare_dataset',
                      'status': 'running',
                      'message': 'Preparing dataset',
                      'progress': 25,
                    },
                  ],
                },
              }),
              200,
              headers: {'content-type': 'application/json'},
            ),
          ),
        );

        final events = await ApiService.getOperationEvents('op-1');

        expect(events, hasLength(1));
        expect(events.single['type'], 'step.started');
        expect(events.single['phase'], 'prepare_dataset');
      },
    );
  });

  group('ApiService control tasks API', () {
    test('listControlTasks unwraps planning task list', () async {
      ApiService.setTokenProviderForTesting(() async => 'test-token');
      ApiService.setHttpClientForTesting(
        MockClient(
          (_) async => http.Response(
            jsonEncode(const {
              'success': true,
              'data': {
                'control_tasks': [
                  {
                    'id': 'fetch_data_hourly',
                    'kind': 'scheduler',
                    'title': '每小时抓取',
                    'enabled': true,
                  },
                ],
              },
            }),
            200,
            headers: {'content-type': 'application/json'},
          ),
        ),
      );

      final tasks = await ApiService.listControlTasks(kind: 'scheduler');

      expect(tasks, hasLength(1));
      expect(tasks.single['id'], 'fetch_data_hourly');
    });

    test('getControlTask unwraps planning task payload', () async {
      ApiService.setTokenProviderForTesting(() async => 'test-token');
      ApiService.setHttpClientForTesting(
        MockClient(
          (_) async => http.Response(
            jsonEncode(const {
              'success': true,
              'data': {
                'id': 'train_model_daily',
                'kind': 'scheduler',
                'title': '每日模型重训',
                'enabled': true,
              },
            }),
            200,
            headers: {'content-type': 'application/json'},
          ),
        ),
      );

      final task = await ApiService.getControlTask('train_model_daily');

      expect(task['id'], 'train_model_daily');
      expect(task['title'], '每日模型重训');
    });

    test('runControlTask posts trigger request to planning endpoint', () async {
      late http.Request capturedRequest;

      ApiService.setTokenProviderForTesting(() async => 'test-token');
      ApiService.setHttpClientForTesting(
        MockClient((request) async {
          capturedRequest = request;
          return http.Response(
            jsonEncode(const {
              'success': true,
              'data': {
                'job_id': 'op-9',
                'operation_id': 'op-9',
                'type': 'train_model',
                'status': 'queued',
                'progress': 0,
                'requested_by': 'tester',
                'attempt_count': 0,
                'max_attempts': 3,
              },
            }),
            202,
            headers: {'content-type': 'application/json'},
          );
        }),
      );

      final payload = await ApiService.runControlTask(
        'train_model_daily',
        trigger: 'manual',
        input: const {'n_estimators': 200},
      );

      final body = jsonDecode(capturedRequest.body) as Map<String, dynamic>;

      expect(
        capturedRequest.url.path,
        '/api/control-tasks/train_model_daily/run',
      );
      expect(body['trigger'], 'manual');
      expect(body['input']['n_estimators'], 200);
      expect(payload['operation_id'], 'op-9');
    });

    test(
      'setControlTaskEnabled patches enabled flag to planning endpoint',
      () async {
        late http.Request capturedRequest;

        ApiService.setTokenProviderForTesting(() async => 'test-token');
        ApiService.setHttpClientForTesting(
          MockClient((request) async {
            capturedRequest = request;
            return http.Response(
              jsonEncode(const {
                'success': true,
                'data': {
                  'id': 'train_model_daily',
                  'kind': 'scheduler',
                  'operation_type': 'train_model',
                  'title': '每日模型重训',
                  'enabled': false,
                },
              }),
              202,
              headers: {'content-type': 'application/json'},
            );
          }),
        );

        final payload = await ApiService.setControlTaskEnabled(
          'train_model_daily',
          enabled: false,
        );

        final body = jsonDecode(capturedRequest.body) as Map<String, dynamic>;

        expect(capturedRequest.method, 'PATCH');
        expect(
          capturedRequest.url.path,
          '/api/control-tasks/train_model_daily',
        );
        expect(body['enabled'], isFalse);
        expect(payload['enabled'], isFalse);
      },
    );

    test(
      'setControlTaskApprovalPolicy patches approval policy to planning endpoint',
      () async {
        late http.Request capturedRequest;

        ApiService.setTokenProviderForTesting(() async => 'test-token');
        ApiService.setHttpClientForTesting(
          MockClient((request) async {
            capturedRequest = request;
            return http.Response(
              jsonEncode(const {
                'success': true,
                'data': {
                  'id': 'train_model_daily',
                  'kind': 'scheduler',
                  'operation_type': 'train_model',
                  'title': '每日模型重训',
                  'enabled': true,
                  'approval_policy': {'required': true, 'mode': 'manual'},
                },
              }),
              202,
              headers: {'content-type': 'application/json'},
            );
          }),
        );

        final payload = await ApiService.setControlTaskApprovalPolicy(
          'train_model_daily',
          approvalPolicy: const {'required': true, 'mode': 'manual'},
        );

        final body = jsonDecode(capturedRequest.body) as Map<String, dynamic>;

        expect(capturedRequest.method, 'PATCH');
        expect(body['approval_policy']['required'], isTrue);
        expect(body['approval_policy']['mode'], 'manual');
        expect(payload['approval_policy']['mode'], 'manual');
      },
    );

    test(
      'updateControlTaskDefinition patches schedule owner and default input',
      () async {
        late http.Request capturedRequest;

        ApiService.setTokenProviderForTesting(() async => 'test-token');
        ApiService.setHttpClientForTesting(
          MockClient((request) async {
            capturedRequest = request;
            return http.Response(
              jsonEncode(const {
                'success': true,
                'data': {
                  'id': 'train_model_daily',
                  'kind': 'scheduler',
                  'operation_type': 'train_model',
                  'title': '每日模型重训',
                  'schedule': 'every day 05:00 UTC',
                  'owner': 'mlops',
                  'dependencies': ['dataset_ready', 'weather_ready'],
                  'approval_policy': {
                    'required': true,
                    'mode': 'manual',
                    'reason': '高成本重训需要审批',
                  },
                  'default_input': {'window_days': 60},
                },
              }),
              202,
              headers: {'content-type': 'application/json'},
            );
          }),
        );

        final payload = await ApiService.updateControlTaskDefinition(
          'train_model_daily',
          schedule: 'every day 05:00 UTC',
          owner: 'mlops',
          dependencies: const ['dataset_ready', 'weather_ready'],
          approvalPolicy: const {
            'required': true,
            'mode': 'manual',
            'reason': '高成本重训需要审批',
          },
          defaultInput: const {'window_days': 60},
        );

        final body = jsonDecode(capturedRequest.body) as Map<String, dynamic>;

        expect(capturedRequest.method, 'PATCH');
        expect(body['schedule'], 'every day 05:00 UTC');
        expect(body['owner'], 'mlops');
        expect(body['dependencies'], ['dataset_ready', 'weather_ready']);
        expect(body['approval_policy']['reason'], '高成本重训需要审批');
        expect(body['default_input']['window_days'], 60);
        expect(payload['owner'], 'mlops');
        expect(payload['dependencies'], ['dataset_ready', 'weather_ready']);
      },
    );
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
