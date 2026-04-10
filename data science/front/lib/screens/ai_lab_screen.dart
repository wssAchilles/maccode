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
import '../models/main_shell_projection.dart';
import '../models/shell_action_outcome.dart';
import '../models/workbench_launch_context.dart';
import '../utils/asset_chain_context.dart';
import '../utils/job_presentation.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../viewmodels/job_view_model.dart';
import '../viewmodels/rag_view_model.dart';
import '../widgets/common/glass_card.dart';
import '../widgets/deep_learning/deep_learning_config_panel.dart';
import '../widgets/deep_learning/deep_learning_terminal_panel.dart';
import '../widgets/deep_learning/training_result_visual_panel.dart';
import '../widgets/navigation/main_shell_runtime_scope.dart';
import '../widgets/operations/ai_lab_operations_board.dart';
import '../widgets/operations/ai_lab_asset_control_board.dart';
import '../widgets/operations/decision_layout.dart';
import '../widgets/operations/job_activity_list.dart';
import '../widgets/operations/job_event_timeline.dart';
import '../widgets/operations/lab_split_panel.dart';
import '../widgets/operations/workbench_page_frame.dart';
import '../widgets/rag/rag_input_area.dart';
import '../widgets/rag/rag_message_list.dart';
import '../widgets/responsive_wrapper.dart';

class AiLabScreen extends StatefulWidget {
  const AiLabScreen({
    super.key,
    required this.dashboardViewModel,
    this.trainingJobsViewModel,
    this.ragJobsViewModel,
    this.shellProjection,
    this.launchIntent,
    this.onLaunchIntentHandled,
    this.isActive = true,
    this.sharedRuntimeManaged = false,
    this.surfaceMode = WorkbenchSurfaceMode.standalone,
  });

  final DashboardViewModel dashboardViewModel;
  final JobViewModel? trainingJobsViewModel;
  final JobViewModel? ragJobsViewModel;
  final MainShellProjection? shellProjection;
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
  final _pageScrollController = ScrollController();
  final _ragScrollController = ScrollController();
  final _trainingResultKey = GlobalKey();
  final _trainingStatusKey = GlobalKey();
  final _ragValidationKey = GlobalKey();
  final _ragTrackingKey = GlobalKey();

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
  String? _lastTrainingResultFocusToken;
  String? _lastRagValidationFocusToken;
  DashboardSummary? get _sharedSummary => widget.sharedRuntimeManaged
      ? (widget.shellProjection?.summary ?? widget.dashboardViewModel.summary)
      : widget.dashboardViewModel.summary;

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
    _pageScrollController.dispose();
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
      _sharedSummary?.assetSummary,
    );
    final resolvedTargetColumn = _resolvedTrainingTargetColumn(
      _sharedSummary?.assetSummary,
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
      await _openJobInShellRuntime(job);
      _showFeedback(
        _chainFeedbackMessage(
          chain,
          prefix: '训练任务已提交',
          detail: job.jobId.substring(0, 8),
        ),
      );
      await _refreshSharedProjection();
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
      await _openJobInShellRuntime(job);
      _showFeedback(
        _chainFeedbackMessage(
          chain,
          prefix: '知识库构建任务已提交',
          detail: job.jobId.substring(0, 8),
        ),
      );
      await _refreshSharedProjection();
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
    await _ragViewModel.sendMessage(
      text,
      collectionName: _ragCollectionController.text.trim(),
    );
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

  AssetChainSummary? _chainForKey(String key) {
    return _sharedSummary?.assetSummary.chainSummaries
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
    final summary = _sharedSummary;
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
        final summary = _sharedSummary;
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
        final trainingFocusJob = _primaryJob(
          _trainingJobsViewModel.jobs,
          _trainingJobsViewModel.activeJob,
          preferVisualizedSuccess: true,
        );
        final ragFocusJob = _primaryJob(
          _ragJobsViewModel.jobs,
          _ragJobsViewModel.activeJob,
        );
        final trainingResultReady =
            trainingFocusJob?.hasTrainingVisualization == true;
        final ragValidationReady = _hasRagValidationReady(
          ragFocusJob,
          latestKnowledgeAsset,
        );
        _syncResolvedTrainingControllers(assetSummary);
        _queueTrainingPathRepair(assetSummary);
        final trainingError = _normalizeJobErrorMessage(
          _trainingJobsViewModel.errorMessage,
        );
        final ragError = _normalizeJobErrorMessage(
          _ragJobsViewModel.errorMessage,
        );
        final tabSwitcher = _buildTabSwitcher();
        _scheduleAiLabFocus(
          trainingFocusJob:
              _currentTab == _AiLabTab.deepLearning && trainingResultReady
              ? trainingFocusJob
              : null,
          ragFocusJob: _currentTab == _AiLabTab.rag && ragValidationReady
              ? ragFocusJob
              : null,
          latestKnowledgeAsset:
              _currentTab == _AiLabTab.rag && ragValidationReady
              ? latestKnowledgeAsset
              : null,
        );
        final content = ResponsiveWrapper(
          child: SingleChildScrollView(
            controller: _pageScrollController,
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                DecisionHeaderCard(
                  title: 'AI Lab',
                  summary: _currentTab == _AiLabTab.deepLearning
                      ? '先准备训练数据和配置，再跟进训练状态；资产治理与版本回填全部下沉。'
                      : '先确认知识路径和集合，再构建知识库并直接验证问答结果。',
                  metrics: [
                    DecisionHeaderMetric(
                      label: '当前车道',
                      value: _currentTab == _AiLabTab.deepLearning
                          ? '深度学习'
                          : 'RAG',
                      helper: '当前唯一主流程',
                      accent: _currentTab == _AiLabTab.deepLearning
                          ? AppColors.cta
                          : AppColors.success,
                      icon: _currentTab == _AiLabTab.deepLearning
                          ? Icons.model_training_rounded
                          : Icons.auto_awesome_rounded,
                    ),
                    DecisionHeaderMetric(
                      label: '训练状态',
                      value: trainingFocusJob != null
                          ? buildJobPrimaryText(trainingFocusJob)
                          : (_trainingJobsViewModel.jobs.isEmpty ? '空闲' : '就绪'),
                      helper: '最近训练任务',
                      accent: trainingError != null
                          ? AppColors.error
                          : (trainingFocusJob?.isRunning == true
                                ? AppColors.warning
                                : trainingResultReady
                                ? AppColors.success
                                : AppColors.primary),
                      icon: Icons.model_training_rounded,
                    ),
                    DecisionHeaderMetric(
                      label: '知识状态',
                      value: ragFocusJob != null
                          ? buildJobPrimaryText(ragFocusJob)
                          : (_ragJobsViewModel.jobs.isEmpty ? '空闲' : '就绪'),
                      helper: '最近知识任务',
                      accent: ragError != null
                          ? AppColors.error
                          : (ragFocusJob?.isRunning == true
                                ? AppColors.warning
                                : ragValidationReady
                                ? AppColors.success
                                : AppColors.success),
                      icon: Icons.auto_stories_rounded,
                    ),
                    DecisionHeaderMetric(
                      label: '最近资产',
                      value: _currentTab == _AiLabTab.deepLearning
                          ? (latestModelAsset == null ? '暂无模型' : '模型已就绪')
                          : (latestKnowledgeAsset == null ? '暂无快照' : '快照已就绪'),
                      helper: _currentTab == _AiLabTab.deepLearning
                          ? '模型产物回填'
                          : '知识快照回填',
                      accent: AppColors.primary,
                      icon: Icons.inventory_2_rounded,
                    ),
                  ],
                  primaryAction: _buildPrimaryAction(
                    trainingFocusJob: trainingFocusJob,
                    ragFocusJob: ragFocusJob,
                    latestKnowledgeAsset: latestKnowledgeAsset,
                  ),
                  banner: _buildAiLabBanner(
                    trainingError: trainingError,
                    ragError: ragError,
                    latestModelAsset: latestModelAsset,
                    latestKnowledgeAsset: latestKnowledgeAsset,
                  ),
                ),
                const SizedBox(height: 20),
                PrimaryWorkflowPanel(
                  eyebrow: _currentTab == _AiLabTab.deepLearning
                      ? '训练数据 -> 训练配置 -> 训练状态'
                      : '知识路径 -> 构建入口 -> 问答面板',
                  title: _currentTab == _AiLabTab.deepLearning
                      ? '深度学习主流程'
                      : '知识助手主流程',
                  summary: _currentTab == _AiLabTab.deepLearning
                      ? (trainingResultReady
                            ? '训练结果已置顶展示，输入表单和日志已下沉到结果下方。'
                            : (trainingFocusJob?.isRunning == true
                                  ? '训练已进入运行态，首屏优先跟进阶段轨迹和关键进度。'
                                  : '首屏只保留训练输入、训练配置和训练状态。'))
                      : (ragValidationReady
                            ? '知识问答验证已置顶，构建入口和日志已下沉到结果下方。'
                            : (ragFocusJob?.isRunning == true
                                  ? '知识构建已进入运行态，首屏优先跟进构建轨迹。'
                                  : '首屏只保留知识路径、构建入口和问答验证。')),
                  trailing: widget.surfaceMode.isEmbedded ? tabSwitcher : null,
                  child: _currentTab == _AiLabTab.deepLearning
                      ? _buildDeepLearningTab()
                      : _buildRagTab(latestKnowledgeAsset),
                ),
                const SizedBox(height: 20),
                ProgressiveDetailSection(
                  title: '任务与资产治理',
                  summary: '实验态摘要、资产回填、护照复制和版本治理统一下沉到这里。',
                  icon: Icons.account_tree_rounded,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
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
                            _chainAssetActionMessage(
                              modelChain,
                              prefix: '模型路径已复制',
                            ),
                          );
                        },
                        onApplyKnowledgeSnapshot: (job) {
                          _applyKnowledgeSnapshot(job, chain: knowledgeChain);
                        },
                        onCopyCollection: (collection) {
                          _copyText(
                            collection,
                            _chainAssetActionMessage(
                              knowledgeChain,
                              prefix: '集合名已复制',
                            ),
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
                    ],
                  ),
                ),
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

  Widget _buildAiLabBanner({
    required String? trainingError,
    required String? ragError,
    required AssetModel? latestModelAsset,
    required KnowledgeAsset? latestKnowledgeAsset,
  }) {
    if (_currentTab == _AiLabTab.deepLearning) {
      if (trainingError != null) {
        return DecisionBanner(
          title: '训练提交需要复核',
          message: trainingError,
          accent: AppColors.error,
          icon: Icons.error_outline_rounded,
        );
      }
      if (latestModelAsset != null) {
        return const DecisionBanner(
          title: '已有最近模型资产',
          message: '可以直接回填最近模型资产，或调整配置后重新发起训练。',
          accent: AppColors.primary,
          icon: Icons.cloud_done_rounded,
        );
      }
      return const DecisionBanner(
        title: '先准备训练输入',
        message: '填写存储路径和目标列后，首屏会继续跟进训练状态。',
        accent: AppColors.cta,
        icon: Icons.model_training_rounded,
      );
    }

    if (ragError != null) {
      return DecisionBanner(
        title: '知识构建需要复核',
        message: ragError,
        accent: AppColors.error,
        icon: Icons.error_outline_rounded,
      );
    }
    if (latestKnowledgeAsset != null) {
      return const DecisionBanner(
        title: '已有最近知识快照',
        message: '可以直接回填最近知识快照，或更换集合后重新构建。',
        accent: AppColors.success,
        icon: Icons.library_add_check_rounded,
      );
    }
    return const DecisionBanner(
      title: '先构建知识库',
      message: '填写知识路径后先完成一次构建，再在首屏直接验证问答结果。',
      accent: AppColors.success,
      icon: Icons.auto_awesome_rounded,
    );
  }

  Widget _buildDeepLearningTab() {
    final focusJob = _primaryJob(
      _trainingJobsViewModel.jobs,
      _trainingJobsViewModel.activeJob,
      preferVisualizedSuccess: true,
    );
    final logs = _buildTrainingLogOutput(focusJob);
    final trainingInputPanel = Column(
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
    );
    final trainingStatusPanel = KeyedSubtree(
      key: _trainingStatusKey,
      child: Column(
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
    final resultReady = focusJob != null && focusJob.hasTrainingVisualization;
    final statusFirst = resultReady || focusJob?.isRunning == true;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (resultReady) ...[
          KeyedSubtree(
            key: _trainingResultKey,
            child: DeepLearningTrainingResultPanel(job: focusJob),
          ),
          const SizedBox(height: 16),
        ],
        LabSplitPanel(
          left: statusFirst ? trainingStatusPanel : trainingInputPanel,
          right: statusFirst ? trainingInputPanel : trainingStatusPanel,
        ),
      ],
    );
  }

  Widget _buildRagTab(KnowledgeAsset? latestKnowledgeAsset) {
    final focusJob = _primaryJob(
      _ragJobsViewModel.jobs,
      _ragJobsViewModel.activeJob,
    );
    final ingestPanel = Column(
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
    );
    final validationReady = _hasRagValidationReady(
      focusJob,
      latestKnowledgeAsset,
    );
    final trackingPanel = KeyedSubtree(
      key: _ragTrackingKey,
      child: Column(
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
          if (!validationReady)
            _buildRagValidationPanel(
              statusLabel:
                  focusJob?.statusMessage ??
                  latestKnowledgeAsset?.collection ??
                  '默认知识库',
            ),
        ],
      ),
    );
    final statusFirst = validationReady || focusJob?.isRunning == true;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (validationReady) ...[
          KeyedSubtree(
            key: _ragValidationKey,
            child: _buildRagValidationPanel(
              statusLabel:
                  focusJob?.statusMessage ??
                  latestKnowledgeAsset?.collection ??
                  '默认知识库',
            ),
          ),
          const SizedBox(height: 16),
        ],
        LabSplitPanel(
          left: statusFirst ? trackingPanel : ingestPanel,
          right: statusFirst ? ingestPanel : trackingPanel,
        ),
      ],
    );
  }

  Widget _buildRagValidationPanel({required String statusLabel}) {
    return SizedBox(
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
                  Text(statusLabel, style: AppTextStyles.bodySmall),
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
    );
  }

  String _buildTrainingLogOutput(JobRecord? focusJob) {
    if (focusJob == null) {
      return '等待提交训练任务。\n请先填写训练数据路径和目标列。';
    }

    final buffer = StringBuffer();
    buffer.writeln(
      '[${buildJobPrimaryText(focusJob)}] ${focusJob.displayTitle}',
    );
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

  DecisionHeaderAction _buildPrimaryAction({
    required JobRecord? trainingFocusJob,
    required JobRecord? ragFocusJob,
    required KnowledgeAsset? latestKnowledgeAsset,
  }) {
    if (_currentTab == _AiLabTab.deepLearning) {
      if (trainingFocusJob?.hasTrainingVisualization == true) {
        return DecisionHeaderAction(
          label: '查看训练结果',
          icon: Icons.insights_rounded,
          onTap: _scrollToTrainingResult,
          isPrimary: true,
        );
      }
      if (trainingFocusJob?.isRunning == true) {
        return DecisionHeaderAction(
          label: '查看运行详情',
          icon: Icons.monitor_rounded,
          onTap: widget.sharedRuntimeManaged
              ? () => _openJobInShellRuntime(trainingFocusJob!)
              : _scrollToTrainingStatus,
          isPrimary: true,
        );
      }
      return DecisionHeaderAction(
        label: '启动云端训练',
        icon: Icons.play_arrow_rounded,
        onTap: _canSubmitTraining() ? _submitTrainingJob : null,
        isPrimary: true,
      );
    }

    if (_hasRagValidationReady(ragFocusJob, latestKnowledgeAsset)) {
      return DecisionHeaderAction(
        label: '验证知识问答',
        icon: Icons.question_answer_rounded,
        onTap: _scrollToRagValidation,
        isPrimary: true,
      );
    }
    if (ragFocusJob?.isRunning == true) {
      return DecisionHeaderAction(
        label: '查看构建进度',
        icon: Icons.auto_awesome_motion_rounded,
        onTap: widget.sharedRuntimeManaged
            ? () => _openJobInShellRuntime(ragFocusJob!)
            : _scrollToRagTracking,
        isPrimary: true,
      );
    }
    return DecisionHeaderAction(
      label: '提交知识构建',
      icon: Icons.library_add_rounded,
      onTap: _canSubmitRag() ? _submitRagIngestJob : null,
      isPrimary: true,
    );
  }

  bool _canSubmitTraining() {
    final assetSummary = _sharedSummary?.assetSummary;
    final storagePath =
        _resolvedTrainingStoragePath(assetSummary) ??
        _trainingStorageController.text.trim();
    final targetColumn =
        _resolvedTrainingTargetColumn(assetSummary) ??
        _trainingTargetController.text.trim();
    return storagePath.isNotEmpty && targetColumn.isNotEmpty;
  }

  bool _canSubmitRag() {
    return _ragStorageController.text.trim().isNotEmpty &&
        _ragCollectionController.text.trim().isNotEmpty;
  }

  bool _hasRagValidationReady(
    JobRecord? focusJob,
    KnowledgeAsset? latestKnowledgeAsset,
  ) {
    return focusJob?.status == 'succeeded' ||
        latestKnowledgeAsset != null ||
        _ragViewModel.messages.isNotEmpty;
  }

  void _scheduleAiLabFocus({
    required JobRecord? trainingFocusJob,
    required JobRecord? ragFocusJob,
    required KnowledgeAsset? latestKnowledgeAsset,
  }) {
    final trainingToken = trainingFocusJob == null
        ? null
        : '${trainingFocusJob.jobId}:${trainingFocusJob.status}:${trainingFocusJob.hasTrainingVisualization}';
    if (trainingToken != null &&
        trainingToken != _lastTrainingResultFocusToken) {
      _lastTrainingResultFocusToken = trainingToken;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _scrollToTrainingResult();
      });
    }

    final ragToken = ragFocusJob != null
        ? '${ragFocusJob.jobId}:${ragFocusJob.status}'
        : latestKnowledgeAsset == null
        ? null
        : '${latestKnowledgeAsset.jobId}:${latestKnowledgeAsset.version}';
    if (ragToken != null && ragToken != _lastRagValidationFocusToken) {
      _lastRagValidationFocusToken = ragToken;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _scrollToRagValidation();
      });
    }
  }

  Future<void> _scrollToTrainingResult() async {
    await _ensureVisible(_trainingResultKey);
  }

  Future<void> _scrollToTrainingStatus() async {
    await _ensureVisible(_trainingStatusKey);
  }

  Future<void> _scrollToRagValidation() async {
    await _ensureVisible(_ragValidationKey);
  }

  Future<void> _scrollToRagTracking() async {
    await _ensureVisible(_ragTrackingKey);
  }

  Future<void> _ensureVisible(GlobalKey key) async {
    final context = key.currentContext;
    if (context == null) {
      return;
    }
    await Scrollable.ensureVisible(
      context,
      duration: const Duration(milliseconds: 280),
      curve: Curves.easeOutCubic,
      alignment: 0.08,
    );
  }

  JobRecord? _primaryJob(
    List<JobRecord> jobs,
    JobRecord? activeJob, {
    bool preferVisualizedSuccess = false,
  }) {
    if (activeJob != null) {
      return activeJob;
    }
    if (jobs.isEmpty) {
      return null;
    }
    if (preferVisualizedSuccess) {
      final successfulVisualized = jobs.cast<JobRecord?>().firstWhere(
        (job) =>
            job?.status == 'succeeded' && job?.hasTrainingVisualization == true,
        orElse: () => null,
      );
      if (successfulVisualized != null) {
        return successfulVisualized;
      }
    }
    return jobs.first;
  }

  Future<void> _retryJob(JobViewModel viewModel, JobRecord job) async {
    final runtime = widget.sharedRuntimeManaged
        ? MainShellRuntimeScope.maybeOf(context)
        : null;
    if (runtime != null) {
      final outcome = await runtime.retrySharedJob(job);
      if (!mounted) {
        return;
      }
      _showSharedActionOutcome(outcome);
      return;
    }

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
      await _refreshSharedProjection();
      return;
    }
    final message = _normalizeJobErrorMessage(viewModel.errorMessage);
    if (message != null) {
      _showFeedback(message, color: AppColors.error);
    }
  }

  Future<void> _cancelJob(JobViewModel viewModel, JobRecord job) async {
    final runtime = widget.sharedRuntimeManaged
        ? MainShellRuntimeScope.maybeOf(context)
        : null;
    if (runtime != null) {
      final outcome = await runtime.cancelSharedJob(job);
      if (!mounted) {
        return;
      }
      _showSharedActionOutcome(outcome);
      return;
    }

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
      await _refreshSharedProjection();
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
    final runtime = widget.sharedRuntimeManaged
        ? MainShellRuntimeScope.maybeOf(context)
        : null;
    if (runtime != null) {
      final outcome = await runtime.resolveSharedJobApproval(
        job,
        approved: approved,
      );
      if (!mounted) {
        return;
      }
      _showSharedActionOutcome(outcome);
      return;
    }

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
        _chainFeedbackMessage(chain, prefix: approved ? '任务已批准执行' : '任务已驳回'),
      );
      await _refreshSharedProjection();
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

  void _showSharedActionOutcome(ShellActionOutcome outcome) {
    final color = switch (outcome.tone) {
      ShellActionTone.success => AppColors.success,
      ShellActionTone.warning => AppColors.warning,
      ShellActionTone.error => AppColors.error,
      ShellActionTone.info => AppColors.primary,
    };
    _showFeedback(outcome.message, color: color);
  }

  Future<void> _refreshSharedProjection() async {
    if (widget.sharedRuntimeManaged) {
      final runtime = MainShellRuntimeScope.maybeOf(context);
      if (runtime != null) {
        await runtime.refreshSharedSnapshot(force: true);
        return;
      }
    }
    await widget.dashboardViewModel.loadSummary();
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
