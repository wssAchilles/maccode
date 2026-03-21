import 'package:flutter_test/flutter_test.dart';

import 'package:front/utils/system_status_localizer.dart';

void main() {
  test('localizeSystemStatusLabel translates known status labels', () {
    expect(localizeSystemStatusLabel('API'), '接口');
    expect(localizeSystemStatusLabel('Storage'), '存储');
    expect(localizeSystemStatusLabel('RAG'), '知识库');
  });

  test('localizeSystemStatusMessage translates known backend messages', () {
    expect(localizeSystemStatusMessage('Primary API is reachable'), '主 API 服务可用');
    expect(
      localizeSystemStatusMessage(
        'Knowledge service ready (TF-IDF fallback)',
      ),
      '知识服务已就绪（TF-IDF 回退）',
    );
    expect(
      localizeSystemStatusMessage(
        'Bucket ready: data-science-44398.firebasestorage.app',
      ),
      '存储桶已就绪：data-science-44398.firebasestorage.app',
    );
  });
}
