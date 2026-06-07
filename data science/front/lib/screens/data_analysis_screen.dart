/// 数据分析页面 - Glassmorphism 设计
/// 完整功能实现
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:file_picker/file_picker.dart';
import '../config/app_theme.dart';
import '../models/ai_lab_launch_intent.dart';
import '../models/dashboard_summary.dart';
import '../models/job_record.dart';
import '../models/main_shell_projection.dart';
import '../models/data_analysis_launch_intent.dart';
import '../models/shell_action_outcome.dart';
import '../models/workbench_launch_context.dart';
import '../utils/asset_chain_context.dart';
import '../widgets/responsive_wrapper.dart';
import '../models/analysis_result.dart';
import '../models/history_record.dart';
import '../widgets/analysis/analysis_results_section.dart';
import '../widgets/analysis/data_asset_governance_board.dart';
import '../widgets/analysis/data_analysis_sliver_app_bar.dart';
import '../widgets/analysis/data_analysis_state_views.dart';
import '../widgets/analysis/data_analysis_top_section.dart';
import '../widgets/analysis/data_analysis_workbench.dart';
import '../widgets/analysis/data_analysis_operations_board.dart';
import '../widgets/common/glass_card.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../viewmodels/data_analysis_view_model.dart';
import '../viewmodels/data_analysis_workflow_coordinator.dart';
import '../viewmodels/data_drift_view_model.dart';
import '../viewmodels/history_view_model.dart';
import '../viewmodels/job_view_model.dart';
import '../widgets/navigation/main_shell_runtime_scope.dart';
import '../widgets/operations/job_activity_list.dart';
import '../widgets/operations/job_event_timeline.dart';
import '../widgets/operations/decision_layout.dart';
import '../widgets/operations/workbench_page_frame.dart';

class DataAnalysisScreen extends StatefulWidget {
  const DataAnalysisScreen({
    super.key,
    this.onOpenHistory,
    this.onSendToAiLab,
    this.dashboardViewModel,
    this.viewModel,
    this.analysisJobsViewModel,
    this.shellProjection,
    this.launchIntent,
    this.onLaunchIntentHandled,
    this.isActive = true,
    this.sharedRuntimeManaged = false,
    this.surfaceMode = WorkbenchSurfaceMode.standalone,
  });

  final VoidCallback? onOpenHistory;
  final ValueChanged<AiLabLaunchIntent>? onSendToAiLab;
  final DashboardViewModel? dashboardViewModel;
  final DataAnalysisViewModel? viewModel;
  final JobViewModel? analysisJobsViewModel;
  final MainShellProjection? shellProjection;
  final DataAnalysisLaunchIntent? launchIntent;
  final VoidCallback? onLaunchIntentHandled;
  final bool isActive;
  final bool sharedRuntimeManaged;
  final WorkbenchSurfaceMode surfaceMode;

  @override
  State<DataAnalysisScreen> createState() => _DataAnalysisScreenState();
}

class _DataAnalysisScreenState extends State<DataAnalysisScreen> {
  // 表单控制器
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  final _pageScrollController = ScrollController();
  final _analysisResultKey = GlobalKey();
  late final DataAnalysisViewModel _viewModel;
  late final DashboardViewModel _dashboardViewModel;
  late final JobViewModel _analysisJobsViewModel;
  late final HistoryViewModel _historyViewModel;
  late final DataDriftViewModel _driftViewModel;
  late final DataAnalysisWorkflowCoordinator _workflowCoordinator;
  late final bool _ownsViewModel;
  late final bool _ownsDashboardViewModel;
  late final bool _ownsAnalysisJobsViewModel;
  WorkbenchLaunchContext? _activeLaunchContext;
  String? _selectedReferencePath;
  Set<String>? _selectedDriftFeatures;
  bool _didActivateWorkspace = false;

  User? get _currentUser => _viewModel.currentUser;
  PlatformFile? get _pickedFile => _viewModel.pickedFile;
  AnalysisResult? get _analysisResult => _viewModel.analysisResult;
  String? get _latestStoragePath => _viewModel.latestStoragePath;
  bool get _isLoading => _viewModel.isLoading;
  bool get _isSubmittingAnalysisJob => _viewModel.isSubmittingAnalysisJob;
  bool get _saveToStorage => _viewModel.saveToStorage;
  String? get _errorMessage => _viewModel.errorMessage;
  String get _authMode => _viewModel.authMode;
  DashboardSummary? get _sharedSummary => widget.sharedRuntimeManaged
      ? (widget.shellProjection?.summary ?? _dashboardViewModel.summary)
      : _dashboardViewModel.summary;

  static const _defaultErrorDuration = Duration(seconds: 4);
  static const _analysisErrorDuration = Duration(seconds: 5);

  @override
  void initState() {
    super.initState();
    _ownsViewModel = widget.viewModel == null;
    _ownsDashboardViewModel = widget.dashboardViewModel == null;
    _viewModel = widget.viewModel ?? DataAnalysisViewModel();
    _dashboardViewModel = widget.dashboardViewModel ?? DashboardViewModel();
    _analysisJobsViewModel =
        widget.analysisJobsViewModel ??
        JobViewModel(jobType: 'analysis', limit: 8);
    _ownsAnalysisJobsViewModel = widget.analysisJobsViewModel == null;
    _historyViewModel = HistoryViewModel();
    _driftViewModel = DataDriftViewModel();
    _workflowCoordinator = DataAnalysisWorkflowCoordinator(
      viewModel: _viewModel,
      analysisJobsViewModel: _analysisJobsViewModel,
      refreshSharedProjection: _refreshSharedProjection,
      openJob: _openJobInShellRuntime,
      showError: _showViewModelError,
      showSuccess: _showSuccessFeedback,
      focusAnalysisResult: _focusAnalysisResult,
      datasetFeedbackMessage: _datasetFeedbackMessage,
      isMounted: () => mounted,
    );
    _applyLaunchIntent(widget.launchIntent);
    _handleWorkspaceActivation(widget.isActive);
  }

  @override
  void didUpdateWidget(covariant DataAnalysisScreen oldWidget) {
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
    if (_ownsViewModel) {
      _viewModel.dispose();
    }
    if (_ownsDashboardViewModel) {
      _dashboardViewModel.dispose();
    }
    if (_ownsAnalysisJobsViewModel) {
      _analysisJobsViewModel.dispose();
    }
    _historyViewModel.dispose();
    _driftViewModel.dispose();
    _pageScrollController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _handleWorkspaceActivation(bool isActive) {
    if (!widget.sharedRuntimeManaged) {
      _analysisJobsViewModel.setWorkspaceActive(isActive);
    }
    if (!isActive) {
      return;
    }
    if (!_didActivateWorkspace) {
      _didActivateWorkspace = true;
      _viewModel.initialize();
      if (!widget.sharedRuntimeManaged) {
        _dashboardViewModel.initialize();
        _analysisJobsViewModel.loadJobs();
      }
      _historyViewModel.loadHistory(limit: 12);
    }
  }

  /// 使用 Google 登录
  Future<void> _signInWithGoogle() async {
    final user = await _viewModel.signInWithGoogle();
    if (!mounted) return;
    if (user == null) {
      _showViewModelError();
    }
  }

  /// 邮箱密码登录
  Future<void> _signInWithEmail() async {
    await _submitEmailAuth(
      action: ({required email, required password}) {
        return _viewModel.signInWithEmail(email: email, password: password);
      },
      successMessage: (user) => '欢迎回来, ${user.email ?? "用户"}!',
    );
  }

  /// 邮箱密码注册
  Future<void> _registerWithEmail() async {
    await _submitEmailAuth(
      action: ({required email, required password}) {
        return _viewModel.registerWithEmail(email: email, password: password);
      },
      successMessage: (user) => '注册成功！欢迎, ${user.email}!',
    );
  }

  Future<void> _submitEmailAuth({
    required Future<User?> Function({
      required String email,
      required String password,
    })
    action,
    required String Function(User user) successMessage,
  }) async {
    if (!_formKey.currentState!.validate()) return;

    final user = await action(
      email: _emailController.text.trim(),
      password: _passwordController.text,
    );
    if (!mounted) return;
    if (user != null) {
      _showSuccessFeedback(successMessage(user));
      return;
    }

    _showViewModelError();
  }

  /// 登出
  Future<void> _signOut() async {
    try {
      await _viewModel.signOut();
      if (!mounted) return;
      _emailController.clear();
      _passwordController.clear();
    } catch (e) {
      if (!mounted) return;
      _showFeedback(message: '登出失败: $e', backgroundColor: AppColors.error);
    }
  }

  /// 选择文件
  Future<void> _pickFile() async {
    await _workflowCoordinator.pickFile();
  }

  /// 开始分析 - 核心功能
  Future<void> _startAnalysis() async {
    await _workflowCoordinator.startAnalysis(
      currentUser: _currentUser,
      pickedFile: _pickedFile,
      errorDuration: _analysisErrorDuration,
    );
  }

  Future<void> _submitAnalysisJob() async {
    await _workflowCoordinator.submitAnalysisJob(
      errorDuration: _analysisErrorDuration,
    );
  }

  void _openHistory() {
    final onOpenHistory = widget.onOpenHistory;
    if (onOpenHistory != null) {
      onOpenHistory();
      return;
    }

    _showFeedback(
      message: '历史与审计是顶级工作台，请通过主导航进入。',
      backgroundColor: AppColors.primary,
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([
        _viewModel,
        _dashboardViewModel,
        _analysisJobsViewModel,
        _historyViewModel,
        _driftViewModel,
      ]),
      builder: (context, _) {
        final datasetChain = _sharedSummary?.assetSummary.chainSummaries
            .cast<AssetChainSummary?>()
            .firstWhere((item) => item?.key == 'dataset', orElse: () => null);
        final resultReady = _analysisResult != null;
        final controls = DataAnalysisTopSection(
          currentUser: _currentUser,
          pickedFile: _pickedFile,
          saveToStorage: _saveToStorage,
          formKey: _formKey,
          emailController: _emailController,
          passwordController: _passwordController,
          authMode: _authMode,
          onSignInWithEmail: _signInWithEmail,
          onRegisterWithEmail: _registerWithEmail,
          onToggleAuthMode: _viewModel.toggleAuthMode,
          onGoogleSignIn: _signInWithGoogle,
          onPickFile: _pickFile,
          onClearFile: _viewModel.clearPickedFile,
          onStorageChanged: _viewModel.setSaveToStorage,
        );
        final commandDeck = DataAnalysisCommandDeck(
          isAuthenticated: _currentUser != null,
          hasFile: _pickedFile != null,
          isLoading: _isLoading,
          isSubmittingBackgroundAnalysis: _isSubmittingAnalysisJob,
          saveToStorage: _saveToStorage,
          analysisResult: _analysisResult,
          onStartAnalysis: _startAnalysis,
          onSubmitBackgroundAnalysis: _submitAnalysisJob,
          onOpenHistory: _openHistory,
        );
        final analysisResultPanel = KeyedSubtree(
          key: _analysisResultKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildWorkflowActions(),
              const SizedBox(height: 24),
              _buildResultsSection(),
            ],
          ),
        );
        final primaryAction = DecisionHeaderAction(
          label: resultReady
              ? '查看分析结果'
              : (_currentUser == null
                    ? '连接账号'
                    : (_pickedFile == null ? '上传数据' : '开始分析')),
          icon: resultReady
              ? Icons.insights_rounded
              : (_currentUser == null
                    ? Icons.lock_open_rounded
                    : (_pickedFile == null
                          ? Icons.upload_file_rounded
                          : Icons.play_arrow_rounded)),
          onTap: resultReady
              ? _focusAnalysisResult
              : (_currentUser != null && _pickedFile != null
                    ? _startAnalysis
                    : null),
          isPrimary: true,
        );
        final content = _isLoading
            ? DataAnalysisLoadingView(isAuthenticated: _currentUser != null)
            : CustomScrollView(
                controller: _pageScrollController,
                slivers: [
                  if (widget.surfaceMode.isStandalone)
                    DataAnalysisSliverAppBar(
                      isLoggedIn: _currentUser != null,
                      onOpenHistory: _openHistory,
                      onSignOut: _signOut,
                    ),
                  SliverToBoxAdapter(
                    child: ResponsiveWrapper(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            DecisionHeaderCard(
                              title: '数据分析工作流',
                              summary: '上传数据后先看质量，再看分析结果，最后决定是否交给 AI。',
                              metrics: [
                                DecisionHeaderMetric(
                                  label: '会话状态',
                                  value: _currentUser == null ? '未登录' : '已连接',
                                  helper: _currentUser == null
                                      ? '登录后才能发起云端分析'
                                      : '可访问私有数据与历史资产',
                                  accent: _currentUser == null
                                      ? AppColors.warning
                                      : AppColors.success,
                                  icon: _currentUser == null
                                      ? Icons.lock_outline_rounded
                                      : Icons.verified_user_rounded,
                                ),
                                DecisionHeaderMetric(
                                  label: '当前数据集',
                                  value: _pickedFile?.name ?? '未选择',
                                  helper: '支持单个 CSV 文件',
                                  accent: _pickedFile == null
                                      ? AppColors.textSecondary
                                      : AppColors.primary,
                                  icon: _pickedFile == null
                                      ? Icons.upload_file_outlined
                                      : Icons.dataset_rounded,
                                ),
                                DecisionHeaderMetric(
                                  label: '质量评分',
                                  value:
                                      _analysisResult
                                              ?.qualityAnalysis
                                              ?.qualityScore ==
                                          null
                                      ? '待分析'
                                      : '${_analysisResult!.qualityAnalysis!.qualityScore!.toStringAsFixed(0)} / 100',
                                  helper: '分析后更新',
                                  accent:
                                      (_analysisResult
                                                  ?.qualityAnalysis
                                                  ?.qualityScore ??
                                              0) >=
                                          80
                                      ? AppColors.success
                                      : AppColors.warning,
                                  icon: Icons.health_and_safety_rounded,
                                ),
                                DecisionHeaderMetric(
                                  label: '高风险列',
                                  value:
                                      '${_analysisResult?.qualityAnalysis?.highRiskColumns?.length ?? 0}',
                                  helper: '优先治理字段',
                                  accent:
                                      (_analysisResult
                                                  ?.qualityAnalysis
                                                  ?.highRiskColumns
                                                  ?.length ??
                                              0) >
                                          0
                                      ? AppColors.error
                                      : AppColors.cta,
                                  icon: Icons.warning_amber_rounded,
                                ),
                              ],
                              primaryAction: primaryAction,
                              banner: _buildAnalysisBanner(),
                            ),
                            const SizedBox(height: 24),
                            PrimaryWorkflowPanel(
                              eyebrow: '上传数据 -> 质量检查 -> 分析结果 -> 交给 AI',
                              title: resultReady ? '分析结果' : '当前分析流程',
                              summary: resultReady
                                  ? '结果与 AI 交接已经置顶展示，上传、认证和治理区已下沉到详情区。'
                                  : '认证、上传和分析操作只保留在一个主面板里，Storage Path、治理和任务队列全部下沉。',
                              child: resultReady
                                  ? analysisResultPanel
                                  : LayoutBuilder(
                                      builder: (context, constraints) {
                                        final stacked =
                                            constraints.maxWidth < 1120;
                                        if (stacked) {
                                          return Column(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.stretch,
                                            children: [
                                              controls,
                                              const SizedBox(height: 20),
                                              commandDeck,
                                            ],
                                          );
                                        }

                                        return Row(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Expanded(flex: 7, child: controls),
                                            const SizedBox(width: 20),
                                            Expanded(
                                              flex: 4,
                                              child: commandDeck,
                                            ),
                                          ],
                                        );
                                      },
                                    ),
                            ),
                            const SizedBox(height: 24),
                            ProgressiveDetailSection(
                              title: resultReady ? '上传、任务与治理' : '任务与治理',
                              summary: resultReady
                                  ? '上传区、后台任务、Storage Path 和治理面板已经下沉到这里，避免继续占据首屏。'
                                  : '后台任务、数据链路状态、Storage Path 和治理面板统一下沉到这里。',
                              icon: Icons.account_tree_rounded,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  if (resultReady) ...[
                                    LayoutBuilder(
                                      builder: (context, constraints) {
                                        final stacked =
                                            constraints.maxWidth < 1120;
                                        if (stacked) {
                                          return Column(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.stretch,
                                            children: [
                                              controls,
                                              const SizedBox(height: 20),
                                              commandDeck,
                                            ],
                                          );
                                        }

                                        return Row(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Expanded(flex: 7, child: controls),
                                            const SizedBox(width: 20),
                                            Expanded(
                                              flex: 4,
                                              child: commandDeck,
                                            ),
                                          ],
                                        );
                                      },
                                    ),
                                    const SizedBox(height: 24),
                                  ],
                                  DataAnalysisOperationsBoard(
                                    chain: datasetChain,
                                    continuationContext: _activeLaunchContext,
                                    currentUser: _currentUser,
                                    pickedFile: _pickedFile,
                                    analysisResult: _analysisResult,
                                    saveToStorage: _saveToStorage,
                                    latestStoragePath: _latestStoragePath,
                                    jobs: _analysisJobsViewModel.jobs,
                                    jobsLoading:
                                        _analysisJobsViewModel.isLoading,
                                    jobErrorMessage:
                                        _analysisJobsViewModel.errorMessage,
                                  ),
                                  const SizedBox(height: 24),
                                  _buildAnalysisJobPanel(),
                                  if (_errorMessage != null) ...[
                                    const SizedBox(height: 16),
                                    DataAnalysisErrorBanner(
                                      message: _errorMessage!,
                                      onDismiss: _viewModel.clearError,
                                    ),
                                  ],
                                  if (_analysisResult != null) ...[
                                    const SizedBox(height: 24),
                                    _buildAssetGovernanceBoard(),
                                  ],
                                ],
                              ),
                            ),
                            const SizedBox(height: 32),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              );

        return WorkbenchPageFrame(
          surfaceMode: widget.surfaceMode,
          body: content,
        );
      },
    );
  }

  Widget _buildAnalysisBanner() {
    if (_errorMessage != null) {
      return DecisionBanner(
        title: '分析需要复核',
        message: _errorMessage!,
        accent: AppColors.error,
        icon: Icons.error_outline_rounded,
      );
    }

    final result = _analysisResult;
    final qualityScore = result?.qualityAnalysis?.qualityScore;
    final riskCount = result?.qualityAnalysis?.highRiskColumns?.length ?? 0;
    if (result != null) {
      return DecisionBanner(
        title: riskCount > 0 ? '已发现治理重点' : '分析结果已生成',
        message: qualityScore == null
            ? '当前结果已生成，可以继续查看统计、相关性和 AI 交接。'
            : '质量评分 ${qualityScore.toStringAsFixed(0)} / 100，${riskCount == 0 ? "当前没有高风险列" : "共有 $riskCount 个高风险字段需要优先处理"}。',
        accent: riskCount > 0 ? AppColors.warning : AppColors.success,
        icon: riskCount > 0
            ? Icons.warning_amber_rounded
            : Icons.task_alt_rounded,
      );
    }

    return const DecisionBanner(
      title: '先完成一次分析',
      message: '登录并上传 CSV 后，首屏会直接给出质量结果和下一步 AI 交接入口。',
      accent: AppColors.primary,
      icon: Icons.insights_rounded,
    );
  }

  /// 结果展示部分 - 响应式布局
  Widget _buildResultsSection() {
    if (_analysisResult == null) return const SizedBox.shrink();
    final datasetChain = _dashboardViewModel
        .summary
        ?.assetSummary
        .chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((item) => item?.key == 'dataset', orElse: () => null);
    return AnalysisResultsSection(
      result: _analysisResult!,
      chain: datasetChain,
      continuationContext: _activeLaunchContext,
    );
  }

  Widget _buildWorkflowActions() {
    final result = _analysisResult;
    if (result == null) {
      return const SizedBox.shrink();
    }
    final datasetChain = _dashboardViewModel
        .summary
        ?.assetSummary
        .chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((item) => item?.key == 'dataset', orElse: () => null);
    final referenceAssets = _availableReferenceAssets();
    final referenceAsset = referenceAssets.cast<HistoryRecord?>().firstWhere(
      (item) => item?.storageUrl == _effectiveReferencePath(referenceAssets),
      orElse: () => null,
    );
    final compareDigest = _buildCompareDigest(
      result,
      referenceAsset: referenceAsset,
      driftStatus: _driftViewModel.report?.overallStatus,
      recommendation: _driftViewModel.report?.recommendation,
    );

    return DataAnalysisWorkflowActionsCard(
      chain: datasetChain,
      continuationContext: _activeLaunchContext,
      storagePath: _latestStoragePath,
      savedAsAsset: _saveToStorage,
      schemaDigest: _buildSchemaDigest(result),
      governanceDigest: _buildGovernanceDigest(result),
      assetPassport: _buildAssetPassport(
        result,
        storagePath: _latestStoragePath,
        assetLabel: _pickedFile?.name,
        savedAsAsset: _saveToStorage,
      ),
      compareDigest: compareDigest,
      collaborationBrief: _buildCollaborationBrief(
        result,
        storagePath: _latestStoragePath,
        referenceAsset: referenceAsset,
        compareDigest: compareDigest,
      ),
      onOpenHistory: _openHistory,
      onCopyStoragePath: _copyStoragePath,
      onCopySchemaDigest: _copySchemaDigest,
      onCopyGovernanceDigest: _copyGovernanceDigest,
      onCopyAssetPassport: _copyAssetPassport,
      onCopyCompareDigest: _copyCompareDigest,
      onCopyCollaborationBrief: _copyCollaborationBrief,
      onSendToTraining: widget.onSendToAiLab == null
          ? null
          : () => widget.onSendToAiLab!(
              AiLabLaunchIntent.deepLearning(
                _latestStoragePath!,
                sourceLabel: _datasetSourceLabel(
                  datasetChain,
                  prefix: '分析后续动作 · 训练交接',
                ),
              ),
            ),
      onSendToRag: widget.onSendToAiLab == null
          ? null
          : () => widget.onSendToAiLab!(
              AiLabLaunchIntent.rag(
                _latestStoragePath!,
                sourceLabel: _datasetSourceLabel(
                  datasetChain,
                  prefix: '分析后续动作 · 知识库交接',
                ),
              ),
            ),
    );
  }

  Widget _buildAssetGovernanceBoard() {
    final result = _analysisResult;
    if (result == null) {
      return const SizedBox.shrink();
    }
    final datasetChain = _dashboardViewModel
        .summary
        ?.assetSummary
        .chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((item) => item?.key == 'dataset', orElse: () => null);

    final referenceAssets = _availableReferenceAssets();
    final selectedReferencePath = _effectiveReferencePath(referenceAssets);
    final availableFeatures = _numericDriftFeatures(result);
    final selectedFeatures = _effectiveSelectedDriftFeatures(availableFeatures);

    return DataAssetGovernanceBoard(
      chain: datasetChain,
      continuationContext: _activeLaunchContext,
      currentStoragePath: _latestStoragePath,
      currentQualityScore: result.qualityAnalysis?.qualityScore,
      currentAssetLabel: _pickedFile?.name ?? '当前会话资产',
      referenceAssets: referenceAssets,
      selectedReferencePath: selectedReferencePath,
      availableFeatures: availableFeatures,
      selectedFeatures: selectedFeatures,
      isLoadingAssets: _historyViewModel.isLoading,
      isRunningDrift: _driftViewModel.isLoading,
      assetsErrorMessage: _historyViewModel.errorMessage,
      driftErrorMessage: _driftViewModel.errorMessage,
      report: _driftViewModel.report,
      onSelectReference: (value) {
        setState(() {
          _selectedReferencePath = value;
        });
      },
      onToggleFeature: (feature) {
        final next =
            (_selectedDriftFeatures ?? availableFeatures.take(5).toSet())
                .toSet();
        if (!next.add(feature)) {
          next.remove(feature);
        }
        setState(() {
          _selectedDriftFeatures = next;
        });
      },
      onRefreshAssets: () {
        _historyViewModel.loadHistory(limit: 12);
      },
      onRunDrift: _runDriftDetection,
      onCopyCurrentPath: _copyStoragePath,
      onCopyDriftReport: _copyDriftReport,
    );
  }

  Widget _buildAnalysisJobPanel() {
    final latestJob = _analysisJobsViewModel.jobs.isEmpty
        ? null
        : _analysisJobsViewModel.jobs.first;
    final canHydrateLatest =
        latestJob != null &&
        latestJob.status == 'succeeded' &&
        latestJob.result.containsKey('analysis_result');

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('后台分析任务中心', style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      '大文件和长时分析统一通过任务中心观察。同步分析继续保留，用于立即查看结果。',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              if (canHydrateLatest)
                OutlinedButton.icon(
                  onPressed: () => _hydrateLatestAnalysisJob(latestJob),
                  icon: const Icon(Icons.download_done_rounded),
                  label: const Text('载入最近后台结果'),
                ),
            ],
          ),
          const SizedBox(height: 12),
          if (latestJob != null) ...[
            Text(
              '最近任务: ${latestJob.displayTitle} · ${latestJob.statusMessage ?? latestJob.status}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 12),
            JobEventTimeline(
              job: latestJob,
              title: '最近分析任务轨迹',
              emptyMessage: '后台分析开始执行后，这里会显示基础剖析、质量检查和统计检验阶段。',
              onOpenOperation: () => _openJobInShellRuntime(latestJob),
              onRetry: latestJob.retryable
                  ? () => _retryAnalysisJob(latestJob)
                  : null,
              onCancel: latestJob.isTerminal
                  ? null
                  : () => _cancelAnalysisJob(latestJob),
              onApprove: latestJob.isAwaitingApproval
                  ? () => _resolveAnalysisApproval(latestJob, approved: true)
                  : null,
              onReject: latestJob.isAwaitingApproval
                  ? () => _resolveAnalysisApproval(latestJob, approved: false)
                  : null,
            ),
            const SizedBox(height: 16),
          ],
          JobActivityList(
            jobs: _analysisJobsViewModel.jobs,
            emptyMessage: '暂无后台分析任务。提交后可在这里观察上传后的分析进度。',
            compact: true,
            onOpenJob: _openJobInShellRuntime,
          ),
        ],
      ),
    );
  }

  Future<void> _copyStoragePath() async {
    final storagePath = _latestStoragePath;
    if (storagePath == null || storagePath.isEmpty) {
      return;
    }
    await Clipboard.setData(ClipboardData(text: storagePath));
    if (!mounted) {
      return;
    }
    _showSuccessFeedback(_datasetFeedbackMessage('Storage Path 已复制'));
  }

  void _applyLaunchIntent(DataAnalysisLaunchIntent? intent) {
    if (intent == null) {
      return;
    }

    _activeLaunchContext = intent.context;

    if (intent.analysisResult != null) {
      _viewModel.loadAnalysisSnapshot(
        result: intent.analysisResult!,
        storagePath: intent.storagePath,
        filename: intent.filename,
        saveToStorage: intent.savedAsAsset,
      );
      _driftViewModel.clearReport();
      _selectedReferencePath = null;
      _selectedDriftFeatures = null;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) {
          return;
        }
        final arrivalContext = normalizeLaunchContextSubject(
          intent.context,
          fallbackSubject: intent.sourceLabel ?? intent.filename ?? '资产',
        );
        _showSuccessFeedback(
          buildLaunchArrivalMessage(
            arrivalContext,
            fallbackSubject: intent.sourceLabel ?? intent.filename ?? '资产',
            destination: '数据分析工作台',
            verb: '已载入',
          ),
        );
        _focusAnalysisResult();
      });
    } else if ((intent.sourceLabel ?? '').isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) {
          return;
        }
        final arrivalContext = normalizeLaunchContextSubject(
          intent.context,
          fallbackSubject: intent.sourceLabel!,
        );
        _showSuccessFeedback(
          buildLaunchArrivalMessage(
            arrivalContext,
            fallbackSubject: intent.sourceLabel!,
            destination: '数据分析工作台',
            includeWorkspaceBrief: false,
          ),
        );
      });
    } else {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) {
          return;
        }
        _showFeedback(
          message: '该资产缺少可回放的分析结果',
          backgroundColor: AppColors.error,
        );
      });
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.onLaunchIntentHandled?.call();
    });
  }

  Future<void> _copySchemaDigest() async {
    final result = _analysisResult;
    if (result == null) {
      return;
    }
    await Clipboard.setData(ClipboardData(text: _buildSchemaDigest(result)));
    if (!mounted) {
      return;
    }
    _showSuccessFeedback(_datasetFeedbackMessage('Schema Digest 已复制'));
  }

  Future<void> _copyGovernanceDigest() async {
    final result = _analysisResult;
    if (result == null) {
      return;
    }
    await Clipboard.setData(
      ClipboardData(text: _buildGovernanceDigest(result)),
    );
    if (!mounted) {
      return;
    }
    _showSuccessFeedback(_datasetFeedbackMessage('治理摘要已复制'));
  }

  Future<void> _copyDriftReport() async {
    final report = _driftViewModel.report;
    if (report == null || report.report.isEmpty) {
      return;
    }
    await Clipboard.setData(ClipboardData(text: report.report));
    if (!mounted) {
      return;
    }
    _showSuccessFeedback(_datasetFeedbackMessage('漂移报告已复制'));
  }

  Future<void> _copyAssetPassport() async {
    final result = _analysisResult;
    if (result == null) {
      return;
    }
    await Clipboard.setData(
      ClipboardData(
        text: _buildAssetPassport(
          result,
          storagePath: _latestStoragePath,
          assetLabel: _pickedFile?.name,
          savedAsAsset: _saveToStorage,
        ),
      ),
    );
    if (!mounted) {
      return;
    }
    _showSuccessFeedback(_datasetFeedbackMessage('资产护照已复制'));
  }

  Future<void> _copyCompareDigest() async {
    final result = _analysisResult;
    if (result == null) {
      return;
    }
    final referenceAssets = _availableReferenceAssets();
    final referenceAsset = referenceAssets.cast<HistoryRecord?>().firstWhere(
      (item) => item?.storageUrl == _effectiveReferencePath(referenceAssets),
      orElse: () => null,
    );
    await Clipboard.setData(
      ClipboardData(
        text: _buildCompareDigest(
          result,
          referenceAsset: referenceAsset,
          driftStatus: _driftViewModel.report?.overallStatus,
          recommendation: _driftViewModel.report?.recommendation,
        ),
      ),
    );
    if (!mounted) {
      return;
    }
    _showSuccessFeedback(_datasetFeedbackMessage('对比摘要已复制'));
  }

  Future<void> _copyCollaborationBrief() async {
    final result = _analysisResult;
    if (result == null) {
      return;
    }
    final referenceAssets = _availableReferenceAssets();
    final referenceAsset = referenceAssets.cast<HistoryRecord?>().firstWhere(
      (item) => item?.storageUrl == _effectiveReferencePath(referenceAssets),
      orElse: () => null,
    );
    await Clipboard.setData(
      ClipboardData(
        text: _buildCollaborationBrief(
          result,
          storagePath: _latestStoragePath,
          referenceAsset: referenceAsset,
          compareDigest: _buildCompareDigest(
            result,
            referenceAsset: referenceAsset,
            driftStatus: _driftViewModel.report?.overallStatus,
            recommendation: _driftViewModel.report?.recommendation,
          ),
        ),
      ),
    );
    if (!mounted) {
      return;
    }
    _showSuccessFeedback(_datasetFeedbackMessage('协作摘要已复制'));
  }

  Future<void> _runDriftDetection() async {
    final currentPath = _latestStoragePath;
    final result = _analysisResult;
    if (currentPath == null || currentPath.isEmpty || result == null) {
      return;
    }

    final referencePath = _effectiveReferencePath(_availableReferenceAssets());
    final features = _effectiveSelectedDriftFeatures(
      _numericDriftFeatures(result),
    ).toList(growable: false);

    if (referencePath == null || referencePath.isEmpty) {
      _showFeedback(
        message: '缺少基线资产，无法运行漂移检测',
        backgroundColor: AppColors.error,
      );
      return;
    }
    if (features.isEmpty) {
      _showFeedback(message: '请选择至少一个数值字段', backgroundColor: AppColors.error);
      return;
    }

    final report = await _driftViewModel.detectDrift(
      referencePath: referencePath,
      currentPath: currentPath,
      features: features,
    );
    if (!mounted) {
      return;
    }
    if (report != null) {
      _showSuccessFeedback(
        _datasetFeedbackMessage(
          '漂移检测完成',
          detail: report.overallStatus.toUpperCase(),
        ),
      );
      return;
    }
    final message = _driftViewModel.errorMessage;
    if (message != null) {
      _showFeedback(message: message, backgroundColor: AppColors.error);
    }
  }

  void _hydrateLatestAnalysisJob(JobRecord latestJob) {
    final success = _viewModel.loadAnalysisResultFromJobPayload(
      latestJob.result,
    );
    if (success) {
      _showSuccessFeedback(_datasetFeedbackMessage('已载入最近后台分析结果'));
      _focusAnalysisResult();
      return;
    }
    _showViewModelError(duration: _analysisErrorDuration);
  }

  Future<void> _focusAnalysisResult() async {
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final context = _analysisResultKey.currentContext;
      if (context == null) {
        return;
      }
      await Scrollable.ensureVisible(
        context,
        duration: const Duration(milliseconds: 280),
        curve: Curves.easeOutCubic,
        alignment: 0.08,
      );
    });
  }

  Future<void> _retryAnalysisJob(JobRecord job) async {
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

    final retried = await _analysisJobsViewModel.retryJob(job.jobId);
    if (!mounted) {
      return;
    }
    if (retried != null) {
      await _openJobInShellRuntime(retried);
      _showSuccessFeedback(_datasetFeedbackMessage('后台分析任务已重新排队'));
      return;
    }
    final message = _analysisJobsViewModel.errorMessage;
    if (message != null) {
      _showFeedback(message: message, backgroundColor: AppColors.error);
    }
  }

  Future<void> _cancelAnalysisJob(JobRecord job) async {
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

    final cancelled = await _analysisJobsViewModel.cancelJob(job);
    if (!mounted) {
      return;
    }
    if (cancelled != null) {
      await _openJobInShellRuntime(cancelled);
      _showSuccessFeedback(_datasetFeedbackMessage('后台分析任务已提交取消'));
      return;
    }
    final message = _analysisJobsViewModel.errorMessage;
    if (message != null) {
      _showFeedback(message: message, backgroundColor: AppColors.error);
    }
  }

  Future<void> _resolveAnalysisApproval(
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

    final updated = await _analysisJobsViewModel.resolveApproval(
      job,
      approved: approved,
    );
    if (!mounted) {
      return;
    }
    if (updated != null) {
      await _openJobInShellRuntime(updated);
      _showSuccessFeedback(
        _datasetFeedbackMessage(approved ? '后台分析任务已批准执行' : '后台分析任务已驳回'),
      );
      return;
    }
    final message = _analysisJobsViewModel.errorMessage;
    if (message != null) {
      _showFeedback(message: message, backgroundColor: AppColors.error);
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

  Future<void> _refreshSharedProjection() async {
    if (widget.sharedRuntimeManaged) {
      final runtime = MainShellRuntimeScope.maybeOf(context);
      if (runtime != null) {
        await runtime.refreshSharedSnapshot(force: true);
        return;
      }
    }
    await _dashboardViewModel.loadSummary();
  }

  void _showSuccessFeedback(String message) {
    _showFeedback(message: message, backgroundColor: AppColors.success);
  }

  void _showSharedActionOutcome(ShellActionOutcome outcome) {
    final backgroundColor = switch (outcome.tone) {
      ShellActionTone.success => AppColors.success,
      ShellActionTone.warning => AppColors.warning,
      ShellActionTone.error => AppColors.error,
      ShellActionTone.info => AppColors.primary,
    };
    _showFeedback(message: outcome.message, backgroundColor: backgroundColor);
  }

  void _showViewModelError({Duration duration = _defaultErrorDuration}) {
    final message = _errorMessage;
    if (!mounted || message == null) {
      return;
    }

    _showFeedback(
      message: message,
      backgroundColor: AppColors.error,
      duration: duration,
    );
  }

  void _showFeedback({
    required String message,
    required Color backgroundColor,
    Duration duration = _defaultErrorDuration,
  }) {
    final messenger = ScaffoldMessenger.of(context);
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: backgroundColor,
        duration: duration,
      ),
    );
  }

  List<String> _numericDriftFeatures(AnalysisResult result) {
    final features = <String>[];
    for (final entry in result.basicInfo.columnTypes.entries) {
      final normalized = entry.value.toLowerCase();
      if (normalized.contains('int') ||
          normalized.contains('float') ||
          normalized.contains('double') ||
          normalized.contains('num')) {
        features.add(entry.key);
      }
    }
    return features;
  }

  List<HistoryRecord> _availableReferenceAssets() {
    final currentPath = _latestStoragePath;
    return _historyViewModel.records
        .where((record) {
          final path = record.storageUrl;
          if (path == null || path.isEmpty) {
            return false;
          }
          return currentPath == null || path != currentPath;
        })
        .toList(growable: false);
  }

  String? _effectiveReferencePath(List<HistoryRecord> assets) {
    final selected = _selectedReferencePath;
    if (selected != null &&
        assets.any((record) => record.storageUrl == selected)) {
      return selected;
    }
    return assets.isEmpty ? null : assets.first.storageUrl!;
  }

  Set<String> _effectiveSelectedDriftFeatures(List<String> availableFeatures) {
    final selected = _selectedDriftFeatures;
    if (selected == null) {
      return availableFeatures.take(5).toSet();
    }
    return selected.where(availableFeatures.contains).toSet();
  }

  String _datasetSourceLabel(
    AssetChainSummary? chain, {
    required String prefix,
  }) {
    return buildChainSourceLabel(
      chain,
      prefix: prefix,
      includeWorkspaceBrief: true,
    );
  }

  AssetChainSummary? _datasetChain() {
    return _sharedSummary?.assetSummary.chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((item) => item?.key == 'dataset', orElse: () => null);
  }

  String _datasetFeedbackMessage(String prefix, {String? detail}) {
    return buildChainActionFeedbackMessage(
      _datasetChain(),
      prefix: prefix,
      detail: detail,
    );
  }
}

String _buildSchemaDigest(AnalysisResult result) {
  final counts = _schemaCounts(result.basicInfo.columnTypes);
  return [
    'rows=${result.basicInfo.rows}',
    'columns=${result.basicInfo.columns}',
    'numeric=${counts.numeric}',
    'categorical=${counts.categorical}',
    'datetime=${counts.datetime}',
    if (result.basicInfo.columnNames.isNotEmpty)
      'key_columns=${result.basicInfo.columnNames.take(5).join(', ')}',
  ].join(' | ');
}

String _buildGovernanceDigest(AnalysisResult result) {
  final quality = result.qualityAnalysis;
  final metrics = quality?.qualityMetrics;
  final duplicates = quality?.duplicateCheck?.count ?? 0;
  final highRiskColumns = quality?.highRiskColumns ?? const <String>[];
  final nonNormalCount =
      result.statisticalTests?.summary?.nonNormalDistributionCount ?? 0;
  final highCorrelationCount =
      result.correlations?.highCorrelations?.length ??
      result.correlations?.correlations?.length ??
      0;

  return [
    'quality_score=${quality?.qualityScore?.toStringAsFixed(0) ?? '--'}',
    'missing_rate=${metrics?.missingRate.toStringAsFixed(1) ?? '0.0'}%',
    'duplicate_rows=$duplicates',
    'outliers=${metrics?.totalOutliers ?? 0}',
    'high_risk_columns=${highRiskColumns.take(4).join(', ').ifEmpty('--')}',
    'high_correlations=$highCorrelationCount',
    'non_normal_distributions=$nonNormalCount',
  ].join(' | ');
}

String _buildAssetPassport(
  AnalysisResult result, {
  String? storagePath,
  String? assetLabel,
  bool savedAsAsset = false,
}) {
  final quality = result.qualityAnalysis;
  final qualityScore = quality?.qualityScore?.toStringAsFixed(0) ?? '--';
  final riskCount = quality?.highRiskColumns?.length ?? 0;
  return [
    'asset=${assetLabel ?? "current-session"}',
    'storage=${storagePath ?? "--"}',
    'rows=${result.basicInfo.rows}',
    'columns=${result.basicInfo.columns}',
    'quality_score=$qualityScore',
    'high_risk_columns=$riskCount',
    'archived=${savedAsAsset ? "yes" : "no"}',
  ].join(' | ');
}

String _buildCompareDigest(
  AnalysisResult result, {
  HistoryRecord? referenceAsset,
  String? driftStatus,
  String? recommendation,
}) {
  if (referenceAsset == null) {
    return '当前未选择基线资产。建议选择一份历史分析资产并运行漂移检测。';
  }

  final currentRows = result.basicInfo.rows;
  final currentColumns = result.basicInfo.columns;
  final referenceRows = referenceAsset.basicInfo?['rows']?.toString() ?? '--';
  final referenceColumns =
      referenceAsset.basicInfo?['columns']?.toString() ?? '--';
  final qualityDelta =
      (result.qualityAnalysis?.qualityScore != null &&
          referenceAsset.qualityScore != null)
      ? (result.qualityAnalysis!.qualityScore! - referenceAsset.qualityScore!)
      : null;

  return [
    'baseline=${referenceAsset.filename}',
    'rows=$currentRows vs $referenceRows',
    'columns=$currentColumns vs $referenceColumns',
    if (qualityDelta != null)
      'quality_delta=${qualityDelta >= 0 ? "+" : ""}${qualityDelta.toStringAsFixed(1)}',
    if (driftStatus != null) 'drift=${driftStatus.toUpperCase()}',
    if (recommendation != null && recommendation.isNotEmpty)
      'next=$recommendation',
  ].join(' | ');
}

String _buildCollaborationBrief(
  AnalysisResult result, {
  String? storagePath,
  HistoryRecord? referenceAsset,
  String? compareDigest,
}) {
  return [
    'Data Analysis Collaboration Brief',
    _buildAssetPassport(
      result,
      storagePath: storagePath,
      savedAsAsset: storagePath != null && storagePath.isNotEmpty,
    ),
    _buildGovernanceDigest(result),
    compareDigest ??
        _buildCompareDigest(result, referenceAsset: referenceAsset),
  ].join('\n');
}

_SchemaCounts _schemaCounts(Map<String, String> columnTypes) {
  var numeric = 0;
  var categorical = 0;
  var datetime = 0;

  for (final type in columnTypes.values) {
    final normalized = type.toLowerCase();
    if (normalized.contains('int') ||
        normalized.contains('float') ||
        normalized.contains('double') ||
        normalized.contains('num')) {
      numeric++;
      continue;
    }
    if (normalized.contains('date') || normalized.contains('time')) {
      datetime++;
      continue;
    }
    categorical++;
  }

  return _SchemaCounts(
    numeric: numeric,
    categorical: categorical,
    datetime: datetime,
  );
}

class _SchemaCounts {
  const _SchemaCounts({
    required this.numeric,
    required this.categorical,
    required this.datetime,
  });

  final int numeric;
  final int categorical;
  final int datetime;
}

extension on String {
  String ifEmpty(String fallback) => isEmpty ? fallback : this;
}
