/// 工业驾驶舱主导航壳
library;

import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/ai_lab_launch_intent.dart';
import '../models/data_analysis_launch_intent.dart';
import '../models/optimization_launch_intent.dart';
import '../models/dashboard_summary.dart';
import '../models/job_record.dart';
import '../models/shell_action_outcome.dart';
import '../models/workbench_runtime_models.dart';
import '../repositories/auth_repository.dart';
import '../screens/ai_lab_screen.dart';
import '../screens/data_analysis_screen.dart';
import '../screens/history_audit_screen.dart';
import '../screens/modeling_screen.dart';
import '../screens/operations_hub_screen.dart';
import '../services/auth_gateway.dart';
import '../utils/asset_chain_context.dart';
import '../utils/responsive_helper.dart';
import '../viewmodels/approval_queue_view_model.dart';
import '../viewmodels/compute_governance_view_model.dart';
import '../viewmodels/control_task_view_model.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../viewmodels/main_shell_runtime_view_model.dart';
import '../viewmodels/operation_console_view_model.dart';
import 'navigation/lazy_workspace_stack.dart';
import 'navigation/main_shell_runtime_scope.dart';
import 'navigation/shell_runtime_action_bar.dart';
import 'navigation/shell_runtime_panel.dart';
import 'operations/approval_resolution_dialog.dart';
import 'operations/workbench_page_frame.dart';
import 'operations/system_status_strip.dart';

class MainNavigation extends StatefulWidget {
  /// The app-wide shell owns the only top-level Scaffold for the default
  /// product experience. Default pages always render as embedded content.
  const MainNavigation({
    super.key,
    AuthRepository? authRepository,
    AuthGateway? authGateway,
    DashboardViewModel? dashboardViewModel,
    ComputeGovernanceViewModel? computeGovernanceViewModel,
    ControlTaskViewModel? controlTaskViewModel,
    ApprovalQueueViewModel? approvalQueueViewModel,
    OperationConsoleViewModel? operationConsoleViewModel,
  }) : _authRepository = authRepository,
       _authGateway = authGateway,
       _dashboardViewModel = dashboardViewModel,
       _computeGovernanceViewModel = computeGovernanceViewModel,
       _controlTaskViewModel = controlTaskViewModel,
       _approvalQueueViewModel = approvalQueueViewModel,
       _operationConsoleViewModel = operationConsoleViewModel,
       _customPages = null,
       assert(
         authRepository == null || authGateway == null,
         'Provide either authRepository or authGateway, not both.',
       );

  /// Custom pages are allowed to define their own page-shell contract.
  const MainNavigation.custom({
    super.key,
    required List<Widget> pages,
    AuthRepository? authRepository,
    AuthGateway? authGateway,
    DashboardViewModel? dashboardViewModel,
    ComputeGovernanceViewModel? computeGovernanceViewModel,
    ControlTaskViewModel? controlTaskViewModel,
    ApprovalQueueViewModel? approvalQueueViewModel,
    OperationConsoleViewModel? operationConsoleViewModel,
  }) : _authRepository = authRepository,
       _authGateway = authGateway,
       _dashboardViewModel = dashboardViewModel,
       _computeGovernanceViewModel = computeGovernanceViewModel,
       _controlTaskViewModel = controlTaskViewModel,
       _approvalQueueViewModel = approvalQueueViewModel,
       _operationConsoleViewModel = operationConsoleViewModel,
       _customPages = pages,
       assert(
         authRepository == null || authGateway == null,
         'Provide either authRepository or authGateway, not both.',
       ),
       assert(
         pages.length == 5,
         'MainNavigation.custom expects exactly 5 pages.',
       );

  final AuthRepository? _authRepository;
  final AuthGateway? _authGateway;
  final DashboardViewModel? _dashboardViewModel;
  final ComputeGovernanceViewModel? _computeGovernanceViewModel;
  final ControlTaskViewModel? _controlTaskViewModel;
  final ApprovalQueueViewModel? _approvalQueueViewModel;
  final OperationConsoleViewModel? _operationConsoleViewModel;
  final List<Widget>? _customPages;

  @override
  State<MainNavigation> createState() => _MainNavigationState();
}

class _MainNavigationState extends State<MainNavigation> {
  static const List<_NavDestination> _destinations = [
    _NavDestination(label: '概览', icon: Icons.dashboard_customize_rounded),
    _NavDestination(label: '能源优化', icon: Icons.bolt_rounded),
    _NavDestination(label: '数据分析', icon: Icons.analytics_rounded),
    _NavDestination(label: 'AI Lab', icon: Icons.auto_awesome_rounded),
    _NavDestination(label: '历史与审计', icon: Icons.fact_check_rounded),
  ];

  int _currentIndex = 0;
  late final AuthRepository _authRepository;
  late final MainShellRuntimeViewModel _shellRuntime;
  StreamSubscription<User?>? _authSubscription;
  User? _currentUser;
  AiLabLaunchIntent? _pendingAiLabIntent;
  DataAnalysisLaunchIntent? _pendingDataAnalysisIntent;
  OptimizationLaunchIntent? _pendingOptimizationIntent;
  bool _shellBootstrapping = false;

  bool get _hasAuthenticatedUser => _currentUser != null;
  bool get _usesDefaultShell => widget._customPages == null;
  DashboardViewModel get _dashboardViewModel =>
      _shellRuntime.dashboardViewModel;
  ComputeGovernanceViewModel get _computeGovernanceViewModel =>
      _shellRuntime.computeGovernanceViewModel;
  ControlTaskViewModel get _controlTaskViewModel =>
      _shellRuntime.controlTaskViewModel;
  ApprovalQueueViewModel get _approvalQueueViewModel =>
      _shellRuntime.approvalQueueViewModel;
  OperationConsoleViewModel get _operationConsoleViewModel =>
      _shellRuntime.operationConsoleViewModel;

  @override
  void initState() {
    super.initState();
    _authRepository =
        widget._authRepository ??
        GatewayAuthRepository(authGateway: widget._authGateway);
    _shellRuntime = MainShellRuntimeViewModel(
      dashboardViewModel: widget._dashboardViewModel,
      computeGovernanceViewModel: widget._computeGovernanceViewModel,
      controlTaskViewModel: widget._controlTaskViewModel,
      approvalQueueViewModel: widget._approvalQueueViewModel,
      operationConsoleViewModel: widget._operationConsoleViewModel,
    );
    _currentUser = _authRepository.currentUser;
    _authSubscription = _authRepository.authStateChanges.listen((user) {
      if (!mounted || user == _currentUser) {
        return;
      }
      setState(() {
        _currentUser = user;
      });
    });
    if (_usesDefaultShell) {
      _shellBootstrapping = true;
      unawaited(_bootstrapShell());
    }
  }

  @override
  void dispose() {
    _authSubscription?.cancel();
    _shellRuntime.dispose();
    super.dispose();
  }

  Future<void> _handleSignOut() async {
    if (!_hasAuthenticatedUser) {
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认退出登录'),
        content: const Text('退出后将返回登录页。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(backgroundColor: AppColors.error),
            child: const Text('退出'),
          ),
        ],
      ),
    );

    if (confirmed != true) {
      return;
    }

    try {
      await _authRepository.signOut();
      if (!mounted) {
        return;
      }
      setState(() {
        _currentUser = null;
        _currentIndex = 0;
      });
      _shellRuntime.closePanel();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('已退出登录'),
          backgroundColor: AppColors.success,
        ),
      );
    } catch (e) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('退出失败: $e'), backgroundColor: AppColors.error),
      );
    }
  }

  void _showUserInfo() {
    final user = _currentUser;
    if (user == null) {
      return;
    }

    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('用户信息'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _InfoRow(label: '邮箱', value: user.email ?? '未设置'),
            const SizedBox(height: 12),
            _InfoRow(label: 'UID', value: user.uid),
            const SizedBox(height: 12),
            _InfoRow(label: '状态', value: user.emailVerified ? '已验证' : '未验证'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return MainShellRuntimeScope(
      runtime: _shellRuntime,
      child: ListenableBuilder(
        listenable: _shellRuntime,
        builder: (context, _) {
          final desktopShell = ResponsiveHelper.isDesktop(context);
          final projection = _shellRuntime.projection;
          final statusItems = _prioritizedStatusItems(
            projection.summary?.systemStatus ?? const <SystemStatusItem>[],
          );
          final statusHeadline = _statusHeadline(projection.summary);
          final showBootPlaceholder =
              _usesDefaultShell &&
              _shellBootstrapping &&
              projection.summary == null &&
              !_shellRuntime.hasSelectedOperation;

          if (desktopShell) {
            return Scaffold(
              backgroundColor: AppColors.background,
              body: Column(
                children: [
                  SystemStatusStrip(
                    items: statusItems,
                    compact: true,
                    headline: statusHeadline,
                    maxVisibleItems: 4,
                    trailing: _buildAccountActions(compact: true),
                  ),
                  Expanded(
                    child: Row(
                      children: [
                        NavigationRail(
                          selectedIndex: _currentIndex,
                          onDestinationSelected: _onNavTap,
                          extended: MediaQuery.of(context).size.width >= 1280,
                          minWidth: 88,
                          labelType: NavigationRailLabelType.none,
                          leading: Padding(
                            padding: const EdgeInsets.fromLTRB(12, 16, 12, 12),
                            child: Column(
                              children: [
                                Container(
                                  width: 48,
                                  height: 48,
                                  decoration: BoxDecoration(
                                    gradient: AppColors.primaryGradient,
                                    borderRadius: BorderRadius.circular(
                                      AppDecorations.radiusLg,
                                    ),
                                  ),
                                  child: const Icon(
                                    Icons.hub_rounded,
                                    color: Colors.white,
                                  ),
                                ),
                                const SizedBox(height: 12),
                                Text(
                                  'Sentinel Ops',
                                  style: AppTextStyles.labelMedium,
                                ),
                              ],
                            ),
                          ),
                          destinations: _destinations
                              .asMap()
                              .entries
                              .map(
                                (entry) => NavigationRailDestination(
                                  icon: Icon(entry.value.icon),
                                  selectedIcon: Icon(entry.value.icon),
                                  label: Text(entry.value.label),
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 6,
                                  ),
                                ),
                              )
                              .toList(growable: false),
                        ),
                        const VerticalDivider(width: 1),
                        Expanded(
                          child: SafeArea(
                            top: false,
                            bottom: false,
                            child: showBootPlaceholder
                                ? _buildShellBootPlaceholder()
                                : LazyWorkspaceStack(
                                    currentIndex: _currentIndex,
                                    pageCount: _pageCount,
                                    pageBuilder: _buildPage,
                                  ),
                          ),
                        ),
                        if (_usesDefaultShell &&
                            _shellRuntime.panelVisible) ...[
                          const VerticalDivider(width: 1),
                          SizedBox(width: 420, child: _buildRuntimePanel()),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            );
          }

          return Scaffold(
            backgroundColor: AppColors.background,
            body: SafeArea(
              bottom: false,
              child: showBootPlaceholder
                  ? _buildShellBootPlaceholder()
                  : LazyWorkspaceStack(
                      currentIndex: _currentIndex,
                      pageCount: _pageCount,
                      pageBuilder: _buildPage,
                    ),
            ),
            bottomNavigationBar: Container(
              decoration: BoxDecoration(
                color: AppColors.surface,
                border: const Border(top: BorderSide(color: AppColors.border)),
              ),
              child: SafeArea(
                top: false,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
                      child: Row(
                        children: [Expanded(child: _buildAccountActions())],
                      ),
                    ),
                    NavigationBar(
                      selectedIndex: _currentIndex,
                      onDestinationSelected: _onNavTap,
                      destinations: _destinations
                          .map(
                            (item) => NavigationDestination(
                              icon: Icon(item.icon),
                              label: item.label,
                            ),
                          )
                          .toList(growable: false),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildAccountActions({bool compact = false}) {
    if (!_usesDefaultShell) {
      return Wrap(
        spacing: 8,
        runSpacing: 8,
        alignment: WrapAlignment.end,
        children: [
          OutlinedButton.icon(
            key: const ValueKey('main-nav-user-info'),
            onPressed: _hasAuthenticatedUser ? _showUserInfo : null,
            icon: const Icon(Icons.account_circle_outlined),
            label: Text(compact ? '用户' : '用户信息'),
          ),
          FilledButton.tonalIcon(
            key: const ValueKey('main-nav-sign-out'),
            onPressed: _hasAuthenticatedUser ? _handleSignOut : null,
            icon: const Icon(Icons.logout_rounded),
            label: Text(compact ? '退出' : '退出登录'),
          ),
        ],
      );
    }

    return ShellRuntimeActionBar(
      projection: _shellRuntime.projection,
      onOpenApprovals: _openApprovalPanel,
      onOpenOperations: _openOperationPanel,
      onOpenNotifications: _openNotificationsPanel,
      onShowUserInfo: _showUserInfo,
      onSignOut: _handleSignOut,
      compact: compact,
      enableAccountActions: _hasAuthenticatedUser,
    );
  }

  List<SystemStatusItem> _prioritizedStatusItems(List<SystemStatusItem> items) {
    const preferredOrder = ['api', 'storage', 'model', 'rag', 'orchestrator'];
    final preferred = <SystemStatusItem>[];

    for (final key in preferredOrder) {
      final match = items.cast<SystemStatusItem?>().firstWhere(
        (item) => item?.key == key,
        orElse: () => null,
      );
      if (match != null) {
        preferred.add(match);
      }
    }

    final warnings = items
        .where((item) => item.status == 'warning' || item.status == 'error')
        .where((item) => !preferred.contains(item));
    final healthy = items
        .where((item) => item.status != 'warning' && item.status != 'error')
        .where((item) => !preferred.contains(item));

    return [
      ...warnings,
      ...preferred,
      ...healthy,
    ].take(4).toList(growable: false);
  }

  String? _statusHeadline(DashboardSummary? summary) {
    if (summary == null) {
      return null;
    }
    for (final alert in summary.alerts) {
      final title = alert.title.trim();
      if (title.isEmpty) {
        continue;
      }
      if (!title.endsWith('状态异常')) {
        return title;
      }
    }
    if (summary.kpis.failedJobs > 0) {
      return '当前有 ${summary.kpis.failedJobs} 个失败任务需要关注';
    }
    if (summary.dutySummary.focusWatch.isNotEmpty) {
      return summary.dutySummary.focusWatch;
    }
    return '系统运行稳定，可直接进入当前工作流';
  }

  Future<void> _bootstrapShell() async {
    try {
      await _shellRuntime.activateTab(WorkbenchTab.fromIndex(_currentIndex));
    } finally {
      if (mounted) {
        setState(() {
          _shellBootstrapping = false;
        });
      }
    }
  }

  Widget _buildShellBootPlaceholder() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Container(
            padding: const EdgeInsets.all(28),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(AppDecorations.radiusXl),
              border: Border.all(color: AppColors.border),
              boxShadow: AppDecorations.shadowSm,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const SizedBox(
                  width: 28,
                  height: 28,
                  child: CircularProgressIndicator(strokeWidth: 2.6),
                ),
                const SizedBox(height: 18),
                Text('正在准备驾驶舱', style: AppTextStyles.h3),
                const SizedBox(height: 8),
                Text(
                  '系统状态、关键任务和当前工作流正在同步，完成后会直接进入主界面。',
                  textAlign: TextAlign.center,
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _onNavTap(int index) {
    if (_currentIndex == index) {
      return;
    }
    if (index == 3 && _pendingAiLabIntent == null) {
      final defaultAiIntent = _defaultAiLabIntent();
      if (defaultAiIntent != null) {
        setState(() {
          _pendingAiLabIntent = defaultAiIntent;
        });
        _setCurrentIndex(index);
        return;
      }
    }
    _setCurrentIndex(index);
  }

  void _setCurrentIndex(int index) {
    setState(() {
      _currentIndex = index;
    });
    if (_usesDefaultShell) {
      unawaited(_shellRuntime.activateTab(WorkbenchTab.fromIndex(index)));
    }
  }

  AiLabLaunchIntent? _defaultAiLabIntent() {
    final assetSummary = _dashboardViewModel.summary?.assetSummary;
    if (assetSummary == null) {
      return null;
    }

    AssetChainSummary? findChain(String key) {
      return assetSummary.chainSummaries.cast<AssetChainSummary?>().firstWhere(
        (item) => item?.key == key,
        orElse: () => null,
      );
    }

    final latestModel = assetSummary.models.isNotEmpty
        ? assetSummary.models.first
        : null;
    final latestKnowledge = assetSummary.knowledgeBases.isNotEmpty
        ? assetSummary.knowledgeBases.first
        : null;

    if (latestModel?.storagePath != null &&
        latestModel!.storagePath!.isNotEmpty) {
      final context = buildLaunchContextFromChain(
        findChain('model'),
        prefix: '侧栏进入 AI Lab',
      );
      return AiLabLaunchIntent.deepLearning(
        latestModel.storagePath!,
        targetColumn: latestModel.targetColumn,
        sourceLabel: context == null
            ? '侧栏进入 AI Lab'
            : buildWorkbenchSourceLabel(context, prefix: '侧栏进入 AI Lab'),
        context: context,
      );
    }

    if (latestKnowledge?.storagePath != null &&
        latestKnowledge!.storagePath!.isNotEmpty) {
      final context = buildLaunchContextFromChain(
        findChain('knowledge'),
        prefix: '侧栏进入 AI Lab',
      );
      return AiLabLaunchIntent.rag(
        latestKnowledge.storagePath!,
        collectionName: latestKnowledge.collection,
        resetCollection: latestKnowledge.reset ?? false,
        sourceLabel: context == null
            ? '侧栏进入 AI Lab'
            : buildWorkbenchSourceLabel(context, prefix: '侧栏进入 AI Lab'),
        context: context,
      );
    }

    return null;
  }

  int get _pageCount => widget._customPages?.length ?? _destinations.length;

  Widget _buildPage(BuildContext context, int index, bool isActive) {
    final customPages = widget._customPages;
    if (customPages != null) {
      return customPages[index];
    }

    return switch (index) {
      0 => OperationsHubScreen(
        viewModel: _dashboardViewModel,
        computeGovernanceViewModel: _computeGovernanceViewModel,
        controlTaskViewModel: _controlTaskViewModel,
        approvalQueueViewModel: _approvalQueueViewModel,
        operationConsoleViewModel: _operationConsoleViewModel,
        shellProjection: _shellRuntime.projection,
        onNavigateToTab: _onNavTap,
        onOpenAiLab: _openAiLabWithIntent,
        onOpenDataAnalysis: _openDataAnalysisWithIntent,
        onOpenOptimization: _openOptimizationWithIntent,
        isActive: isActive,
        sharedRuntimeManaged: true,
        surfaceMode: WorkbenchSurfaceMode.embedded,
      ),
      1 => ModelingScreen(
        dashboardViewModel: _dashboardViewModel,
        jobsViewModel: _shellRuntime.jobFeeds.optimizationFeed,
        shellProjection: _shellRuntime.projection,
        launchIntent: _pendingOptimizationIntent,
        onLaunchIntentHandled: _clearOptimizationIntent,
        isActive: isActive,
        sharedRuntimeManaged: true,
        surfaceMode: WorkbenchSurfaceMode.embedded,
      ),
      2 => DataAnalysisScreen(
        onOpenHistory: () => _onNavTap(4),
        onSendToAiLab: _openAiLabWithIntent,
        dashboardViewModel: _dashboardViewModel,
        analysisJobsViewModel: _shellRuntime.jobFeeds.analysisFeed,
        shellProjection: _shellRuntime.projection,
        launchIntent: _pendingDataAnalysisIntent,
        onLaunchIntentHandled: _clearDataAnalysisIntent,
        isActive: isActive,
        sharedRuntimeManaged: true,
        surfaceMode: WorkbenchSurfaceMode.embedded,
      ),
      3 => AiLabScreen(
        dashboardViewModel: _dashboardViewModel,
        trainingJobsViewModel: _shellRuntime.jobFeeds.mlTrainFeed,
        ragJobsViewModel: _shellRuntime.jobFeeds.ragIngestFeed,
        shellProjection: _shellRuntime.projection,
        launchIntent: _pendingAiLabIntent,
        onLaunchIntentHandled: _clearAiLabIntent,
        isActive: isActive,
        sharedRuntimeManaged: true,
        surfaceMode: WorkbenchSurfaceMode.embedded,
      ),
      4 => HistoryAuditScreen(
        dashboardViewModel: _dashboardViewModel,
        jobsViewModel: _shellRuntime.jobFeeds.historyAuditFeed,
        shellProjection: _shellRuntime.projection,
        onOpenAiLab: _openAiLabWithIntent,
        onOpenDataAnalysis: _openDataAnalysisWithIntent,
        onOpenOptimization: _openOptimizationWithIntent,
        isActive: isActive,
        sharedRuntimeManaged: true,
        surfaceMode: WorkbenchSurfaceMode.embedded,
      ),
      _ => const SizedBox.shrink(),
    };
  }

  Widget _buildRuntimePanel() {
    return ShellRuntimePanel(
      projection: _shellRuntime.projection,
      panelKind: _shellRuntime.panelKind,
      approvalQueueViewModel: _approvalQueueViewModel,
      operationConsoleViewModel: _operationConsoleViewModel,
      onSelectPanel: (kind) => unawaited(_shellRuntime.showPanel(kind)),
      onClose: _shellRuntime.closePanel,
      onApproveQueued: (job) => _resolveQueuedApproval(job, approved: true),
      onRejectQueued: (job) => _resolveQueuedApproval(job, approved: false),
      onOpenOperation: (job) =>
          unawaited(_shellRuntime.openOperation(job.operationId ?? job.jobId)),
      onOpenOperationId: (operationId) =>
          unawaited(_shellRuntime.openOperation(operationId)),
      onApproveSelected: () =>
          _resolveSelectedOperationApproval(approved: true),
      onRejectSelected: () =>
          _resolveSelectedOperationApproval(approved: false),
      onRetrySelected: _retrySelectedOperation,
      onCancelSelected: _cancelSelectedOperation,
      onMarkNotificationRead: _shellRuntime.markNotificationRead,
      onMarkAllNotificationsRead: _shellRuntime.markAllNotificationsRead,
      onDismissNotification: _shellRuntime.dismissNotification,
    );
  }

  void _openApprovalPanel() {
    if (!_usesDefaultShell) {
      return;
    }
    _openShellPanel(ShellRuntimePanelKind.approvals);
  }

  void _openOperationPanel() {
    if (!_usesDefaultShell) {
      return;
    }
    _openShellPanel(ShellRuntimePanelKind.operations);
  }

  void _openNotificationsPanel() {
    if (!_usesDefaultShell) {
      return;
    }
    _openShellPanel(ShellRuntimePanelKind.notifications);
  }

  void _openShellPanel(ShellRuntimePanelKind kind) {
    if (ResponsiveHelper.isDesktop(context)) {
      unawaited(_shellRuntime.showPanel(kind));
      return;
    }
    unawaited(_showMobileShellPanel(kind));
  }

  Future<void> _showMobileShellPanel(ShellRuntimePanelKind kind) async {
    await _shellRuntime.showPanel(kind);
    if (!mounted) {
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return FractionallySizedBox(
          heightFactor: 0.92,
          child: DecoratedBox(
            decoration: const BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
            ),
            child: ListenableBuilder(
              listenable: _shellRuntime,
              builder: (context, _) => _buildRuntimePanel(),
            ),
          ),
        );
      },
    );
    _shellRuntime.closePanel();
  }

  Future<void> _resolveQueuedApproval(
    JobRecord job, {
    required bool approved,
  }) async {
    final message = await _showApprovalDialog(
      approved: approved,
      title: job.displayTitle,
    );
    if (!mounted || message == null) {
      return;
    }
    final outcome = await _shellRuntime.resolveQueuedApprovalAction(
      job,
      approved: approved,
      message: message.isEmpty ? null : message,
    );
    if (!mounted) {
      return;
    }
    _showShellActionOutcome(outcome);
  }

  Future<void> _resolveSelectedOperationApproval({
    required bool approved,
  }) async {
    final operation = _operationConsoleViewModel.selectedOperation;
    if (operation == null) {
      return;
    }
    final message = await _showApprovalDialog(
      approved: approved,
      title: operation.displayTitle,
    );
    if (!mounted || message == null) {
      return;
    }
    final outcome = await _shellRuntime.resolveSelectedOperationApprovalAction(
      approved: approved,
      message: message.isEmpty ? null : message,
    );
    if (!mounted) {
      return;
    }
    _showShellActionOutcome(outcome);
  }

  Future<void> _retrySelectedOperation() async {
    final outcome = await _shellRuntime.retrySelectedOperationAction();
    if (!mounted) {
      return;
    }
    _showShellActionOutcome(outcome);
  }

  Future<void> _cancelSelectedOperation() async {
    final outcome = await _shellRuntime.cancelSelectedOperationAction();
    if (!mounted) {
      return;
    }
    _showShellActionOutcome(outcome);
  }

  Future<String?> _showApprovalDialog({
    required bool approved,
    required String title,
  }) async {
    return showApprovalResolutionDialog(
      context,
      approved: approved,
      title: title,
    );
  }

  void _showShellSnackBar(String message, {required Color backgroundColor}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: backgroundColor),
    );
  }

  void _showShellActionOutcome(ShellActionOutcome outcome) {
    _showShellSnackBar(
      outcome.message,
      backgroundColor: _colorForActionTone(outcome.tone),
    );
  }

  Color _colorForActionTone(ShellActionTone tone) {
    return switch (tone) {
      ShellActionTone.success => AppColors.success,
      ShellActionTone.warning => AppColors.warning,
      ShellActionTone.error => AppColors.error,
      ShellActionTone.info => AppColors.primary,
    };
  }

  void _openAiLabWithIntent(AiLabLaunchIntent intent) {
    setState(() {
      _pendingAiLabIntent = intent;
    });
    _setCurrentIndex(3);
  }

  void _openDataAnalysisWithIntent(DataAnalysisLaunchIntent intent) {
    setState(() {
      _pendingDataAnalysisIntent = intent;
    });
    _setCurrentIndex(2);
  }

  void _openOptimizationWithIntent(OptimizationLaunchIntent intent) {
    setState(() {
      _pendingOptimizationIntent = intent;
    });
    _setCurrentIndex(1);
  }

  void _clearAiLabIntent() {
    if (_pendingAiLabIntent == null || !mounted) {
      return;
    }
    setState(() {
      _pendingAiLabIntent = null;
    });
  }

  void _clearDataAnalysisIntent() {
    if (_pendingDataAnalysisIntent == null || !mounted) {
      return;
    }
    setState(() {
      _pendingDataAnalysisIntent = null;
    });
  }

  void _clearOptimizationIntent() {
    if (_pendingOptimizationIntent == null || !mounted) {
      return;
    }
    setState(() {
      _pendingOptimizationIntent = null;
    });
  }
}

class _NavDestination {
  const _NavDestination({required this.label, required this.icon});

  final String label;
  final IconData icon;
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 56,
          child: Text(label, style: AppTextStyles.labelMedium),
        ),
        const SizedBox(width: 8),
        Expanded(child: SelectableText(value, style: AppTextStyles.bodyMedium)),
      ],
    );
  }
}
