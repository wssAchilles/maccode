/// 能源优化仪表盘页面
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../config/app_theme.dart';
import '../models/dashboard_summary.dart';
import '../models/job_record.dart';
import '../models/main_shell_projection.dart';
import '../models/modeling_controls_state.dart';
import '../models/optimization_result.dart';
import '../models/optimization_launch_intent.dart';
import '../models/shell_action_outcome.dart';
import '../models/workbench_launch_context.dart';
import '../utils/asset_chain_context.dart';
import '../utils/job_presentation.dart';
import '../utils/responsive_helper.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../viewmodels/job_view_model.dart';
import '../viewmodels/modeling_view_model.dart';
import '../widgets/common/glass_card.dart';
import '../widgets/navigation/main_shell_runtime_scope.dart';
import '../widgets/operations/decision_layout.dart';
import '../widgets/operations/job_activity_list.dart';
import '../widgets/operations/job_event_timeline.dart';
import '../widgets/operations/workbench_page_frame.dart';
import '../widgets/operations/workspace_action_lane.dart';
import '../widgets/operations/workspace_digest_card.dart';
import '../widgets/modeling/modeling_control_panel.dart';
import '../widgets/modeling/optimization_asset_registry_board.dart';
import '../widgets/modeling/optimization_operations_board.dart';
import '../widgets/modeling/modeling_results_section.dart';
import '../widgets/responsive_wrapper.dart';

class ModelingScreen extends StatefulWidget {
  const ModelingScreen({
    super.key,
    this.viewModel,
    this.dashboardViewModel,
    this.jobsViewModel,
    this.shellProjection,
    this.nowBuilder,
    this.launchIntent,
    this.onLaunchIntentHandled,
    this.isActive = true,
    this.sharedRuntimeManaged = false,
    this.surfaceMode = WorkbenchSurfaceMode.standalone,
  });

  final ModelingViewModel? viewModel;
  final DashboardViewModel? dashboardViewModel;
  final JobViewModel? jobsViewModel;
  final MainShellProjection? shellProjection;
  final DateTime Function()? nowBuilder;
  final OptimizationLaunchIntent? launchIntent;
  final VoidCallback? onLaunchIntentHandled;
  final bool isActive;
  final bool sharedRuntimeManaged;
  final WorkbenchSurfaceMode surfaceMode;

  @override
  State<ModelingScreen> createState() => _ModelingScreenState();
}

class _ModelingScreenState extends State<ModelingScreen> {
  final _pageScrollController = ScrollController();
  final _optimizationResultKey = GlobalKey();
  late final ModelingViewModel _viewModel;
  late final JobViewModel _jobViewModel;
  late final bool _ownsViewModel;
  late final bool _ownsJobViewModel;
  late ModelingControlsState _controls;
  WorkbenchLaunchContext? _activeLaunchContext;
  bool _didActivateWorkspace = false;

  bool get _isLoading => _viewModel.isLoading;
  OptimizationResponse? get _result => _viewModel.result;
  OptimizationResponse? get _previousResult => _viewModel.previousResult;
  String? get _errorMessage => _viewModel.errorMessage;
  DashboardSummary? get _sharedSummary => widget.sharedRuntimeManaged
      ? (widget.shellProjection?.summary ?? widget.dashboardViewModel?.summary)
      : widget.dashboardViewModel?.summary;

  @override
  void initState() {
    super.initState();
    _viewModel = widget.viewModel ?? ModelingViewModel();
    _jobViewModel =
        widget.jobsViewModel ?? JobViewModel(jobType: 'optimization', limit: 8);
    _ownsViewModel = widget.viewModel == null;
    _ownsJobViewModel = widget.jobsViewModel == null;
    _controls = ModelingControlsState.initial(now: _now);
    _applyLaunchIntent(widget.launchIntent);
    _handleWorkspaceActivation(widget.isActive);
  }

  @override
  void didUpdateWidget(covariant ModelingScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.launchIntent != oldWidget.launchIntent) {
      _applyLaunchIntent(widget.launchIntent);
    }
    if (widget.isActive != oldWidget.isActive) {
      _handleWorkspaceActivation(widget.isActive);
    }
  }

  DateTime get _now => (widget.nowBuilder ?? DateTime.now).call();

  @override
  void dispose() {
    _pageScrollController.dispose();
    if (_ownsJobViewModel) {
      _jobViewModel.dispose();
    }
    if (_ownsViewModel) {
      _viewModel.dispose();
    }
    super.dispose();
  }

  void _handleWorkspaceActivation(bool isActive) {
    if (!widget.sharedRuntimeManaged) {
      _jobViewModel.setWorkspaceActive(isActive);
    }
    if (!isActive) {
      return;
    }
    if (!_didActivateWorkspace) {
      _didActivateWorkspace = true;
      if (!widget.sharedRuntimeManaged) {
        widget.dashboardViewModel?.initialize();
        _jobViewModel.loadJobs();
      }
    }
  }

  Future<void> _runOptimization({bool saveForComparison = true}) async {
    final result = await _viewModel.runOptimization(
      initialSoc: _controls.initialSoc,
      targetDate: _controls.targetDate,
      batteryCapacity: _controls.batteryCapacity,
      batteryPower: _controls.maxPower,
      temperatureAdjust: _controls.temperatureAdjust,
      saveForComparison: saveForComparison,
    );

    if (!mounted) {
      return;
    }

    if (result == null) {
      final message = _errorMessage;
      if (message != null) {
        _showErrorSnackBar(message);
      }
      return;
    }

    if (result.isSuccess) {
      _showSuccessSnackBar(
        '优化完成！节省 ${result.optimization?.summary.savingsFormatted ?? "0"}',
      );
      await _refreshSharedProjection();
      _focusOptimizationResults();
      return;
    }

    final message = _errorMessage;
    if (message != null) {
      _showErrorSnackBar(message);
    }
  }

  Future<void> _refreshResults() async {
    if (_isLoading || _result == null) {
      return;
    }

    await _runOptimization(saveForComparison: false);
  }

  String _scenarioLabel(ModelingScenario? scenario) {
    switch (scenario) {
      case ModelingScenario.summer:
        return '夏季高温';
      case ModelingScenario.winter:
        return '冬季寒潮';
      case ModelingScenario.overtime:
        return '夜间加班';
      case null:
        return '自定义';
    }
  }

  Color _jobStatusColor(String status) {
    switch (status) {
      case 'queued':
        return AppColors.primary;
      case 'running':
        return AppColors.warning;
      case 'succeeded':
        return AppColors.success;
      case 'failed':
        return AppColors.error;
      case 'cancelled':
        return AppColors.textSecondary;
      default:
        return AppColors.textSecondary;
    }
  }

  void _showSuccessSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: AppColors.success,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  AssetChainSummary? _optimizationChain() {
    return _sharedSummary?.assetSummary.chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((item) => item?.key == 'optimization', orElse: () => null);
  }

  String _optimizationFeedbackMessage(String prefix, {String? detail}) {
    return buildChainActionFeedbackMessage(
      _optimizationChain(),
      prefix: prefix,
      detail: detail,
    );
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: AppColors.error,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
        margin: const EdgeInsets.all(16),
        duration: const Duration(seconds: 5),
      ),
    );
  }

  void _updateControls(ModelingControlsState nextState) {
    setState(() {
      _controls = nextState;
    });
  }

  void _applyOptimizationAsset(OptimizationAsset asset) {
    final targetDate = asset.targetDate == null
        ? _controls.targetDate
        : DateTime.tryParse(asset.targetDate!) ?? _controls.targetDate;
    _updateControls(
      _controls.copyWith(
        initialSoc: asset.initialSoc,
        targetDate: targetDate,
        batteryCapacity: asset.batteryCapacity,
        maxPower: asset.batteryPower,
        temperatureAdjust: 0,
        clearScenario: true,
      ),
    );
    _showSuccessSnackBar(_optimizationFeedbackMessage('优化资产快照已回填到工作台'));
  }

  Future<void> _submitOptimizationJob() async {
    final job = await _jobViewModel.submitOptimizationJob(
      initialSoc: _controls.initialSoc,
      targetDate: _controls.targetDate,
      batteryCapacity: _controls.batteryCapacity,
      batteryPower: _controls.maxPower,
      temperatureAdjust: _controls.temperatureAdjust,
    );

    if (!mounted) {
      return;
    }

    if (job != null) {
      _showSuccessSnackBar(_optimizationFeedbackMessage('后台优化任务已提交'));
      widget.dashboardViewModel?.loadSummary();
      return;
    }

    final error = _jobViewModel.errorMessage;
    if (error != null) {
      _showErrorSnackBar(error);
    }
  }

  Future<void> _selectDate() async {
    final now = _now;
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _controls.targetDate,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: DateTime(
        now.year,
        now.month,
        now.day,
      ).add(const Duration(days: 7)),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: ColorScheme.light(
              primary: Colors.blue[700]!,
              onPrimary: Colors.white,
            ),
          ),
          child: child!,
        );
      },
    );

    if (!mounted || picked == null || picked == _controls.targetDate) {
      return;
    }

    _updateControls(_controls.copyWith(targetDate: picked));
  }

  void _applyLaunchIntent(OptimizationLaunchIntent? intent) {
    if (intent == null) {
      return;
    }

    final nextState = _controls.copyWith(
      initialSoc: intent.initialSoc,
      targetDate: intent.targetDate,
      batteryCapacity: intent.batteryCapacity,
      maxPower: intent.batteryPower,
      temperatureAdjust: intent.temperatureAdjust,
      clearScenario: true,
    );

    setState(() {
      _controls = nextState;
      _activeLaunchContext = intent.context;
    });

    if (intent.hasResultPayload) {
      _viewModel.loadResultFromJobPayload(intent.resultPayload!);
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      final fallbackSubject = intent.sourceLabel ?? '后台任务';
      final arrivalContext = normalizeLaunchContextSubject(
        intent.context,
        fallbackSubject: fallbackSubject,
      );
      _showSuccessSnackBar(
        buildLaunchArrivalMessage(
          arrivalContext,
          fallbackSubject: fallbackSubject,
          destination: '优化工作台',
          verb: intent.hasResultPayload ? '已载入' : '已打开',
          includeWorkspaceBrief: intent.hasResultPayload,
        ),
      );
      widget.onLaunchIntentHandled?.call();
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([
        _viewModel,
        _jobViewModel,
        if (widget.dashboardViewModel != null) widget.dashboardViewModel!,
      ]),
      builder: (context, _) {
        final assetSummary = _sharedSummary?.assetSummary;
        final optimizationChain = assetSummary?.chainSummaries
            .cast<AssetChainSummary?>()
            .firstWhere(
              (item) => item?.key == 'optimization',
              orElse: () => null,
            );
        final latestCompletedJob = _jobViewModel.jobs
            .cast<JobRecord?>()
            .firstWhere(
              (job) =>
                  job?.status == 'succeeded' &&
                  job?.result.containsKey('optimization') == true,
              orElse: () => null,
            );
        final resultReady = _result?.isSuccess == true;
        final optimizationControls = ModelingControlPanel(
          state: _controls,
          isLoading: _isLoading,
          onToggleAdvancedParams: () {
            _updateControls(
              _controls.copyWith(
                showAdvancedParams: !_controls.showAdvancedParams,
              ),
            );
          },
          onScenarioChanged: (scenario) {
            _updateControls(_controls.applyScenario(scenario));
          },
          onInitialSocChanged: (value) {
            _updateControls(_controls.copyWith(initialSoc: value));
          },
          onBatteryCapacityChanged: (value) {
            _updateControls(_controls.copyWith(batteryCapacity: value));
          },
          onMaxPowerChanged: (value) {
            _updateControls(_controls.copyWith(maxPower: value));
          },
          onTemperatureAdjustChanged: (value) {
            _updateControls(_controls.copyWith(temperatureAdjust: value));
          },
          onSelectDate: _selectDate,
          onRunOptimization: _runOptimization,
        );
        final optimizationResultPanel = KeyedSubtree(
          key: _optimizationResultKey,
          child: ModelingResultsSection(
            isLoading: _isLoading,
            errorMessage: _errorMessage,
            result: _result,
            previousResult: _previousResult,
            onDismissError: _viewModel.clearError,
            chain: optimizationChain,
            continuationContext: _activeLaunchContext,
          ),
        );
        final primaryAction = DecisionHeaderAction(
          label: resultReady ? '查看节省结果' : '立即试算',
          icon: resultReady ? Icons.insights_rounded : Icons.play_arrow_rounded,
          onTap: resultReady
              ? _focusOptimizationResults
              : () => _runOptimization(),
          isPrimary: true,
        );
        final content = RefreshIndicator(
          onRefresh: _refreshResults,
          child: ResponsiveWrapper(
            maxWidth: ResponsiveHelper.getMaxContentWidth(context),
            child: SingleChildScrollView(
              controller: _pageScrollController,
              physics: const AlwaysScrollableScrollPhysics(),
              padding: ResponsiveHelper.getPagePadding(context),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  DecisionHeaderCard(
                    title: '今日调度结果',
                    summary: '先设定场景和目标日，再试算一次可执行策略；后台队列和注册表统一下沉到详情区。',
                    metrics: [
                      DecisionHeaderMetric(
                        label: '场景',
                        value: _scenarioLabel(_controls.selectedScenario),
                        helper: '当前试算上下文',
                        accent: AppColors.primary,
                        icon: Icons.tune_rounded,
                      ),
                      DecisionHeaderMetric(
                        label: '目标日期',
                        value: DateFormat('MM-dd').format(_controls.targetDate),
                        helper: '计划执行日',
                        accent: AppColors.cta,
                        icon: Icons.event_rounded,
                      ),
                      DecisionHeaderMetric(
                        label: '后台状态',
                        value: latestCompletedJob == null
                            ? (_jobViewModel.jobs.isEmpty
                                  ? '空闲'
                                  : buildJobPrimaryText(
                                      _jobViewModel.jobs.first,
                                    ))
                            : buildJobPrimaryText(latestCompletedJob),
                        helper: '最近一次求解任务',
                        accent: latestCompletedJob == null
                            ? AppColors.textSecondary
                            : _jobStatusColor(latestCompletedJob.status),
                        icon: Icons.cloud_queue_rounded,
                      ),
                      DecisionHeaderMetric(
                        label: '预计节省',
                        value:
                            _result?.optimization?.summary.savingsFormatted ??
                            '等待试算',
                        helper: _result?.isSuccess == true
                            ? '本次方案收益'
                            : '运行后展示结果',
                        accent: _result?.isSuccess == true
                            ? AppColors.success
                            : AppColors.warning,
                        icon: Icons.savings_rounded,
                      ),
                    ],
                    primaryAction: primaryAction,
                    banner: _buildOptimizationBanner(latestCompletedJob),
                  ),
                  const SizedBox(height: 16),
                  PrimaryWorkflowPanel(
                    eyebrow: '输入参数 -> 立即试算 -> 节省结果',
                    title: resultReady ? '本次节省结果' : '本次优化工作流',
                    summary: resultReady
                        ? '试算结果已经置顶，参数配置和后台任务已下沉到结果下方。'
                        : '首屏只保留参数配置、一次试算动作和核心节省结果，不再混排队列、注册表和复制动作。',
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildOptimizationHighlights(latestCompletedJob),
                        const SizedBox(height: 16),
                        if (resultReady)
                          optimizationResultPanel
                        else
                          optimizationControls,
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  ProgressiveDetailSection(
                    title: resultReady ? '参数、任务与产物' : '任务与产物',
                    summary: resultReady
                        ? '参数区、后台队列、结果回填和运维协作动作统一下沉到这里。'
                        : '后台队列、结果回填、资产注册表和运维协作动作统一放到这里。',
                    icon: Icons.inventory_2_rounded,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (resultReady) ...[
                          optimizationControls,
                          const SizedBox(height: 16),
                        ],
                        _buildJobPanel(),
                        const SizedBox(height: 16),
                        OptimizationOperationsBoard(
                          chain: optimizationChain,
                          continuationContext: _activeLaunchContext,
                          result: _result,
                          latestCompletedJob: latestCompletedJob,
                        ),
                        const SizedBox(height: 16),
                        OptimizationAssetRegistryBoard(
                          chain: optimizationChain,
                          continuationContext: _activeLaunchContext,
                          assetSummary: assetSummary,
                          latestCompletedJob: latestCompletedJob,
                          onApplyAsset: _applyOptimizationAsset,
                          onCopyAssetPassport: (asset) {
                            _copyOptimizationAssetPassport(asset);
                          },
                          onLoadLatestJobResult: latestCompletedJob == null
                              ? null
                              : () =>
                                    _hydrateLatestJobResult(latestCompletedJob),
                        ),
                        const SizedBox(height: 16),
                        _buildOperationsCard(optimizationChain),
                      ],
                    ),
                  ),
                  if (!resultReady) ...[
                    const SizedBox(height: 16),
                    ProgressiveDetailSection(
                      title: '详细结果',
                      summary: '约束命中、解释性、历史对比和完整结果保留在这一层。',
                      icon: Icons.analytics_rounded,
                      child: optimizationResultPanel,
                    ),
                  ],
                  const SizedBox(height: 32),
                ],
              ),
            ),
          ),
        );

        return WorkbenchPageFrame(
          surfaceMode: widget.surfaceMode,
          body: content,
        );
      },
    );
  }

  Widget _buildOptimizationBanner(JobRecord? latestCompletedJob) {
    if (_errorMessage != null) {
      return DecisionBanner(
        title: '试算需要复核',
        message: _errorMessage!,
        accent: AppColors.error,
        icon: Icons.error_outline_rounded,
      );
    }

    final summary = _result?.optimization?.summary;
    if (_result?.isSuccess == true && summary != null) {
      return DecisionBanner(
        title: '本次方案可执行',
        message:
            '预计节省 ${summary.savingsFormatted}，成本下降 ${summary.savingsPercentFormatted}。',
        accent: AppColors.success,
        icon: Icons.task_alt_rounded,
      );
    }

    if (latestCompletedJob != null) {
      return DecisionBanner(
        title: '已有最近后台结果',
        message: '你可以直接载入最近后台结果，或调整参数后重新试算。',
        accent: AppColors.primary,
        icon: Icons.cloud_done_rounded,
      );
    }

    return const DecisionBanner(
      title: '先完成一次试算',
      message: '调整日期和工况后运行试算，首屏就会给出节省结果和建议策略。',
      accent: AppColors.primary,
      icon: Icons.play_circle_outline_rounded,
    );
  }

  Widget _buildOptimizationHighlights(JobRecord? latestCompletedJob) {
    final summary = _result?.optimization?.summary;
    final strategy = _result?.optimization?.strategy;
    final cards = <Widget>[
      _OptimizationHighlightCard(
        label: '节省金额',
        value: summary?.savingsFormatted ?? '等待结果',
        helper: '运行后自动更新',
        accent: _result?.isSuccess == true
            ? AppColors.success
            : AppColors.warning,
      ),
      _OptimizationHighlightCard(
        label: '建议策略',
        value: strategy == null
            ? '等待策略结论'
            : '充电 ${strategy.chargingCount} 次 / 放电 ${strategy.dischargingCount} 次',
        helper: strategy == null
            ? '运行后给出操作建议'
            : '充电 ${strategy.chargingHoursFormatted}',
        accent: AppColors.cta,
      ),
      _OptimizationHighlightCard(
        label: '目标日期',
        value: DateFormat('yyyy-MM-dd').format(_controls.targetDate),
        helper: _scenarioLabel(_controls.selectedScenario),
        accent: AppColors.primary,
      ),
      _OptimizationHighlightCard(
        label: '是否可执行',
        value: _result?.isSuccess == true ? '可执行' : '待确认',
        helper: latestCompletedJob == null
            ? '还没有后台产物'
            : buildJobPrimaryText(latestCompletedJob),
        accent: _result?.isSuccess == true
            ? AppColors.success
            : AppColors.textSecondary,
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 1080
            ? 4
            : constraints.maxWidth >= 720
            ? 2
            : 1;
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: cards.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: columns == 1 ? 3.6 : 2.2,
          ),
          itemBuilder: (context, index) => cards[index],
        );
      },
    );
  }

  Widget _buildJobPanel() {
    final latestJob = _jobViewModel.jobs.isEmpty
        ? null
        : _jobViewModel.jobs.first;
    final canHydrateLatest =
        latestJob != null &&
        latestJob.status == 'succeeded' &&
        latestJob.result.containsKey('optimization');
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
                    Text('后台优化任务', style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      '用于长时优化和异步监控。同步优化仍然保留，用于即时试算。',
                      style: AppTextStyles.bodySmall,
                    ),
                  ],
                ),
              ),
              FilledButton.tonalIcon(
                onPressed: _jobViewModel.isSubmitting
                    ? null
                    : _submitOptimizationJob,
                icon: _jobViewModel.isSubmitting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.cloud_queue_rounded),
                label: Text(_jobViewModel.isSubmitting ? '提交中...' : '提交后台任务'),
              ),
            ],
          ),
          if (latestJob != null) ...[
            const SizedBox(height: 12),
            Text(
              '最近任务: ${latestJob.displayTitle} · ${buildJobPrimaryText(latestJob)}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            if (canHydrateLatest) ...[
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton.icon(
                  onPressed: () => _hydrateLatestJobResult(latestJob),
                  icon: const Icon(Icons.download_done_rounded),
                  label: const Text('载入最近后台结果'),
                ),
              ),
            ],
            const SizedBox(height: 12),
            JobEventTimeline(
              job: latestJob,
              title: '最近后台任务轨迹',
              emptyMessage: '后台优化开始执行后，这里会显示预测、求解和结果封装阶段。',
              onOpenOperation: () => _openJobInShellRuntime(latestJob),
              onRetry: latestJob.retryable ? () => _retryJob(latestJob) : null,
              onCancel: latestJob.isTerminal
                  ? null
                  : () => _cancelJob(latestJob),
              onApprove: latestJob.isAwaitingApproval
                  ? () => _resolveApproval(latestJob, approved: true)
                  : null,
              onReject: latestJob.isAwaitingApproval
                  ? () => _resolveApproval(latestJob, approved: false)
                  : null,
            ),
          ],
          const SizedBox(height: 16),
          JobActivityList(
            jobs: _jobViewModel.jobs,
            emptyMessage: '暂无后台优化任务。提交后可在这里观察排队、运行和完成状态。',
            compact: true,
            onOpenJob: _openJobInShellRuntime,
          ),
        ],
      ),
    );
  }

  Widget _buildOperationsCard(AssetChainSummary? chain) {
    final result = _result;
    final summary = result?.optimization?.summary;
    final diagnostics = result?.optimization?.diagnostics;
    final constraintHits = result?.optimization?.constraintHits;
    final explainability = result?.modelExplainability;
    final hasExportableResult = result != null && result.isSuccess;
    final latestCompletedJob = _jobViewModel.jobs.cast<JobRecord?>().firstWhere(
      (job) =>
          job?.status == 'succeeded' &&
          job?.result.containsKey('optimization') == true,
      orElse: () => null,
    );
    final scenarioDigest = _buildScenarioDigest();
    final strategyDigest = _buildStrategyDigest(result);
    final comparisonDigest = _buildComparisonDigest(result, _previousResult);
    final snapshotDigest = _buildSnapshotDigest(result, latestCompletedJob);
    final operationsDigest = _buildOperationsDigest(
      diagnostics,
      constraintHits,
      explainability,
    );

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('结果操作', style: AppTextStyles.h4),
          const SizedBox(height: 8),
          Text(
            hasExportableResult
                ? '导出当前优化结果，或复制关键节省摘要给团队协作。'
                : '先运行一次优化，再导出结果或复制摘要。',
            style: AppTextStyles.bodySmall,
          ),
          if (chain != null) ...[
            const SizedBox(height: 12),
            WorkspaceContextBanner(
              accent: AppColors.warning,
              workspaceLabel:
                  _activeLaunchContext?.workspaceTargetLabel ??
                  chain.workspaceTargetLabel,
              cardLabel:
                  _activeLaunchContext?.cardTargetLabel ??
                  chain.cardTargetLabel,
              incidentLabel:
                  _activeLaunchContext?.incidentTargetLabel ??
                  chain.incidentTargetLabel,
              summary:
                  _activeLaunchContext?.workspaceBrief ?? chain.workspaceBrief,
            ),
          ],
          const SizedBox(height: 16),
          WorkspaceDigestList(
            items: [
              WorkspaceDigestListItem(
                title: 'Scenario Digest',
                value: scenarioDigest,
                icon: Icons.tune_rounded,
                accent: AppColors.primary,
                highlighted: _operationsDigestFocus(
                  chain,
                  'scenario',
                  _activeLaunchContext,
                ),
                highlightLabel: '当前链路焦点',
              ),
              WorkspaceDigestListItem(
                title: '策略摘要',
                value: strategyDigest,
                icon: Icons.route_rounded,
                accent: AppColors.cta,
                highlighted: _operationsDigestFocus(
                  chain,
                  'strategy',
                  _activeLaunchContext,
                ),
                highlightLabel: '当前链路焦点',
              ),
              WorkspaceDigestListItem(
                title: '结果对比',
                value: comparisonDigest,
                icon: Icons.compare_arrows_rounded,
                accent: AppColors.success,
                highlighted: _operationsDigestFocus(
                  chain,
                  'comparison',
                  _activeLaunchContext,
                ),
                highlightLabel: '当前链路焦点',
              ),
              WorkspaceDigestListItem(
                title: 'Result Snapshot',
                value: snapshotDigest,
                icon: Icons.inventory_2_rounded,
                accent: AppColors.warning,
                highlighted: _operationsDigestFocus(
                  chain,
                  'snapshot',
                  _activeLaunchContext,
                ),
                highlightLabel: '当前链路焦点',
              ),
              WorkspaceDigestListItem(
                title: '运维摘要',
                value: operationsDigest,
                icon: Icons.monitor_heart_rounded,
                accent: AppColors.primary,
                highlighted: _operationsDigestFocus(
                  chain,
                  'operations',
                  _activeLaunchContext,
                ),
                highlightLabel: '当前链路焦点',
              ),
            ],
          ),
          const SizedBox(height: 16),
          WorkspaceActionDeck(
            lanes: [
              WorkspaceActionLane(
                title: '结果导出与协作',
                description: hasExportableResult
                    ? '将当前优化结果、节省摘要和策略摘要直接打包给协作方，不再让复制动作散在一排按钮里。'
                    : '先完成一次有效优化，再导出 JSON、快照和节省摘要。',
                accent: AppColors.primary,
                icon: Icons.ios_share_rounded,
                workspaceLabel:
                    _activeLaunchContext?.workspaceTargetLabel ??
                    chain?.workspaceTargetLabel,
                cardLabel:
                    _activeLaunchContext?.cardTargetLabel ??
                    chain?.cardTargetLabel,
                incidentLabel:
                    _activeLaunchContext?.incidentTargetLabel ??
                    chain?.incidentTargetLabel,
                summary:
                    _activeLaunchContext?.workspaceBrief ??
                    chain?.workspaceBrief,
                statusLabel: hasExportableResult ? '就绪' : '待完成',
                statusColor: hasExportableResult
                    ? AppColors.success
                    : AppColors.warning,
                recommendedActionKey: _recommendedExportAction(
                  chain,
                  _activeLaunchContext,
                  hasExportableResult: hasExportableResult,
                ),
                actions: [
                  WorkspaceActionLaneAction(
                    label: '复制结果 JSON',
                    icon: Icons.download_rounded,
                    onTap: hasExportableResult ? _copyResultJson : null,
                    semanticKey: 'copy_result_json',
                    tone: WorkspaceActionLaneTone.primary,
                  ),
                  WorkspaceActionLaneAction(
                    label: '复制节省摘要',
                    icon: Icons.content_copy_rounded,
                    onTap: hasExportableResult ? _copySummaryDigest : null,
                    semanticKey: 'copy_summary_digest',
                    tone: WorkspaceActionLaneTone.tonal,
                  ),
                  WorkspaceActionLaneAction(
                    label: '复制配置摘要',
                    icon: Icons.copy_rounded,
                    onTap: _copyScenarioDigest,
                    semanticKey: 'copy_scenario_digest',
                  ),
                  WorkspaceActionLaneAction(
                    label: '复制策略摘要',
                    icon: Icons.rule_rounded,
                    onTap: hasExportableResult ? _copyStrategyDigest : null,
                    semanticKey: 'copy_strategy_digest',
                  ),
                ],
              ),
              WorkspaceActionLane(
                title: '运维回填与复盘',
                description: latestCompletedJob != null
                    ? '把最近后台结果、结果护照和运维摘要收在同一条复盘车道里，便于值班处理。'
                    : '当前还没有可回填的后台结果，但可以先刷新任务队列并保留运维摘要出口。',
                accent: AppColors.warning,
                icon: Icons.monitor_heart_rounded,
                workspaceLabel:
                    _activeLaunchContext?.workspaceTargetLabel ??
                    chain?.workspaceTargetLabel,
                cardLabel:
                    _activeLaunchContext?.cardTargetLabel ??
                    chain?.cardTargetLabel,
                incidentLabel:
                    _activeLaunchContext?.incidentTargetLabel ??
                    chain?.incidentTargetLabel,
                summary:
                    _activeLaunchContext?.workspaceBrief ??
                    chain?.workspaceBrief,
                statusLabel: latestCompletedJob == null ? 'Waiting' : 'Hot',
                statusColor: latestCompletedJob == null
                    ? AppColors.textSecondary
                    : AppColors.warning,
                recommendedActionKey: _recommendedOperationsAction(
                  chain,
                  _activeLaunchContext,
                  latestCompletedJob != null,
                ),
                actions: [
                  WorkspaceActionLaneAction(
                    label: '复制结果护照',
                    icon: Icons.inventory_2_rounded,
                    onTap: hasExportableResult ? _copySnapshotDigest : null,
                    semanticKey: 'copy_snapshot_digest',
                    tone: WorkspaceActionLaneTone.tonal,
                  ),
                  WorkspaceActionLaneAction(
                    label: '复制运维摘要',
                    icon: Icons.monitor_heart_rounded,
                    onTap: hasExportableResult ? _copyOperationsDigest : null,
                    semanticKey: 'copy_operations_digest',
                  ),
                  WorkspaceActionLaneAction(
                    label: '载入最近后台结果',
                    icon: Icons.download_done_rounded,
                    onTap: latestCompletedJob == null
                        ? null
                        : () => _hydrateLatestJobResult(latestCompletedJob),
                    semanticKey: 'load_latest_job_result',
                    tone: WorkspaceActionLaneTone.primary,
                  ),
                  WorkspaceActionLaneAction(
                    label: '刷新任务状态',
                    icon: Icons.sync_rounded,
                    onTap: _jobViewModel.loadJobs,
                    semanticKey: 'refresh_jobs',
                  ),
                ],
              ),
            ],
          ),
          if (summary != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              ),
              child: Text(
                '本次优化节省 ${summary.savingsFormatted}，较原始成本下降 ${summary.savingsPercentFormatted}。',
                style: AppTextStyles.bodyMedium,
              ),
            ),
          ],
          if (latestCompletedJob != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.background,
                borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              ),
              child: Text(
                '最近后台产物: ${latestCompletedJob.completedAt == null ? "--" : DateFormat("MM-dd HH:mm").format(latestCompletedJob.completedAt!.toLocal())} · '
                '${buildJobPrimaryText(latestCompletedJob)}',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _copyResultJson() async {
    final result = _result;
    if (result == null) {
      return;
    }

    final payload = const JsonEncoder.withIndent('  ').convert(result.toJson());
    await Clipboard.setData(ClipboardData(text: payload));
    if (!mounted) {
      return;
    }
    _showSuccessSnackBar(_optimizationFeedbackMessage('优化结果 JSON 已复制'));
  }

  Future<void> _copySummaryDigest() async {
    final summary = _result?.optimization?.summary;
    if (summary == null) {
      return;
    }

    final digest =
        '优化节省 ${summary.savingsFormatted}，'
        '总成本从 ${summary.totalCostWithoutBattery.toStringAsFixed(2)} 元 '
        '降至 ${summary.totalCostWithBattery.toStringAsFixed(2)} 元，'
        '降幅 ${summary.savingsPercentFormatted}。';
    await Clipboard.setData(ClipboardData(text: digest));
    if (!mounted) {
      return;
    }
    _showSuccessSnackBar(_optimizationFeedbackMessage('节省摘要已复制'));
  }

  Future<void> _copyScenarioDigest() async {
    await Clipboard.setData(ClipboardData(text: _buildScenarioDigest()));
    if (!mounted) {
      return;
    }
    _showSuccessSnackBar(_optimizationFeedbackMessage('配置摘要已复制'));
  }

  Future<void> _copyStrategyDigest() async {
    final result = _result;
    if (result == null || !result.isSuccess) {
      return;
    }

    await Clipboard.setData(ClipboardData(text: _buildStrategyDigest(result)));
    if (!mounted) {
      return;
    }
    _showSuccessSnackBar(_optimizationFeedbackMessage('策略摘要已复制'));
  }

  Future<void> _copySnapshotDigest() async {
    final result = _result;
    if (result == null || !result.isSuccess) {
      return;
    }

    final latestCompletedJob = _jobViewModel.jobs.cast<JobRecord?>().firstWhere(
      (job) =>
          job?.status == 'succeeded' &&
          job?.result.containsKey('optimization') == true,
      orElse: () => null,
    );
    await Clipboard.setData(
      ClipboardData(text: _buildSnapshotDigest(result, latestCompletedJob)),
    );
    if (!mounted) {
      return;
    }
    _showSuccessSnackBar(_optimizationFeedbackMessage('结果护照已复制'));
  }

  Future<void> _copyOperationsDigest() async {
    final result = _result;
    if (result == null || !result.isSuccess) {
      return;
    }

    await Clipboard.setData(
      ClipboardData(
        text: _buildOperationsDigest(
          result.optimization?.diagnostics,
          result.optimization?.constraintHits,
          result.modelExplainability,
        ),
      ),
    );
    if (!mounted) {
      return;
    }
    _showSuccessSnackBar(_optimizationFeedbackMessage('运维摘要已复制'));
  }

  Future<void> _copyOptimizationAssetPassport(OptimizationAsset asset) async {
    await Clipboard.setData(
      ClipboardData(text: _buildOptimizationAssetPassport(asset)),
    );
    if (!mounted) {
      return;
    }
    _showSuccessSnackBar(_optimizationFeedbackMessage('优化护照已复制'));
  }

  void _hydrateLatestJobResult(JobRecord latestJob) {
    final payload = latestJob.result;
    if (payload.isEmpty) {
      _showErrorSnackBar('最近后台任务尚未生成可载入结果');
      return;
    }

    final success = _viewModel.loadResultFromJobPayload(payload);
    if (success) {
      _showSuccessSnackBar(_optimizationFeedbackMessage('已载入最近后台优化结果'));
      _focusOptimizationResults();
      return;
    }

    final message = _errorMessage;
    if (message != null) {
      _showErrorSnackBar(message);
    }
  }

  Future<void> _retryJob(JobRecord job) async {
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

    final retried = await _jobViewModel.retryJob(job.jobId);
    if (!mounted) {
      return;
    }
    if (retried != null) {
      await _openJobInShellRuntime(retried);
      _showSuccessSnackBar(_optimizationFeedbackMessage('后台优化任务已重新排队'));
      await _refreshSharedProjection();
      return;
    }
    final error = _jobViewModel.errorMessage;
    if (error != null) {
      _showErrorSnackBar(error);
    }
  }

  Future<void> _focusOptimizationResults() async {
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final context = _optimizationResultKey.currentContext;
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

  Future<void> _cancelJob(JobRecord job) async {
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

    final cancelled = await _jobViewModel.cancelJob(job);
    if (!mounted) {
      return;
    }
    if (cancelled != null) {
      await _openJobInShellRuntime(cancelled);
      _showSuccessSnackBar(_optimizationFeedbackMessage('后台优化任务已提交取消'));
      await _refreshSharedProjection();
      return;
    }
    final error = _jobViewModel.errorMessage;
    if (error != null) {
      _showErrorSnackBar(error);
    }
  }

  Future<void> _resolveApproval(JobRecord job, {required bool approved}) async {
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

    final updated = await _jobViewModel.resolveApproval(
      job,
      approved: approved,
    );
    if (!mounted) {
      return;
    }
    if (updated != null) {
      await _openJobInShellRuntime(updated);
      _showSuccessSnackBar(
        _optimizationFeedbackMessage(approved ? '后台优化任务已批准执行' : '后台优化任务已驳回'),
      );
      await _refreshSharedProjection();
      return;
    }
    final error = _jobViewModel.errorMessage;
    if (error != null) {
      _showErrorSnackBar(error);
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
    final dashboardViewModel = widget.dashboardViewModel;
    if (dashboardViewModel != null) {
      await dashboardViewModel.loadSummary();
    }
  }

  void _showSharedActionOutcome(ShellActionOutcome outcome) {
    final backgroundColor = switch (outcome.tone) {
      ShellActionTone.success => AppColors.success,
      ShellActionTone.warning => AppColors.warning,
      ShellActionTone.error => AppColors.error,
      ShellActionTone.info => AppColors.primary,
    };
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(outcome.message),
        backgroundColor: backgroundColor,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  String _buildScenarioDigest() {
    return [
      'scenario=${_scenarioLabel(_controls.selectedScenario)}',
      'target_date=${DateFormat('yyyy-MM-dd').format(_controls.targetDate)}',
      'initial_soc=${(_controls.initialSoc * 100).toStringAsFixed(0)}%',
      'capacity=${_controls.batteryCapacity.toStringAsFixed(0)}kWh',
      'max_power=${_controls.maxPower.toStringAsFixed(0)}kW',
      'temperature_adjust=${_controls.temperatureAdjust.toStringAsFixed(1)}°C',
    ].join(' | ');
  }

  String _buildStrategyDigest(OptimizationResponse? result) {
    final strategy = result?.optimization?.strategy;
    final summary = result?.optimization?.summary;
    if (strategy == null || summary == null) {
      return '运行优化后，这里会给出充放电时段、循环效率和成本摘要。';
    }

    return [
      'charging=${strategy.chargingHoursFormatted}',
      'discharging=${strategy.dischargingHoursFormatted}',
      'cycle_efficiency=${summary.cycleEfficiency.toStringAsFixed(1)}%',
      'charged=${summary.totalCharged.toStringAsFixed(1)}kWh',
      'discharged=${summary.totalDischarged.toStringAsFixed(1)}kWh',
    ].join(' | ');
  }

  String _buildComparisonDigest(
    OptimizationResponse? current,
    OptimizationResponse? previous,
  ) {
    final currentSummary = current?.optimization?.summary;
    final previousSummary = previous?.optimization?.summary;
    if (currentSummary == null) {
      return '当前还没有可比较的优化结果。先运行一次试算或载入最近后台结果。';
    }
    if (previousSummary == null) {
      return '当前结果已就绪。再次试算不同配置后，这里会显示节省与成本差异。';
    }

    final savingsDelta = currentSummary.savings - previousSummary.savings;
    final costDelta =
        currentSummary.totalCostWithBattery -
        previousSummary.totalCostWithBattery;
    return [
      'savings_delta=${savingsDelta >= 0 ? '+' : ''}${savingsDelta.toStringAsFixed(2)}元',
      'optimized_cost_delta=${costDelta >= 0 ? '+' : ''}${costDelta.toStringAsFixed(2)}元',
      'current=${currentSummary.savingsFormatted}',
      'previous=${previousSummary.savingsFormatted}',
    ].join(' | ');
  }

  String _buildSnapshotDigest(
    OptimizationResponse? result,
    JobRecord? latestCompletedJob,
  ) {
    final summary = result?.optimization?.summary;
    if (summary == null) {
      return '当前没有可归档的优化结果。先运行一次试算或载入后台结果。';
    }

    final version = latestCompletedJob == null
        ? 'session'
        : DateFormat('MMdd-HHmm').format(
            (latestCompletedJob.completedAt ?? DateTime.now()).toLocal(),
          );
    return [
      'version=$version',
      'target_date=${DateFormat('yyyy-MM-dd').format(_controls.targetDate)}',
      'initial_soc=${(_controls.initialSoc * 100).toStringAsFixed(0)}%',
      'savings=${summary.savingsFormatted}',
      'savings_percent=${summary.savingsPercentFormatted}',
      if (latestCompletedJob != null)
        'job=${latestCompletedJob.jobId.substring(0, 8)}',
    ].join(' | ');
  }

  String _buildOperationsDigest(
    SolverDiagnostics? diagnostics,
    ConstraintHits? constraintHits,
    ModelExplainability? explainability,
  ) {
    if (diagnostics == null &&
        constraintHits == null &&
        explainability == null) {
      return '当前结果未返回求解器诊断、约束命中或解释性信息。';
    }

    final segments = <String>[];
    if (diagnostics != null) {
      segments.add('runtime=${diagnostics.runtimeLabel}');
      if (diagnostics.mipGap != null) {
        segments.add('mip_gap=${diagnostics.mipGap!.toStringAsFixed(4)}');
      }
      if (diagnostics.nodeCount != null) {
        segments.add('nodes=${diagnostics.nodeCount}');
      }
    }
    if (constraintHits != null) {
      segments.add(
        'constraint_hits=${constraintHits.socMinHits + constraintHits.socMaxHits + constraintHits.maxChargeHits + constraintHits.maxDischargeHits}',
      );
    }
    if (explainability?.topFeature != null) {
      segments.add(
        'top_feature=${explainability!.topFeature} (${explainability.topFeaturePercent})',
      );
    }
    return segments.join(' | ');
  }

  String _buildOptimizationAssetPassport(OptimizationAsset asset) {
    final completedAt = asset.completedAt == null
        ? '--'
        : DateFormat('yyyy-MM-dd HH:mm').format(asset.completedAt!.toLocal());
    return [
      'Optimization Asset Passport',
      'version=v${asset.version}',
      'job_id=${asset.jobId}',
      'target_date=${asset.targetDate ?? '--'}',
      'initial_soc=${asset.initialSoc == null ? '--' : (asset.initialSoc! * 100).toStringAsFixed(0)}%',
      'battery_capacity=${asset.batteryCapacity?.toStringAsFixed(1) ?? '--'}kWh',
      'battery_power=${asset.batteryPower?.toStringAsFixed(1) ?? '--'}kW',
      'savings=${asset.savings?.toStringAsFixed(2) ?? '--'}元',
      'savings_percent=${asset.savingsPercent == null ? '--' : (asset.savingsPercent! * 100).toStringAsFixed(1)}%',
      'completed_at=$completedAt',
    ].join('\n');
  }
}

bool _operationsDigestFocus(
  AssetChainSummary? chain,
  String card,
  WorkbenchLaunchContext? continuationContext,
) {
  final cardTarget = continuationContext?.cardTarget ?? chain?.cardTarget;
  final sectionTarget =
      continuationContext?.workspaceTarget == 'optimization_registry'
      ? 'optimization_assets'
      : chain?.sectionTarget;
  if (cardTarget == null && chain == null) {
    return false;
  }
  switch (cardTarget) {
    case 'strategy':
      return card == 'strategy';
    case 'comparison':
      return card == 'comparison';
    case 'latest_snapshot':
    case 'recent_artifact':
    case 'registry_summary':
    case 'summary':
      return card == 'snapshot';
    case 'solver_health':
    case 'constraint_pressure':
    case 'explainability_probe':
      return card == 'operations';
  }
  return sectionTarget == 'optimization_assets'
      ? card == 'snapshot'
      : card == 'operations' &&
            (chain?.status == 'active' || chain?.status == 'incident');
}

String _recommendedExportAction(
  AssetChainSummary? chain,
  WorkbenchLaunchContext? continuationContext, {
  required bool hasExportableResult,
}) {
  final cardTarget = continuationContext?.cardTarget ?? chain?.cardTarget;
  if (!hasExportableResult) {
    return 'copy_scenario_digest';
  }
  switch (cardTarget) {
    case 'solver_health':
    case 'constraint_pressure':
    case 'explainability_probe':
      return 'copy_strategy_digest';
    case 'recent_artifact':
    case 'latest_snapshot':
    case 'registry_summary':
      return 'copy_result_json';
    default:
      return 'copy_result_json';
  }
}

String _recommendedOperationsAction(
  AssetChainSummary? chain,
  WorkbenchLaunchContext? continuationContext,
  bool hasLatestCompletedJob,
) {
  final workspaceTarget =
      continuationContext?.workspaceTarget ?? chain?.workspaceTarget;
  final cardTarget = continuationContext?.cardTarget ?? chain?.cardTarget;
  if (workspaceTarget == 'optimization_registry' ||
      cardTarget == 'latest_snapshot') {
    return hasLatestCompletedJob
        ? 'load_latest_job_result'
        : 'copy_snapshot_digest';
  }
  switch (cardTarget) {
    case 'solver_health':
    case 'constraint_pressure':
    case 'explainability_probe':
      return 'copy_operations_digest';
    case 'recent_artifact':
      return hasLatestCompletedJob
          ? 'load_latest_job_result'
          : 'copy_snapshot_digest';
    default:
      return hasLatestCompletedJob ? 'load_latest_job_result' : 'refresh_jobs';
  }
}

class _OptimizationHighlightCard extends StatelessWidget {
  const _OptimizationHighlightCard({
    required this.label,
    required this.value,
    required this.helper,
    required this.accent,
  });

  final String label;
  final String value;
  final String helper;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: accent.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            label,
            style: AppTextStyles.labelMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            value,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.h4.copyWith(color: accent),
          ),
          const SizedBox(height: 6),
          Text(
            helper,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.bodySmall.copyWith(color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }
}
