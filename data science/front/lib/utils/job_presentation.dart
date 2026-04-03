library;

import '../models/job_record.dart';

String buildJobPrimaryText(
  JobRecord job, {
  String fallback = '任务已提交',
}) {
  final statusMessage = _normalized(job.statusMessage);
  if (statusMessage != null && !_isGenericStatusMessage(job.status, statusMessage)) {
    return _translateKnownJobMessage(job, statusMessage) ?? statusMessage;
  }

  final latestEventMessage = _normalized(job.latestEvent?.message);
  if (job.status == 'running' && latestEventMessage != null) {
    return latestEventMessage;
  }

  switch (job.status) {
    case 'queued':
      return '${_jobLabel(job.type)}已排队';
    case 'awaiting_approval':
      return '${_jobLabel(job.type)}等待审批';
    case 'dispatching':
      return '${_jobLabel(job.type)}调度中';
    case 'retrying':
      return '${_jobLabel(job.type)}重试中';
    case 'running':
      return '${_jobLabel(job.type)}运行中';
    case 'succeeded':
      return '${_jobLabel(job.type)}已完成';
    case 'failed':
      return job.error?.message ?? '${_jobLabel(job.type)}失败';
    case 'cancelled':
      return '${_jobLabel(job.type)}已取消';
    default:
      return fallback;
  }
}

String buildJobEventMessage(JobRecord job, JobEvent event) {
  final eventMessage = _normalized(event.message);
  if (eventMessage != null && !_isGenericEventMessage(event, eventMessage)) {
    return _translateKnownJobMessage(job, eventMessage) ?? eventMessage;
  }

  final jobLabel = _jobLabel(job.type);
  switch (event.phase) {
    case 'approval':
      return '等待审批';
    case 'cancel':
      return '取消请求';
    case 'fetch_external_data':
      return '抓取外部数据';
    case 'prepare_dataset':
      return '准备数据集';
    case 'profile_dataset':
      return '生成数据画像';
    case 'run_quality_checks':
      return '执行质量检查';
    case 'run_stat_tests':
      return '执行统计检验';
    case 'train_forecast_model':
      return '训练预测模型';
    case 'evaluate_model':
      return '评估模型';
    case 'optimize_schedule':
      return '优化调度';
    case 'generate_report':
      return '生成报告';
    case 'publish_artifacts':
      return '发布产物';
    case 'ingest_knowledge_base':
      return '知识入库';
    case 'queued':
      return '$jobLabel已排队';
    case 'started':
      return '$jobLabel已启动';
    case 'dataset':
      return '加载任务数据';
    case 'basic_analysis':
      return '执行基础剖析';
    case 'model_metadata':
      return '同步模型元数据';
    case 'quality':
      return '执行质量检查';
    case 'correlation':
      return '计算相关性';
    case 'statistical':
      return '执行统计检验';
    case 'forecast':
      return '执行预测计算';
    case 'solver':
      return '执行优化求解';
    case 'aggregation':
      return '汇总任务结果';
    case 'explainability':
      return '生成解释性摘要';
    case 'sequencing':
      return '构建监督序列';
    case 'model_init':
      return '初始化模型结构';
    case 'training':
      return '执行模型训练';
    case 'artifact_upload':
      return '上传任务产物';
    case 'fetch_documents':
      return '抓取知识文档';
    case 'reset_collection':
      return '重建知识集合';
    case 'parsing':
      return '切分文档内容';
    case 'embedding':
      return '写入向量索引';
    case 'packaging':
      return '封装任务结果';
    case 'completed':
      return '$jobLabel已完成';
    case 'failed':
      return job.error?.message ?? '$jobLabel失败';
    default:
      return buildJobPrimaryText(job);
  }
}

String? _translateKnownJobMessage(JobRecord job, String message) {
  final normalized = message.toLowerCase();

  if (normalized.contains('loading training dataset')) {
    return '加载训练数据';
  }
  if (normalized.contains('preparing sequence data')) {
    return '准备序列数据';
  }
  if (normalized.contains('building supervised sequences')) {
    return '构建监督序列';
  }
  if (normalized.contains('initializing model architecture')) {
    return '初始化模型结构';
  }
  if (normalized.contains('tensorflow unavailable')) {
    return 'TensorFlow 不可用，已切换轻量回退训练后端';
  }
  if (normalized.contains('training fallback neural regressor')) {
    return '执行轻量回退训练';
  }
  if (normalized.contains('persisting trained model artifact')) {
    return '持久化训练产物';
  }
  if (normalized.contains('packaging training metrics and artifact metadata')) {
    return '封装训练指标与产物元数据';
  }
  if (normalized.contains('running ml_train')) {
    return '启动训练任务';
  }
  if (normalized.contains('fetching documents') ||
      normalized.contains('fetch documents') ||
      normalized.contains('fetching source documents')) {
    return '抓取源文档';
  }
  if (normalized.contains('resetting collection') ||
      normalized.contains('reset collection')) {
    return '重建知识集合';
  }
  if (normalized.contains('parsing documents') ||
      normalized.contains('splitting documents') ||
      normalized.contains('chunking documents')) {
    return '切分文档内容';
  }
  if (normalized.contains('embedding documents') ||
      normalized.contains('generating embeddings') ||
      normalized.contains('writing embeddings') ||
      normalized.contains('creating embeddings and persisting vectors')) {
    return '写入向量索引';
  }
  if (normalized.contains('packaging knowledge') ||
      normalized.contains('packaging ingest')) {
    return '封装知识库产物';
  }
  if (normalized.contains('running rag_ingest')) {
    return '启动知识库任务';
  }
  if (normalized.contains('running optimization')) {
    return '启动优化任务';
  }
  if (normalized.contains('predicting demand and pricing')) {
    return '预测负荷与电价';
  }
  if (normalized.contains('loading forecast model metadata')) {
    return '加载预测模型元数据';
  }
  if (normalized.contains('generating 24h demand and tariff forecast')) {
    return '生成 24 小时负荷与电价预测';
  }
  if (normalized.contains('aggregating schedule and cost summary')) {
    return '汇总调度与成本摘要';
  }
  if (normalized.contains('computing model explainability')) {
    return '计算模型解释性指标';
  }
  if (normalized.contains('packaging optimization result payload')) {
    return '封装优化结果产物';
  }
  if (normalized.contains('running analysis')) {
    return '启动分析任务';
  }
  if (normalized.contains('operation approved')) {
    return '任务已批准执行';
  }
  if (normalized.contains('operation rejected')) {
    return '任务已被拒绝';
  }
  if (normalized.contains('cancellation requested')) {
    return '已请求取消任务';
  }
  if (normalized.contains('artifact published')) {
    return '产物已发布';
  }

  if (normalized == 'running') {
    return '${_jobLabel(job.type)}运行中';
  }

  return null;
}

String _jobLabel(String type) {
  switch (type) {
    case 'analysis':
      return '分析任务';
    case 'optimization':
      return '优化任务';
    case 'ml_train':
      return '训练任务';
    case 'rag_ingest':
      return '知识库任务';
    case 'fetch_data':
      return '抓取任务';
    case 'train_model':
      return '重训任务';
    default:
      return '任务';
  }
}

String? _normalized(String? value) {
  final trimmed = value?.trim();
  if (trimmed == null || trimmed.isEmpty) {
    return null;
  }
  return trimmed;
}

bool _isGenericStatusMessage(String status, String message) {
  final normalizedStatus = status.trim().toLowerCase();
  final normalizedMessage = message.trim().toLowerCase();
  return normalizedMessage == normalizedStatus ||
      normalizedMessage == 'job completed' ||
      normalizedMessage == 'job queued' ||
      normalizedMessage == 'job failed' ||
      normalizedMessage == 'job cancelled' ||
      normalizedMessage == 'operation completed' ||
      normalizedMessage == 'operation created';
}

bool _isGenericEventMessage(JobEvent event, String message) {
  final normalizedMessage = message.trim().toLowerCase();
  return normalizedMessage == event.status.trim().toLowerCase() ||
      normalizedMessage == event.phase.trim().toLowerCase() ||
      normalizedMessage == 'job completed' ||
      normalizedMessage == 'job queued' ||
      normalizedMessage == 'job failed' ||
      normalizedMessage == 'job cancelled' ||
      normalizedMessage == 'operation completed' ||
      normalizedMessage == 'operation created';
}
