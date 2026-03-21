library;

String localizeSystemStatusLabel(String label) {
  switch (label) {
    case 'API':
      return '接口';
    case 'Model':
      return '模型';
    case 'Storage':
      return '存储';
    case 'RAG':
      return '知识库';
    default:
      return label;
  }
}

String localizeSystemStatusMessage(String message) {
  if (message.isEmpty) {
    return message;
  }

  if (message == 'Primary API is reachable') {
    return '主 API 服务可用';
  }
  if (message == 'Forecast model metadata available') {
    return '预测模型元数据已就绪';
  }
  if (message.startsWith('Bucket ready: ')) {
    return '存储桶已就绪：${message.substring('Bucket ready: '.length)}';
  }
  if (message == 'Knowledge service ready (TF-IDF fallback)') {
    return '知识服务已就绪（TF-IDF 回退）';
  }
  if (message == 'Knowledge service ready') {
    return '知识服务已就绪';
  }
  if (message == 'Model service ready') {
    return '模型服务已就绪';
  }

  return message;
}
