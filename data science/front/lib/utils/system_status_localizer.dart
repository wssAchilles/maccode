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
    case 'Compute':
      return '计算';
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
  if (message == 'Compute acceleration telemetry active') {
    return '计算遥测运行正常';
  }
  if (message == 'Compute acceleration telemetry active (local snapshot)') {
    return '计算遥测已启用（本地快照）';
  }
  if (message ==
      'Compute acceleration telemetry is waiting for the first hotspot sample') {
    return '计算遥测正在等待首个热点样本';
  }
  if (message == 'Native compute backend is active') {
    return '原生计算后端已启用';
  }
  if (message.endsWith(' latency is still over budget')) {
    final prefix = message.substring(
      0,
      message.length - ' latency is still over budget'.length,
    );
    return '$prefix 延迟仍然超出预算';
  }
  if (message.endsWith(' shows recent latency spikes')) {
    final prefix = message.substring(
      0,
      message.length - ' shows recent latency spikes'.length,
    );
    return '$prefix 最近出现延迟尖峰';
  }

  return message;
}
