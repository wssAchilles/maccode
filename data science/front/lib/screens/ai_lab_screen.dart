/// AI Lab 工作台
library;

import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../config/app_theme.dart';
import '../models/ai_lab_launch_intent.dart';
import '../models/dashboard_summary.dart';
import '../models/deep_learning_config_state.dart';
import '../models/job_record.dart';
import '../models/workbench_launch_context.dart';
import '../utils/asset_chain_context.dart';
import '../utils/job_presentation.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../viewmodels/job_view_model.dart';
import '../viewmodels/rag_view_model.dart';
import '../widgets/common/glass_card.dart';
import '../widgets/deep_learning/deep_learning_config_panel.dart';
import '../widgets/deep_learning/deep_learning_terminal_panel.dart';
import '../widgets/navigation/main_shell_runtime_scope.dart';
import '../widgets/operations/ai_lab_operations_board.dart';
import '../widgets/operations/ai_lab_asset_control_board.dart';
import '../widgets/operations/embedded_page_header.dart';
import '../widgets/operations/job_activity_list.dart';
import '../widgets/operations/job_event_timeline.dart';
import '../widgets/operations/lab_split_panel.dart';
import '../widgets/operations/workbench_page_frame.dart';
import '../widgets/operations/workbench_command_strip.dart';
import '../widgets/operations/workbench_runbook_panel.dart';
import '../widgets/operations/workbench_section_signal.dart';
import '../widgets/operations/workspace_action_lane.dart';
import '../widgets/rag/rag_input_area.dart';
import '../widgets/rag/rag_message_list.dart';
import '../widgets/responsive_wrapper.dart';

class AiLabScreen extends StatefulWidget {
  const AiLabScreen({
    super.key,
    required this.dashboardViewModel,
    this.trainingJobsViewModel,
    this.ragJobsViewModel,
    this.launchIntent,
    this.onLaunchIntentHandled,
    this.isActive = true,
    this.sharedRuntimeManaged = false,
    this.surfaceMode = WorkbenchSurfaceMode.standalone,
  });

  final DashboardViewModel dashboardViewModel;
  final JobViewModel? trainingJobsViewModel;
  final JobViewModel? ragJobsViewModel;
  final AiLabLaunchIntent? launchIntent;
  final VoidCallback? onLaunchIntentHandled;
  final bool isActive;
  final bool sharedRuntimeManaged;
  final WorkbenchSurfaceMode surfaceMode;

  @override
  State<AiLabScreen> createState() => _AiLabScreenState();
}

enum _AiLabTab { deepLearning, rag }

class _AiLabScreenState extends State<AiLabScreen> {
  final _trainingStorageController = TextEditingController();
  final _trainingTargetController = TextEditingController();
  final _ragStorageController = TextEditingController();
  final _ragCollectionController = TextEditingController();
  final _ragQuestionController = TextEditingController();
  final _ragScrollController = ScrollController();

  late final JobViewModel _trainingJobsViewModel;
  late final JobViewModel _ragJobsViewModel;
  late final RagViewModel _ragViewModel;
  late final bool _ownsTrainingJobsViewModel;
  late final bool _ownsRagJobsViewModel;

  DeepLearningConfigState _config = const DeepLearningConfigState.initial();
  _AiLabTab _currentTab = _AiLabTab.deepLearning;
  _AiLabTab? _activeLaunchTab;
  WorkbenchLaunchContext? _activeLaunchContext;
  bool _resetCollection = false;
  bool _didSeedTrainingDefaults = false;
  bool _didSeedKnowledgeDefaults = false;
  bool _suppressInputRefresh = false;
  bool _didActivateWorkspace = false;

  @override
  void initState() {
    super.initState();
    widget.dashboardViewModel.addListener(_handleDashboardSummaryChanged);
    _trainingStorageController.addListener(_handleInputControllersChanged);
    _trainingTargetController.addListener(_handleInputControllersChanged);
    _ragStorageController.addListener(_handleInputControllersChanged);
    _ragCollectionController.addListener(_handleInputControllersChanged);
    _trainingJobsViewModel =
        widget.trainingJobsViewModel ??
        JobViewModel(jobType: 'ml_train', limit: 8);
    _ownsTrainingJobsViewModel = widget.trainingJobsViewModel == null;
    _ragJobsViewModel =
        widget.ragJobsViewModel ??
        JobViewModel(jobType: 'rag_ingest', limit: 8);
    _ownsRagJobsViewModel = widget.ragJobsViewModel == null;
    _ragViewModel = RagViewModel();
    _applyLaunchIntent(widget.launchIntent);
    _handleWorkspaceActivation(widget.isActive);
  }

  @override
  void didUpdateWidget(covariant AiLabScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.launchIntent != oldWidget.launchIntent) {
      _applyLaunchIntent(widget.launchIntent);
    }
    if (widget.isActive != oldWidget.isActive) {
      _handleWorkspaceActivation(widget.isActive);
    }
  }

  @override
  void dispose() {
    widget.dashboardViewModel.removeListener(_handleDashboardSummaryChanged);
    _trainingStorageController.removeListener(_handleInputControllersChanged);
    _trainingTargetController.removeListener(_handleInputControllersChanged);
    _ragStorageController.removeListener(_handleInputControllersChanged);
    _ragCollectionController.removeListener(_handleInputControllersChanged);
    _trainingStorageController.dispose();
    _trainingTargetController.dispose();
    _ragStorageController.dispose();
    _ragCollectionController.dispose();
    _ragQuestionController.dispose();
    _ragScrollController.dispose();
    if (_ownsTrainingJobsViewModel) {
      _trainingJobsViewModel.dispose();
    }
    if (_ownsRagJobsViewModel) {
      _ragJobsViewModel.dispose();
    }
    _ragViewModel.dispose();
    super.dispose();
  }

  void _handleWorkspaceActivation(bool isActive) {
    if (!widget.sharedRuntimeManaged) {
      _trainingJobsViewModel.setWorkspaceActive(isActive);
      _ragJobsViewModel.setWorkspaceActive(isActive);
    }
    if (!isActive) {
      return;
    }
    if (!_didActivateWorkspace) {
      _didActivateWorkspace = true;
      if (!widget.sharedRuntimeManaged) {
        widget.dashboardViewModel.initialize();
        _trainingJobsViewModel.loadJobs();
        _ragJobsViewModel.loadJobs();
      }
    }
    _handleDashboardSummaryChanged();
  }

  Future<void> _submitTrainingJob() async {
    final chain = _chainForKey('model');
    final resolvedStoragePath = _resolvedTrainingStoragePath(
      widget.dashboardViewModel.summary?.assetSummary,
    );
    final resolvedTargetColumn = _resolvedTrainingTargetColumn(
      widget.dashboardViewModel.summary?.assetSummary,
    );
    if (resolvedStoragePath != null &&
        resolvedStoragePath != _trainingStorageController.text.trim()) {
      _trainingStorageController.text = resolvedStoragePath;
    }
    if (resolvedTargetColumn != null &&
        resolvedTargetColumn != _trainingTargetController.text.trim()) {
      _trainingTargetController.text = resolvedTargetColumn;
    }
    final job = await _trainingJobsViewModel.submitMlTrainJob(
      storagePath:
          resolvedStoragePath ?? _trainingStorageController.text.trim(),
      modelType: _config.modelTypeValue,
      epochs: _config.epochs,
      batchSize: _config.batchSize,
      windowSize: _config.windowSize,
      targetColumn:
          resolvedTargetColumn ?? _trainingTargetController.text.trim(),
    );

    if (!mounted) {
      return;
    }

    if (job != null) {
      _showFeedback(
        _chainFeedbackMessage(
          chain,
          prefix: '训练任务已提交',
          detail: job.jobId.substring(0, 8),
        ),
      );
      widget.dashboardViewModel.loadSummary();
      return;
    }

    final message = _normalizeJobErrorMessage(
      _trainingJobsViewModel.errorMessage,
    );
    if (message != null) {
      _showFeedback(message, color: AppColors.error);
    }
  }

  Future<void> _submitRagIngestJob() async {
    final chain = _chainForKey('knowledge');
    final job = await _ragJobsViewModel.submitRagIngestJob(
      storagePath: _ragStorageController.text.trim(),
      collectionName: _ragCollectionController.text.trim(),
      reset: _resetCollection,
    );

    if (!mounted) {
      return;
    }

    if (job != null) {
      _showFeedback(
        _chainFeedbackMessage(
          chain,
          prefix: '知识库构建任务已提交',
          detail: job.jobId.substring(0, 8),
        ),
      );
      widget.dashboardViewModel.loadSummary();
      return;
    }

    final message = _normalizeJobErrorMessage(_ragJobsViewModel.errorMessage);
    if (message != null) {
      _showFeedback(message, color: AppColors.error);
    }
  }

  Future<void> _sendRagQuestion() async {
    final text = _ragQuestionController.text.trim();
    if (text.isEmpty || _ragViewModel.isLoading) {
      return;
    }
    _ragQuestionController.clear();
    await _ragViewModel.sendMessage(text);
    if (!mounted || !_ragScrollController.hasClients) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_ragScrollController.hasClients) {
        _ragScrollController.animateTo(
          _ragScrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _refreshLab() async {
    await Future.wait([
      widget.dashboardViewModel.loadSummary(),
      _trainingJobsViewModel.loadJobs(),
      _ragJobsViewModel.loadJobs(),
    ]);
  }

  AssetChainSummary? _chainForKey(String key) {
    return widget.dashboardViewModel.summary?.assetSummary.chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((item) => item?.key == key, orElse: () => null);
  }

  String _chainFeedbackMessage(
    AssetChainSummary? chain, {
    required String prefix,
    String? detail,
  }) {
    return buildChainFeedbackMessage(chain, prefix: prefix, detail: detail);
  }

  String _chainAssetActionMessage(
    AssetChainSummary? chain, {
    required String prefix,
    String? detail,
  }) {
    return buildChainActionFeedbackMessage(
      chain,
      prefix: prefix,
      detail: detail,
    );
  }

  String? _normalizeJobErrorMessage(String? message) {
    if (message == null || message.trim().isEmpty) {
      return null;
    }
    if (message.contains('HTTP 503') ||
        message.contains('JOB_BACKEND_UNAVAILABLE')) {
      return '当前部署环境未启用 Firestore Native 模式，任务中心暂不可用';
    }
    if (message.contains('No such object') ||
        (message.contains('status code') && message.contains('404'))) {
      return '存储路径不存在，请改用已上传资产的 storage path（例如 uploads/...）';
    }
    return message;
  }

  void _handleDashboardSummaryChanged() {
    final summary = widget.dashboardViewModel.summary;
    if (summary == null) {
      return;
    }
    _seedInputDefaultsFromSummary(summary.assetSummary, summary.recentAssets);
    _normalizeDefaultEntryState(summary.assetSummary);
  }

  void _handleInputControllersChanged() {
    if (!mounted || _suppressInputRefresh) {
      return;
    }
    setState(() {});
  }

  void _seedInputDefaultsFromSummary(
    AssetSummary assetSummary,
    List<DatasetAsset> recentAssets,
  ) {
    final preferredDatasetPath = _bestDatasetPath(assetSummary.datasets);
    final latestDatasetPath = _firstNonEmptyString([
      preferredDatasetPath,
      ...recentAssets.map((item) => _storagePathFromGsUrl(item.storageUrl)),
      assetSummary.models.isNotEmpty
          ? assetSummary.models.first.storagePath
          : null,
    ]);
    final latestModel = assetSummary.models.isEmpty
        ? null
        : assetSummary.models.first;
    final latestKnowledgeAsset = assetSummary.knowledgeBases.isEmpty
        ? null
        : assetSummary.knowledgeBases.first;
    final preferredTrainingPath = _firstNonEmptyString([
      latestModel?.storagePath,
      preferredDatasetPath,
      latestDatasetPath,
    ]);
    final currentTrainingPath = _trainingStorageController.text.trim();
    final shouldPromoteModelTrainingPath =
        latestModel?.storagePath != null &&
        latestModel!.storagePath!.isNotEmpty &&
        currentTrainingPath != latestModel.storagePath &&
        (currentTrainingPath.isEmpty ||
            currentTrainingPath == 'demo_data.csv' ||
            currentTrainingPath.endsWith('optimization_result.csv'));

    if ((!_didSeedTrainingDefaults &&
            (currentTrainingPath.isEmpty ||
                currentTrainingPath == 'demo_data.csv')) ||
        shouldPromoteModelTrainingPath) {
      var seededTraining = false;
      if (preferredTrainingPath != null && preferredTrainingPath.isNotEmpty) {
        _trainingStorageController.text = preferredTrainingPath;
        seededTraining = true;
      }
      if ((_trainingTargetController.text.trim().isEmpty ||
              _trainingTargetController.text.trim() == 'Load') &&
          latestModel?.targetColumn != null &&
          latestModel!.targetColumn!.isNotEmpty) {
        _trainingTargetController.text = latestModel.targetColumn!;
        seededTraining = true;
      }
      _didSeedTrainingDefaults = seededTraining;
    }

    if (latestModel != null) {
      final shouldHydrateTrainingPath =
          _trainingStorageController.text.trim().isEmpty ||
          _trainingStorageController.text.trim() == 'demo_data.csv' ||
          _trainingStorageController.text.trim().endsWith(
            'optimization_result.csv',
          );
      if (shouldHydrateTrainingPath &&
          latestModel.storagePath != null &&
          latestModel.storagePath!.isNotEmpty) {
        _trainingStorageController.text = latestModel.storagePath!;
        _didSeedTrainingDefaults = true;
      }
      if ((_trainingTargetController.text.trim().isEmpty ||
              shouldHydrateTrainingPath) &&
          latestModel.targetColumn != null &&
          latestModel.targetColumn!.isNotEmpty) {
        _trainingTargetController.text = latestModel.targetColumn!;
        _didSeedTrainingDefaults = true;
      }
    }

    if (!_didSeedKnowledgeDefaults &&
        (_ragStorageController.text.trim().isEmpty ||
            _ragStorageController.text.trim() == 'docs/')) {
      var seededKnowledge = false;
      final candidateKnowledgePath = _firstNonEmptyString([
        latestKnowledgeAsset?.storagePath,
        preferredDatasetPath,
        latestDatasetPath,
        latestModel?.storagePath,
      ]);
      if (candidateKnowledgePath != null && candidateKnowledgePath.isNotEmpty) {
        _ragStorageController.text = candidateKnowledgePath;
        seededKnowledge = true;
      }
      if (_ragCollectionController.text.trim().isEmpty ||
          _ragCollectionController.text.trim() == 'default') {
        final collection = _firstNonEmptyString([
          latestKnowledgeAsset?.collection,
          'default',
        ]);
        if (collection != null && collection.isNotEmpty) {
          _ragCollectionController.text = collection;
          seededKnowledge = true;
        }
      }
      _didSeedKnowledgeDefaults = seededKnowledge;
    }
  }

  void _normalizeDefaultEntryState(AssetSummary assetSummary) {
    if (widget.launchIntent != null) {
      return;
    }

    final resolvedTrainingPath = _resolvedTrainingStoragePath(assetSummary);
    if (resolvedTrainingPath == null || resolvedTrainingPath.isEmpty) {
      return;
    }

    final currentTrainingPath = _trainingStorageController.text.trim();
    final shouldHydrateTraining = _needsTrainingPathRepair(currentTrainingPath);
    if (!shouldHydrateTraining) {
      return;
    }

    final chain = _chainForKey('model');
    final context = buildLaunchContextFromChain(chain, prefix: '侧栏进入 AI Lab');

    if (mounted) {
      setState(() {
        _currentTab = _AiLabTab.deepLearning;
        _activeLaunchTab = _AiLabTab.deepLearning;
        _activeLaunchContext = context;
        _trainingStorageController.text = resolvedTrainingPath;
        final resolvedTargetColumn = _resolvedTrainingTargetColumn(
          assetSummary,
        );
        if (resolvedTargetColumn != null && resolvedTargetColumn.isNotEmpty) {
          _trainingTargetController.text = resolvedTargetColumn;
        }
        _didSeedTrainingDefaults = true;
      });
      return;
    }

    _currentTab = _AiLabTab.deepLearning;
    _activeLaunchTab = _AiLabTab.deepLearning;
    _activeLaunchContext = context;
    _trainingStorageController.text = resolvedTrainingPath;
    final resolvedTargetColumn = _resolvedTrainingTargetColumn(assetSummary);
    if (resolvedTargetColumn != null && resolvedTargetColumn.isNotEmpty) {
      _trainingTargetController.text = resolvedTargetColumn;
    }
    _didSeedTrainingDefaults = true;
  }

  String? _resolvedTrainingStoragePath(AssetSummary? assetSummary) {
    final latestSucceededArtifact = _latestSucceededTrainingArtifact();
    final latestModel = assetSummary?.models.isNotEmpty == true
        ? assetSummary!.models.first
        : null;
    final currentTrainingPath = _trainingStorageController.text.trim();
    if (!_needsTrainingPathRepair(currentTrainingPath)) {
      return currentTrainingPath.isEmpty ? null : currentTrainingPath;
    }
    return _firstNonEmptyString([
      latestSucceededArtifact?.result['storage_path']?.toString(),
      latestSucceededArtifact?.input['storage_path']?.toString(),
      latestModel?.storagePath,
      _bestDatasetPath(assetSummary?.datasets ?? const []),
    ]);
  }

  String? _resolvedTrainingTargetColumn(AssetSummary? assetSummary) {
    final latestSucceededArtifact = _latestSucceededTrainingArtifact();
    final latestModel = assetSummary?.models.isNotEmpty == true
        ? assetSummary!.models.first
        : null;
    final currentTargetColumn = _trainingTargetController.text.trim();
    if (currentTargetColumn.isNotEmpty && currentTargetColumn != 'Load') {
      return currentTargetColumn;
    }
    return _firstNonEmptyString([
      latestSucceededArtifact?.result['target_column']?.toString(),
      latestSucceededArtifact?.input['target_column']?.toString(),
      latestModel?.targetColumn,
    ]);
  }

  JobRecord? _latestSucceededTrainingArtifact() {
    for (final job in _trainingJobsViewModel.jobs) {
      if (job.status == 'succeeded' && _hasModelArtifact(job)) {
        return job;
      }
    }
    return null;
  }

  bool _hasModelArtifact(JobRecord job) {
    final modelPath = job.result['model_path']?.toString();
    return modelPath != null && modelPath.trim().isNotEmpty;
  }

  bool _needsTrainingPathRepair(String currentTrainingPath) {
    return currentTrainingPath.isEmpty ||
        currentTrainingPath == 'demo_data.csv' ||
        currentTrainingPath.endsWith('optimization_result.csv');
  }

  void _queueTrainingPathRepair(AssetSummary? assetSummary) {
    if (assetSummary == null) {
      return;
    }
    final resolvedPath = _resolvedTrainingStoragePath(assetSummary);
    if (resolvedPath == null || resolvedPath.isEmpty) {
      return;
    }
    final currentPath = _trainingStorageController.text.trim();
    if (!_needsTrainingPathRepair(currentPath) || currentPath == resolvedPath) {
      return;
    }
    final resolvedTargetColumn = _resolvedTrainingTargetColumn(assetSummary);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      if (_trainingStorageController.text.trim() != resolvedPath) {
        _trainingStorageController.text = resolvedPath;
      }
      if (resolvedTargetColumn != null &&
          resolvedTargetColumn.isNotEmpty &&
          _trainingTargetController.text.trim() != resolvedTargetColumn) {
        _trainingTargetController.text = resolvedTargetColumn;
      }
    });
    Future<void>.delayed(const Duration(milliseconds: 300), () {
      if (!mounted) {
        return;
      }
      if (_needsTrainingPathRepair(_trainingStorageController.text.trim())) {
        _setControllerTextSilently(_trainingStorageController, resolvedPath);
      }
      if (resolvedTargetColumn != null &&
          resolvedTargetColumn.isNotEmpty &&
          (_trainingTargetController.text.trim().isEmpty ||
              _trainingTargetController.text.trim() == 'Load')) {
        _setControllerTextSilently(
          _trainingTargetController,
          resolvedTargetColumn,
        );
      }
    });
  }

  void _syncResolvedTrainingControllers(AssetSummary? assetSummary) {
    final resolvedPath = _resolvedTrainingStoragePath(assetSummary);
    if (resolvedPath != null &&
        resolvedPath.isNotEmpty &&
        _needsTrainingPathRepair(_trainingStorageController.text.trim())) {
      _setControllerTextSilently(_trainingStorageController, resolvedPath);
    }

    final resolvedTargetColumn = _resolvedTrainingTargetColumn(assetSummary);
    if (resolvedTargetColumn != null &&
        resolvedTargetColumn.isNotEmpty &&
        (_trainingTargetController.text.trim().isEmpty ||
            _trainingTargetController.text.trim() == 'Load')) {
      _setControllerTextSilently(
        _trainingTargetController,
        resolvedTargetColumn,
      );
    }
  }

  void _setControllerTextSilently(
    TextEditingController controller,
    String value,
  ) {
    if (controller.text == value) {
      return;
    }
    _suppressInputRefresh = true;
    controller.text = value;
    _suppressInputRefresh = false;
  }

  String? _bestDatasetPath(List<AssetDataset> datasets) {
    final sorted =
        datasets
            .where((item) => _storagePathFromGsUrl(item.storageUrl) != null)
            .toList(growable: false)
          ..sort((left, right) {
            final rowCompare = (right.rows ?? 0).compareTo(left.rows ?? 0);
            if (rowCompare != 0) {
              return rowCompare;
            }
            final timeCompare = (right.createdAt?.millisecondsSinceEpoch ?? 0)
                .compareTo(left.createdAt?.millisecondsSinceEpoch ?? 0);
            if (timeCompare != 0) {
              return timeCompare;
            }
            return right.filename.compareTo(left.filename);
          });
    if (sorted.isEmpty) {
      return null;
    }
    return _storagePathFromGsUrl(sorted.first.storageUrl);
  }

  String? _storagePathFromGsUrl(String? rawUrl) {
    if (rawUrl == null || rawUrl.trim().isEmpty) {
      return null;
    }
    final value = rawUrl.trim();
    if (!value.startsWith('gs://')) {
      return value;
    }
    final withoutScheme = value.substring(5);
    final slashIndex = withoutScheme.indexOf('/');
    if (slashIndex == -1 || slashIndex == withoutScheme.length - 1) {
      return null;
    }
    return withoutScheme.substring(slashIndex + 1);
  }

  String? _firstNonEmptyString(List<String?> candidates) {
    for (final candidate in candidates) {
      if (candidate != null && candidate.trim().isNotEmpty) {
        return candidate.trim();
      }
    }
    return null;
  }

  void _showFeedback(String message, {Color color = AppColors.success}) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message), backgroundColor: color));
  }

  Future<void> _copyText(String text, String successMessage) async {
    final value = text.trim();
    if (value.isEmpty) {
      _showFeedback('没有可复制的内容', color: AppColors.error);
      return;
    }
    await Clipboard.setData(ClipboardData(text: value));
    _showFeedback(successMessage);
  }

  void _applyModelAsset(AssetModel asset, {AssetChainSummary? chain}) {
    setState(() {
      if (asset.storagePath != null && asset.storagePath!.isNotEmpty) {
        _trainingStorageController.text = asset.storagePath!;
      }
      if (asset.targetColumn != null && asset.targetColumn!.isNotEmpty) {
        _trainingTargetController.text = asset.targetColumn!;
      }
      _config = _config.copyWith(modelType: _toModelType(asset.modelType));
      _currentTab = _AiLabTab.deepLearning;
    });

    _showFeedback(_chainAssetActionMessage(chain, prefix: '模型注册表资产已回填到训练入口'));
  }

  void _applyKnowledgeAsset(KnowledgeAsset asset, {AssetChainSummary? chain}) {
    setState(() {
      if (asset.storagePath != null && asset.storagePath!.isNotEmpty) {
        _ragStorageController.text = asset.storagePath!;
      }
      if (asset.collection != null && asset.collection!.isNotEmpty) {
        _ragCollectionController.text = asset.collection!;
      }
      _resetCollection = asset.reset ?? false;
      _currentTab = _AiLabTab.rag;
    });

    _showFeedback(_chainAssetActionMessage(chain, prefix: '知识注册表资产已回填到知识库入口'));
  }

  Future<void> _copyModelPassport(
    AssetModel asset, {
    AssetChainSummary? chain,
  }) async {
    await _copyText(
      _buildModelPassport(asset),
      _chainAssetActionMessage(chain, prefix: '模型护照已复制'),
    );
  }

  Future<void> _copyKnowledgePassport(
    KnowledgeAsset asset, {
    AssetChainSummary? chain,
  }) async {
    await _copyText(
      _buildKnowledgePassport(asset),
      _chainAssetActionMessage(chain, prefix: '知识快照护照已复制'),
    );
  }

  String _buildModelPassport(AssetModel asset) {
    final completedAt = asset.completedAt == null
        ? '--'
        : DateFormat('yyyy-MM-dd HH:mm').format(asset.completedAt!.toLocal());
    return [
      'Model Passport',
      'version=v${asset.version}',
      'job_id=${asset.jobId}',
      'model_type=${(asset.modelType ?? '--').toUpperCase()}',
      'target_column=${asset.targetColumn ?? '--'}',
      'model_path=${asset.modelPath ?? '--'}',
      'storage_path=${asset.storagePath ?? '--'}',
      'attempt=${asset.attemptCount ?? '--'}/${asset.maxAttempts ?? '--'}',
      'completed_at=$completedAt',
    ].join('\n');
  }

  String _buildKnowledgePassport(KnowledgeAsset asset) {
    final completedAt = asset.completedAt == null
        ? '--'
        : DateFormat('yyyy-MM-dd HH:mm').format(asset.completedAt!.toLocal());
    return [
      'Knowledge Snapshot Passport',
      'version=v${asset.version}',
      'job_id=${asset.jobId}',
      'collection=${asset.collection ?? '--'}',
      'storage_path=${asset.storagePath ?? '--'}',
      'document_count=${asset.count ?? '--'}',
      'mode=${asset.reset == true ? 'reset' : 'incremental'}',
      'completed_at=$completedAt',
    ].join('\n');
  }

  void _applyTrainingArtifact(JobRecord job, {AssetChainSummary? chain}) {
    final storagePath = job.input['storage_path']?.toString();
    final targetColumn =
        job.result['target_column']?.toString() ??
        job.input['target_column']?.toString();
    final modelType = _toModelType(
      job.result['model_type']?.toString() ??
          job.input['model_type']?.toString(),
    );
    final epochs = _asInt(job.input['epochs']);
    final batchSize = _asInt(job.input['batch_size']);
    final windowSize = _asInt(job.input['window_size']);

    setState(() {
      if (storagePath != null && storagePath.isNotEmpty) {
        _trainingStorageController.text = storagePath;
      }
      if (targetColumn != null && targetColumn.isNotEmpty) {
        _trainingTargetController.text = targetColumn;
      }
      _config = _config.copyWith(
        modelType: modelType,
        epochs: epochs,
        batchSize: batchSize,
        windowSize: windowSize,
      );
      _currentTab = _AiLabTab.deepLearning;
    });

    _showFeedback(_chainAssetActionMessage(chain, prefix: '训练产物已回填到训练入口'));
  }

  void _applyKnowledgeSnapshot(JobRecord job, {AssetChainSummary? chain}) {
    final storagePath =
        job.result['storage_path']?.toString() ??
        job.input['storage_path']?.toString();
    final collection =
        job.result['collection']?.toString() ??
        job.input['collection_name']?.toString();
    final reset = _asBool(job.input['reset']) ?? false;

    setState(() {
      if (storagePath != null && storagePath.isNotEmpty) {
        _ragStorageController.text = storagePath;
      }
      if (collection != null && collection.isNotEmpty) {
        _ragCollectionController.text = collection;
      }
      _resetCollection = reset;
      _currentTab = _AiLabTab.rag;
    });

    _showFeedback(_chainAssetActionMessage(chain, prefix: '知识库快照已回填到构建入口'));
  }

  void _clearRagConversation({AssetChainSummary? chain}) {
    _ragViewModel.clearMessages();
    _showFeedback(_chainAssetActionMessage(chain, prefix: '问答会话已清空'));
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([
        widget.dashboardViewModel,
        _trainingJobsViewModel,
        _ragJobsViewModel,
        _ragViewModel,
      ]),
      builder: (context, _) {
        final summary = widget.dashboardViewModel.summary;
        final assetSummary = summary?.assetSummary;
        final modelChain = assetSummary?.chainSummaries
            .cast<AssetChainSummary?>()
            .firstWhere((item) => item?.key == 'model', orElse: () => null);
        final knowledgeChain = assetSummary?.chainSummaries
            .cast<AssetChainSummary?>()
            .firstWhere((item) => item?.key == 'knowledge', orElse: () => null);
        final activeChain = _currentTab == _AiLabTab.deepLearning
            ? modelChain
            : knowledgeChain;
        final latestModelAsset =
            assetSummary != null && assetSummary.models.isNotEmpty
            ? assetSummary.models.first
            : null;
        final latestKnowledgeAsset =
            assetSummary != null && assetSummary.knowledgeBases.isNotEmpty
            ? assetSummary.knowledgeBases.first
            : null;
        _syncResolvedTrainingControllers(assetSummary);
        _queueTrainingPathRepair(assetSummary);
        final trainingError = _normalizeJobErrorMessage(
          _trainingJobsViewModel.errorMessage,
        );
        final ragError = _normalizeJobErrorMessage(
          _ragJobsViewModel.errorMessage,
        );
        final tabSwitcher = _buildTabSwitcher();
        final content = ResponsiveWrapper(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (widget.surfaceMode.isEmbedded) ...[
                  _buildEmbeddedHeader(tabSwitcher),
                  const SizedBox(height: 20),
                ],
                AiLabOperationsBoard(
                  summary: summary,
                  trainingJobs: _trainingJobsViewModel.jobs,
                  ragJobs: _ragJobsViewModel.jobs,
                  currentTab: _currentTab.name,
                  launchIntent: widget.launchIntent,
                  trainingStoragePath:
                      _resolvedTrainingStoragePath(assetSummary) ??
                      _trainingStorageController.text.trim(),
                  ragStoragePath: _ragStorageController.text.trim(),
                ),
                const SizedBox(height: 20),
                WorkbenchCommandStrip(
                  title: '页级动作',
                  description: '把训练提交、知识库构建和实验刷新固定在顶部，避免在单壳模式下依赖各面板内部按钮来完成主流程。',
                  actions: [
                    WorkbenchCommandAction(
                      label: _trainingJobsViewModel.isSubmitting
                          ? '训练提交中...'
                          : '提交训练任务',
                      icon: Icons.model_training_rounded,
                      onTap:
                          (_trainingStorageController.text.trim().isNotEmpty &&
                              _trainingTargetController.text
                                  .trim()
                                  .isNotEmpty &&
                              !_trainingJobsViewModel.isSubmitting)
                          ? () {
                              _submitTrainingJob();
                            }
                          : null,
                      tone: _currentTab == _AiLabTab.deepLearning
                          ? WorkbenchCommandTone.primary
                          : WorkbenchCommandTone.tonal,
                      isLoading: _trainingJobsViewModel.isSubmitting,
                    ),
                    WorkbenchCommandAction(
                      label: _ragJobsViewModel.isSubmitting
                          ? '知识库提交中...'
                          : '构建知识库',
                      icon: Icons.auto_awesome_rounded,
                      onTap:
                          (_ragStorageController.text.trim().isNotEmpty &&
                              !_ragJobsViewModel.isSubmitting)
                          ? () {
                              _submitRagIngestJob();
                            }
                          : null,
                      tone: _currentTab == _AiLabTab.rag
                          ? WorkbenchCommandTone.primary
                          : WorkbenchCommandTone.tonal,
                      isLoading: _ragJobsViewModel.isSubmitting,
                    ),
                    WorkbenchCommandAction(
                      label: '切到深度学习',
                      icon: Icons.tune_rounded,
                      onTap: () {
                        setState(() {
                          _currentTab = _AiLabTab.deepLearning;
                        });
                      },
                      tone: WorkbenchCommandTone.outline,
                    ),
                    WorkbenchCommandAction(
                      label: '刷新 AI 实验台',
                      icon: Icons.refresh_rounded,
                      onTap: () {
                        _refreshLab();
                      },
                      tone: WorkbenchCommandTone.outline,
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                WorkbenchRunbookPanel(
                  chain: activeChain,
                  continuationContext: _contextForTab(_currentTab),
                  description: _currentTab == _AiLabTab.deepLearning
                      ? '把训练链路的版本、责任和处置步骤直接压到当前工作台，优先完成模型资产回填与版本治理。'
                      : '把知识库链路的处置步骤直接压到当前工作台，优先完成快照回填、集合校验和问答治理。',
                  actions: _currentTab == _AiLabTab.deepLearning
                      ? [
                          WorkbenchCommandAction(
                            label: '应用最新模型资产',
                            icon: Icons.download_done_rounded,
                            onTap: latestModelAsset == null
                                ? null
                                : () {
                                    _applyModelAsset(
                                      latestModelAsset,
                                      chain: modelChain,
                                    );
                                  },
                            tone: WorkbenchCommandTone.primary,
                          ),
                          WorkbenchCommandAction(
                            label: '复制模型护照',
                            icon: Icons.badge_rounded,
                            onTap: latestModelAsset == null
                                ? null
                                : () {
                                    _copyModelPassport(
                                      latestModelAsset,
                                      chain: modelChain,
                                    );
                                  },
                            tone: WorkbenchCommandTone.tonal,
                          ),
                          WorkbenchCommandAction(
                            label: '刷新 AI 实验台',
                            icon: Icons.refresh_rounded,
                            onTap: _refreshLab,
                            tone: WorkbenchCommandTone.outline,
                          ),
                        ]
                      : [
                          WorkbenchCommandAction(
                            label: '应用最新知识快照',
                            icon: Icons.library_add_check_rounded,
                            onTap: latestKnowledgeAsset == null
                                ? null
                                : () {
                                    _applyKnowledgeAsset(
                                      latestKnowledgeAsset,
                                      chain: knowledgeChain,
                                    );
                                  },
                            tone: WorkbenchCommandTone.primary,
                          ),
                          WorkbenchCommandAction(
                            label: '复制知识护照',
                            icon: Icons.badge_rounded,
                            onTap: latestKnowledgeAsset == null
                                ? null
                                : () {
                                    _copyKnowledgePassport(
                                      latestKnowledgeAsset,
                                      chain: knowledgeChain,
                                    );
                                  },
                            tone: WorkbenchCommandTone.tonal,
                          ),
                          WorkbenchCommandAction(
                            label: '清空问答会话',
                            icon: Icons.cleaning_services_rounded,
                            onTap: () {
                              _clearRagConversation(chain: knowledgeChain);
                            },
                            tone: WorkbenchCommandTone.outline,
                          ),
                        ],
                ),
                if (activeChain != null) const SizedBox(height: 20),
                WorkspaceActionDeck(
                  lanes: [
                    WorkspaceActionLane(
                      title: '模型训练车道',
                      description:
                          '把训练提交、最新模型回填、护照复制和队列刷新收在一条主工作流里，避免训练动作继续散在顶部按钮和资产卡内部。',
                      accent: AppColors.cta,
                      icon: Icons.model_training_rounded,
                      workspaceLabel:
                          _contextForTab(
                            _AiLabTab.deepLearning,
                          )?.workspaceTargetLabel ??
                          modelChain?.workspaceTargetLabel,
                      cardLabel:
                          _contextForTab(
                            _AiLabTab.deepLearning,
                          )?.cardTargetLabel ??
                          modelChain?.cardTargetLabel,
                      incidentLabel:
                          _contextForTab(
                            _AiLabTab.deepLearning,
                          )?.incidentTargetLabel ??
                          modelChain?.incidentTargetLabel,
                      summary:
                          trainingError ??
                          _contextForTab(
                            _AiLabTab.deepLearning,
                          )?.workspaceBrief ??
                          modelChain?.workspaceBrief,
                      statusLabel: trainingError != null
                          ? '提交失败'
                          : _trainingJobsViewModel.isSubmitting
                          ? '提交中'
                          : _trainingJobsViewModel.activeJob != null
                          ? buildJobPrimaryText(_trainingJobsViewModel.activeJob!)
                          : (_trainingJobsViewModel.jobs.isEmpty
                                ? '空闲'
                                : '就绪'),
                      statusColor: trainingError != null
                          ? AppColors.error
                          : _trainingJobsViewModel.isSubmitting
                          ? AppColors.warning
                          : (_trainingJobsViewModel.activeJob?.isRunning == true
                                ? AppColors.warning
                                : AppColors.success),
                      recommendedActionKey: trainingError != null
                          ? 'submit_training'
                          : _recommendedAiLaneAction(
                              _contextForTab(_AiLabTab.deepLearning),
                              hasLatestAsset: latestModelAsset != null,
                              runtimeActionKey: 'submit_training',
                              registryActionKey: 'apply_latest_model_asset',
                              timelineActionKey: 'copy_model_passport',
                            ),
                      actions: [
                        WorkspaceActionLaneAction(
                          label: '提交训练任务',
                          icon: Icons.play_arrow_rounded,
                          onTap:
                              (_trainingStorageController.text
                                      .trim()
                                      .isNotEmpty &&
                                  _trainingTargetController.text
                                      .trim()
                                      .isNotEmpty &&
                                  !_trainingJobsViewModel.isSubmitting)
                              ? _submitTrainingJob
                              : null,
                          semanticKey: 'submit_training',
                          tone: WorkspaceActionLaneTone.primary,
                          isLoading: _trainingJobsViewModel.isSubmitting,
                        ),
                        WorkspaceActionLaneAction(
                          label: '回填最新模型资产',
                          icon: Icons.download_done_rounded,
                          onTap: latestModelAsset == null
                              ? null
                              : () => _applyModelAsset(
                                  latestModelAsset,
                                  chain: modelChain,
                                ),
                          semanticKey: 'apply_latest_model_asset',
                          tone: WorkspaceActionLaneTone.tonal,
                        ),
                        WorkspaceActionLaneAction(
                          label: '复制模型护照',
                          icon: Icons.badge_rounded,
                          onTap: latestModelAsset == null
                              ? null
                              : () => _copyModelPassport(
                                  latestModelAsset,
                                  chain: modelChain,
                                ),
                          semanticKey: 'copy_model_passport',
                        ),
                        WorkspaceActionLaneAction(
                          label: '刷新训练队列',
                          icon: Icons.refresh_rounded,
                          onTap: _trainingJobsViewModel.loadJobs,
                          semanticKey: 'refresh_training_jobs',
                        ),
                      ],
                    ),
                    WorkspaceActionLane(
                      title: '知识构建车道',
                      description:
                          '把知识库构建、快照回填、护照复制和会话治理收在同一条知识工作流里，减少在资产区和问答区之间来回切换。',
                      accent: AppColors.success,
                      icon: Icons.auto_awesome_rounded,
                      workspaceLabel:
                          _contextForTab(_AiLabTab.rag)?.workspaceTargetLabel ??
                          knowledgeChain?.workspaceTargetLabel,
                      cardLabel:
                          _contextForTab(_AiLabTab.rag)?.cardTargetLabel ??
                          knowledgeChain?.cardTargetLabel,
                      incidentLabel:
                          _contextForTab(_AiLabTab.rag)?.incidentTargetLabel ??
                          knowledgeChain?.incidentTargetLabel,
                      summary:
                          ragError ??
                          _contextForTab(_AiLabTab.rag)?.workspaceBrief ??
                          knowledgeChain?.workspaceBrief,
                      statusLabel: ragError != null
                          ? '提交失败'
                          : _ragJobsViewModel.isSubmitting
                          ? '提交中'
                          : _ragJobsViewModel.activeJob != null
                          ? buildJobPrimaryText(_ragJobsViewModel.activeJob!)
                          : (_ragJobsViewModel.jobs.isEmpty ? '空闲' : '就绪'),
                      statusColor: ragError != null
                          ? AppColors.error
                          : _ragJobsViewModel.isSubmitting
                          ? AppColors.warning
                          : (_ragJobsViewModel.activeJob?.isRunning == true
                                ? AppColors.warning
                                : AppColors.success),
                      recommendedActionKey: ragError != null
                          ? 'build_knowledge'
                          : _recommendedAiLaneAction(
                              _contextForTab(_AiLabTab.rag),
                              hasLatestAsset: latestKnowledgeAsset != null,
                              runtimeActionKey: 'build_knowledge',
                              registryActionKey: 'apply_latest_knowledge_asset',
                              timelineActionKey: 'copy_knowledge_passport',
                            ),
                      actions: [
                        WorkspaceActionLaneAction(
                          label: '构建知识库',
                          icon: Icons.hub_rounded,
                          onTap:
                              (_ragStorageController.text.trim().isNotEmpty &&
                                  !_ragJobsViewModel.isSubmitting)
                              ? _submitRagIngestJob
                              : null,
                          semanticKey: 'build_knowledge',
                          tone: WorkspaceActionLaneTone.primary,
                          isLoading: _ragJobsViewModel.isSubmitting,
                        ),
                        WorkspaceActionLaneAction(
                          label: '回填最新知识快照',
                          icon: Icons.library_add_check_rounded,
                          onTap: latestKnowledgeAsset == null
                              ? null
                              : () => _applyKnowledgeAsset(
                                  latestKnowledgeAsset,
                                  chain: knowledgeChain,
                                ),
                          semanticKey: 'apply_latest_knowledge_asset',
                          tone: WorkspaceActionLaneTone.tonal,
                        ),
                        WorkspaceActionLaneAction(
                          label: '复制知识护照',
                          icon: Icons.badge_rounded,
                          onTap: latestKnowledgeAsset == null
                              ? null
                              : () => _copyKnowledgePassport(
                                  latestKnowledgeAsset,
                                  chain: knowledgeChain,
                                ),
                          semanticKey: 'copy_knowledge_passport',
                        ),
                        WorkspaceActionLaneAction(
                          label: '清空问答会话',
                          icon: Icons.cleaning_services_rounded,
                          onTap: () =>
                              _clearRagConversation(chain: knowledgeChain),
                          semanticKey: 'clear_rag_conversation',
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                WorkbenchSectionSignal(
                  chain: activeChain,
                  continuationContext: _contextForTab(_currentTab),
                  title: '资产治理区',
                  description: _currentTab == _AiLabTab.deepLearning
                      ? '先看模型注册表、训练产物和版本血缘，再决定是回填模型还是重新提交训练。'
                      : '先看知识快照、集合状态和版本血缘，再决定是回填快照还是重新构建知识库。',
                  icon: _currentTab == _AiLabTab.deepLearning
                      ? Icons.account_tree_rounded
                      : Icons.auto_stories_rounded,
                ),
                if (activeChain != null) const SizedBox(height: 20),
                AiLabAssetControlBoard(
                  activeChain: activeChain,
                  continuationContext: _contextForTab(_currentTab),
                  assetSummary: summary?.assetSummary,
                  trainingJobs: _trainingJobsViewModel.jobs,
                  ragJobs: _ragJobsViewModel.jobs,
                  onApplyTrainingArtifact: (job) {
                    _applyTrainingArtifact(job, chain: modelChain);
                  },
                  onCopyModelPath: (path) {
                    _copyText(
                      path,
                      _chainAssetActionMessage(modelChain, prefix: '模型路径已复制'),
                    );
                  },
                  onApplyKnowledgeSnapshot: (job) {
                    _applyKnowledgeSnapshot(job, chain: knowledgeChain);
                  },
                  onCopyCollection: (collection) {
                    _copyText(
                      collection,
                      _chainAssetActionMessage(knowledgeChain, prefix: '集合名已复制'),
                    );
                  },
                  onClearConversation: () {
                    _clearRagConversation(chain: knowledgeChain);
                  },
                  onApplyModelAsset: (asset) {
                    _applyModelAsset(asset, chain: modelChain);
                  },
                  onCopyModelPassport: (asset) {
                    _copyModelPassport(asset, chain: modelChain);
                  },
                  onApplyKnowledgeAsset: (asset) {
                    _applyKnowledgeAsset(asset, chain: knowledgeChain);
                  },
                  onCopyKnowledgePassport: (asset) {
                    _copyKnowledgePassport(asset, chain: knowledgeChain);
                  },
                ),
                const SizedBox(height: 20),
                WorkbenchSectionSignal(
                  chain: activeChain,
                  continuationContext: _contextForTab(_currentTab),
                  title: _currentTab == _AiLabTab.deepLearning
                      ? '训练执行面'
                      : '知识执行面',
                  description: _currentTab == _AiLabTab.deepLearning
                      ? '这一块负责训练配置、任务轨迹和最新模型表现，链路活跃时优先盯这里。'
                      : '这一块负责知识构建、问答验证和引用来源，链路活跃或失败时优先盯这里。',
                  icon: _currentTab == _AiLabTab.deepLearning
                      ? Icons.model_training_rounded
                      : Icons.chat_bubble_outline_rounded,
                ),
                if (activeChain != null) const SizedBox(height: 20),
                if (_currentTab == _AiLabTab.deepLearning)
                  _buildDeepLearningTab(summary)
                else
                  _buildRagTab(summary),
              ],
            ),
          ),
        );

        return WorkbenchPageFrame(
          surfaceMode: widget.surfaceMode,
          appBar: widget.surfaceMode.isStandalone
              ? AppBar(
                  title: const Text('AI Lab'),
                  backgroundColor: AppColors.surface,
                  surfaceTintColor: Colors.transparent,
                  actions: [
                    Padding(
                      padding: const EdgeInsets.only(right: 16),
                      child: tabSwitcher,
                    ),
                  ],
                )
              : null,
          body: content,
        );
      },
    );
  }

  Widget _buildTabSwitcher() {
    return SegmentedButton<_AiLabTab>(
      showSelectedIcon: false,
      segments: const [
        ButtonSegment<_AiLabTab>(
          value: _AiLabTab.deepLearning,
          icon: Icon(Icons.model_training_rounded),
          label: Text('深度学习'),
        ),
        ButtonSegment<_AiLabTab>(
          value: _AiLabTab.rag,
          icon: Icon(Icons.auto_awesome_rounded),
          label: Text('知识助手 RAG'),
        ),
      ],
      selected: {_currentTab},
      onSelectionChanged: (selection) {
        setState(() {
          _currentTab = selection.first;
        });
      },
    );
  }

  Widget _buildEmbeddedHeader(Widget tabSwitcher) {
    return EmbeddedPageHeader(
      title: 'AI Lab',
      description: '将深度学习训练、知识库构建和问答调试统一放到一个实验工作台中。',
      trailing: tabSwitcher,
    );
  }

  Widget _buildDeepLearningTab(DashboardSummary? summary) {
    final focusJob = _primaryJob(
      _trainingJobsViewModel.jobs,
      _trainingJobsViewModel.activeJob,
    );
    final logs = _buildTrainingLogOutput(focusJob);
    return LabSplitPanel(
      left: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _TrainingDatasetCard(
            storageController: _trainingStorageController,
            targetController: _trainingTargetController,
          ),
          const SizedBox(height: 16),
          DeepLearningConfigPanel(
            config: _config,
            isTraining: _trainingJobsViewModel.isSubmitting,
            onModelTypeChanged: (value) {
              setState(() {
                _config = _config.copyWith(modelType: value);
              });
            },
            onEpochsChanged: (value) {
              setState(() {
                _config = _config.copyWith(epochs: value);
              });
            },
            onWindowSizeChanged: (value) {
              setState(() {
                _config = _config.copyWith(windowSize: value);
              });
            },
            onBatchSizeChanged: (value) {
              setState(() {
                _config = _config.copyWith(batchSize: value);
              });
            },
            onStartTraining: _submitTrainingJob,
          ),
        ],
      ),
      right: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          DeepLearningTerminalPanel(
            isTraining: focusJob?.isRunning == true,
            logs: logs,
          ),
          if (focusJob != null) ...[
            const SizedBox(height: 16),
            JobEventTimeline(
              job: focusJob,
              title: '训练阶段轨迹',
              emptyMessage: '提交训练任务后，这里会显示数据加载、序列构造、训练与产物上传阶段。',
              onOpenOperation: () => _openJobInShellRuntime(focusJob),
              onRetry: focusJob.retryable
                  ? () => _retryJob(_trainingJobsViewModel, focusJob)
                  : null,
              onCancel: focusJob.isTerminal
                  ? null
                  : () => _cancelJob(_trainingJobsViewModel, focusJob),
              onApprove: focusJob.isAwaitingApproval
                  ? () => _resolveApproval(
                      _trainingJobsViewModel,
                      focusJob,
                      approved: true,
                    )
                  : null,
              onReject: focusJob.isAwaitingApproval
                  ? () => _resolveApproval(
                      _trainingJobsViewModel,
                      focusJob,
                      approved: false,
                    )
                  : null,
            ),
          ],
          const SizedBox(height: 16),
          Text('最近训练任务', style: AppTextStyles.h4),
          const SizedBox(height: 12),
          JobActivityList(
            jobs: _trainingJobsViewModel.jobs,
            emptyMessage: '暂无训练任务，先提交一次模型训练。',
            compact: true,
            onOpenJob: _openJobInShellRuntime,
          ),
        ],
      ),
    );
  }

  Widget _buildRagTab(DashboardSummary? summary) {
    final focusJob = _primaryJob(
      _ragJobsViewModel.jobs,
      _ragJobsViewModel.activeJob,
    );
    return LabSplitPanel(
      left: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _RagIngestCard(
            storageController: _ragStorageController,
            collectionController: _ragCollectionController,
            resetCollection: _resetCollection,
            isSubmitting: _ragJobsViewModel.isSubmitting,
            onResetChanged: (value) {
              setState(() {
                _resetCollection = value;
              });
            },
            onSubmit: _submitRagIngestJob,
          ),
          const SizedBox(height: 16),
          Text('最近知识库任务', style: AppTextStyles.h4),
          const SizedBox(height: 12),
          JobActivityList(
            jobs: _ragJobsViewModel.jobs,
            emptyMessage: '暂无知识库构建任务。',
            compact: true,
            onOpenJob: _openJobInShellRuntime,
          ),
        ],
      ),
      right: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (focusJob != null) ...[
            JobEventTimeline(
              job: focusJob,
              title: '知识库构建轨迹',
              emptyMessage: '提交知识库任务后，这里会显示文档抓取、切片和向量化阶段。',
              onOpenOperation: () => _openJobInShellRuntime(focusJob),
              onRetry: focusJob.retryable
                  ? () => _retryJob(_ragJobsViewModel, focusJob)
                  : null,
              onCancel: focusJob.isTerminal
                  ? null
                  : () => _cancelJob(_ragJobsViewModel, focusJob),
              onApprove: focusJob.isAwaitingApproval
                  ? () => _resolveApproval(
                      _ragJobsViewModel,
                      focusJob,
                      approved: true,
                    )
                  : null,
              onReject: focusJob.isAwaitingApproval
                  ? () => _resolveApproval(
                      _ragJobsViewModel,
                      focusJob,
                      approved: false,
                    )
                  : null,
            ),
            const SizedBox(height: 16),
          ],
          SizedBox(
            height: 520,
            child: GlassCard(
              padding: EdgeInsets.zero,
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                    child: Row(
                      children: [
                        Text('知识问答面板', style: AppTextStyles.h4),
                        const Spacer(),
                        Text(
                          _ragJobsViewModel.activeJob?.statusMessage ?? '默认知识库',
                          style: AppTextStyles.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: RagMessageList(
                      messages: _ragViewModel.messages,
                      scrollController: _ragScrollController,
                    ),
                  ),
                  RagInputArea(
                    controller: _ragQuestionController,
                    isLoading: _ragViewModel.isLoading,
                    onSend: _sendRagQuestion,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _buildTrainingLogOutput(JobRecord? focusJob) {
    if (focusJob == null) {
      return '等待提交训练任务。\n请先填写训练数据路径和目标列。';
    }

    final buffer = StringBuffer();
    buffer.writeln('[${buildJobPrimaryText(focusJob)}] ${focusJob.displayTitle}');
    buffer.writeln('任务编号: ${focusJob.jobId}');
    if (focusJob.events.isNotEmpty) {
      for (final event in focusJob.events.take(10)) {
        final timestamp = event.timestamp == null
            ? '--:--:--'
            : DateFormat('HH:mm:ss').format(event.timestamp!.toLocal());
        buffer.writeln(
          '[$timestamp] (${event.progress}%) [${event.phase}] ${buildJobEventMessage(focusJob, event)}',
        );
      }
    } else if (focusJob.statusMessage != null) {
      buffer.writeln('状态: ${buildJobPrimaryText(focusJob)}');
    }
    if (focusJob.error != null) {
      buffer.writeln('错误: ${focusJob.error!.message}');
    }
    final metrics = focusJob.result['metrics'];
    if (metrics is Map) {
      buffer.writeln('指标: ${metrics.toString()}');
    }
    return buffer.toString().trim();
  }

  JobRecord? _primaryJob(List<JobRecord> jobs, JobRecord? activeJob) {
    if (activeJob != null) {
      return activeJob;
    }
    if (jobs.isEmpty) {
      return null;
    }
    return jobs.first;
  }

  Future<void> _retryJob(JobViewModel viewModel, JobRecord job) async {
    final retried = await viewModel.retryJob(job.jobId);
    if (!mounted) {
      return;
    }
    if (retried != null) {
      await _openJobInShellRuntime(retried);
      final chain = viewModel == _trainingJobsViewModel
          ? _chainForKey('model')
          : _chainForKey('knowledge');
      _showFeedback(_chainFeedbackMessage(chain, prefix: '任务已重新排队'));
      widget.dashboardViewModel.loadSummary();
      return;
    }
    final message = _normalizeJobErrorMessage(viewModel.errorMessage);
    if (message != null) {
      _showFeedback(message, color: AppColors.error);
    }
  }

  Future<void> _cancelJob(JobViewModel viewModel, JobRecord job) async {
    final cancelled = await viewModel.cancelJob(job);
    if (!mounted) {
      return;
    }
    if (cancelled != null) {
      await _openJobInShellRuntime(cancelled);
      final chain = viewModel == _trainingJobsViewModel
          ? _chainForKey('model')
          : _chainForKey('knowledge');
      _showFeedback(_chainFeedbackMessage(chain, prefix: '任务已提交取消'));
      widget.dashboardViewModel.loadSummary();
      return;
    }
    final message = _normalizeJobErrorMessage(viewModel.errorMessage);
    if (message != null) {
      _showFeedback(message, color: AppColors.error);
    }
  }

  Future<void> _resolveApproval(
    JobViewModel viewModel,
    JobRecord job, {
    required bool approved,
  }) async {
    final updated = await viewModel.resolveApproval(job, approved: approved);
    if (!mounted) {
      return;
    }
    if (updated != null) {
      await _openJobInShellRuntime(updated);
      final chain = viewModel == _trainingJobsViewModel
          ? _chainForKey('model')
          : _chainForKey('knowledge');
      _showFeedback(
        _chainFeedbackMessage(
          chain,
          prefix: approved ? '任务已批准执行' : '任务已驳回',
        ),
      );
      widget.dashboardViewModel.loadSummary();
      return;
    }
    final message = _normalizeJobErrorMessage(viewModel.errorMessage);
    if (message != null) {
      _showFeedback(message, color: AppColors.error);
    }
  }

  Future<void> _openJobInShellRuntime(JobRecord job) async {
    if (!widget.sharedRuntimeManaged) {
      return;
    }
    final runtime = MainShellRuntimeScope.maybeOf(context);
    if (runtime == null) {
      return;
    }
    await runtime.openOperation(job.operationId ?? job.jobId, seed: job);
  }

  void _applyLaunchIntent(AiLabLaunchIntent? intent) {
    if (intent == null) {
      return;
    }

    final nextTab = switch (intent.target) {
      AiLabLaunchTarget.deepLearning => _AiLabTab.deepLearning,
      AiLabLaunchTarget.rag => _AiLabTab.rag,
    };

    if (mounted) {
      setState(() {
        _activeLaunchContext = intent.context;
        _activeLaunchTab = nextTab;
        _currentTab = nextTab;
      });
    } else {
      _activeLaunchContext = intent.context;
      _activeLaunchTab = nextTab;
      _currentTab = nextTab;
    }

    switch (intent.target) {
      case AiLabLaunchTarget.deepLearning:
        _trainingStorageController.text = intent.storagePath;
        _didSeedTrainingDefaults = true;
        if (intent.targetColumn != null && intent.targetColumn!.isNotEmpty) {
          _trainingTargetController.text = intent.targetColumn!;
        }
        break;
      case AiLabLaunchTarget.rag:
        _ragStorageController.text = intent.storagePath;
        _didSeedKnowledgeDefaults = true;
        if (intent.collectionName != null &&
            intent.collectionName!.isNotEmpty) {
          _ragCollectionController.text = intent.collectionName!;
        }
        _resetCollection = intent.resetCollection;
        break;
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      final source = intent.sourceLabel;
      if (source != null && source.isNotEmpty && !source.startsWith('侧栏进入 ')) {
        final arrivalContext = normalizeLaunchContextSubject(
          intent.context,
          fallbackSubject: source,
        );
        _showFeedback(
          buildLaunchArrivalMessage(
            arrivalContext,
            fallbackSubject: source,
            destination: 'AI Lab',
            verb: _arrivalVerbForAiLabLaunch(source, intent.context),
            includeWorkspaceBrief: false,
          ),
        );
      }
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.onLaunchIntentHandled?.call();
    });
  }

  WorkbenchLaunchContext? _contextForTab(_AiLabTab tab) {
    return _activeLaunchTab == tab ? _activeLaunchContext : null;
  }
}

String _arrivalVerbForAiLabLaunch(
  String sourceLabel,
  WorkbenchLaunchContext? context,
) {
  final source = sourceLabel.trim();
  final isGenericDutyAction = source.startsWith('Duty Actions ·');
  final isWorkbenchOpenTarget =
      context != null &&
      context.workspaceTarget == 'ai_runtime' &&
      context.cardTarget == 'runtime_product' &&
      (source.contains('开始模型训练') ||
          source.contains('构建知识库') ||
          source.contains('打开 AI Lab'));
  if (isGenericDutyAction || isWorkbenchOpenTarget) {
    return '已打开';
  }
  return '已送入';
}

String _recommendedAiLaneAction(
  WorkbenchLaunchContext? context, {
  required bool hasLatestAsset,
  required String runtimeActionKey,
  required String registryActionKey,
  required String timelineActionKey,
}) {
  switch (context?.cardTarget) {
    case 'registry_snapshot':
      return hasLatestAsset ? registryActionKey : runtimeActionKey;
    case 'version_timeline':
      return hasLatestAsset ? timelineActionKey : runtimeActionKey;
    case 'runtime_product':
      return runtimeActionKey;
    default:
      return hasLatestAsset ? registryActionKey : runtimeActionKey;
  }
}

int? _asInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value);
  }
  return null;
}

bool? _asBool(Object? value) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  if (value is String) {
    final normalized = value.toLowerCase();
    if (normalized == 'true' || normalized == '1') {
      return true;
    }
    if (normalized == 'false' || normalized == '0') {
      return false;
    }
  }
  return null;
}

DeepLearningModelType? _toModelType(String? value) {
  switch (value?.toLowerCase()) {
    case 'gru':
      return DeepLearningModelType.gru;
    case 'lstm':
      return DeepLearningModelType.lstm;
    default:
      return null;
  }
}

class _TrainingDatasetCard extends StatelessWidget {
  const _TrainingDatasetCard({
    required this.storageController,
    required this.targetController,
  });

  final TextEditingController storageController;
  final TextEditingController targetController;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('训练数据与目标列', style: AppTextStyles.h4),
          const SizedBox(height: 16),
          TextField(
            key: const ValueKey('ai-lab-training-storage-path'),
            controller: storageController,
            autofillHints: const <String>[],
            enableSuggestions: false,
            autocorrect: false,
            decoration: const InputDecoration(
              labelText: '训练数据路径',
              hintText: '例如: uploads/your-data.csv',
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey('ai-lab-training-target-column'),
            controller: targetController,
            autofillHints: const <String>[],
            enableSuggestions: false,
            autocorrect: false,
            decoration: const InputDecoration(
              labelText: '目标列',
              hintText: '例如: Load',
            ),
          ),
        ],
      ),
    );
  }
}

class _RagIngestCard extends StatelessWidget {
  const _RagIngestCard({
    required this.storageController,
    required this.collectionController,
    required this.resetCollection,
    required this.isSubmitting,
    required this.onResetChanged,
    required this.onSubmit,
  });

  final TextEditingController storageController;
  final TextEditingController collectionController;
  final bool resetCollection;
  final bool isSubmitting;
  final ValueChanged<bool> onResetChanged;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('知识库构建入口', style: AppTextStyles.h4),
          const SizedBox(height: 16),
          TextField(
            key: const ValueKey('ai-lab-knowledge-storage-path'),
            controller: storageController,
            autofillHints: const <String>[],
            enableSuggestions: false,
            autocorrect: false,
            decoration: const InputDecoration(
              labelText: '知识源路径',
              hintText: '例如: docs/ 或 uploads/manual.pdf',
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey('ai-lab-knowledge-collection'),
            controller: collectionController,
            autofillHints: const <String>[],
            enableSuggestions: false,
            autocorrect: false,
            decoration: const InputDecoration(
              labelText: '集合名称',
              hintText: '例如: default',
            ),
          ),
          const SizedBox(height: 12),
          SwitchListTile.adaptive(
            contentPadding: EdgeInsets.zero,
            title: const Text('重建集合'),
            subtitle: const Text('开启后会先清空已有同名集合。'),
            value: resetCollection,
            onChanged: isSubmitting ? null : onResetChanged,
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: isSubmitting ? null : onSubmit,
              icon: isSubmitting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.cloud_upload_rounded),
              label: Text(isSubmitting ? '提交中...' : '提交知识库构建任务'),
            ),
          ),
        ],
      ),
    );
  }
}
