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
import '../repositories/auth_repository.dart';
import '../screens/ai_lab_screen.dart';
import '../screens/data_analysis_screen.dart';
import '../screens/history_audit_screen.dart';
import '../screens/modeling_screen.dart';
import '../screens/operations_hub_screen.dart';
import '../services/auth_gateway.dart';
import '../utils/asset_chain_context.dart';
import '../utils/responsive_helper.dart';
import '../viewmodels/dashboard_view_model.dart';
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
  }) : _authRepository = authRepository,
       _authGateway = authGateway,
       _dashboardViewModel = dashboardViewModel,
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
  }) : _authRepository = authRepository,
       _authGateway = authGateway,
       _dashboardViewModel = dashboardViewModel,
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
  late final DashboardViewModel _dashboardViewModel;
  late final bool _ownsDashboardViewModel;
  StreamSubscription<User?>? _authSubscription;
  User? _currentUser;
  AiLabLaunchIntent? _pendingAiLabIntent;
  DataAnalysisLaunchIntent? _pendingDataAnalysisIntent;
  OptimizationLaunchIntent? _pendingOptimizationIntent;

  bool get _hasAuthenticatedUser => _currentUser != null;

  @override
  void initState() {
    super.initState();
    _authRepository =
        widget._authRepository ??
        GatewayAuthRepository(authGateway: widget._authGateway);
    _dashboardViewModel = widget._dashboardViewModel ?? DashboardViewModel();
    _ownsDashboardViewModel = widget._dashboardViewModel == null;
    _currentUser = _authRepository.currentUser;
    _authSubscription = _authRepository.authStateChanges.listen((user) {
      if (!mounted || user == _currentUser) {
        return;
      }
      setState(() {
        _currentUser = user;
      });
    });
    _dashboardViewModel.initialize();
  }

  @override
  void dispose() {
    _authSubscription?.cancel();
    if (_ownsDashboardViewModel) {
      _dashboardViewModel.dispose();
    }
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
    final desktopShell = ResponsiveHelper.isDesktop(context);
    final statusItems =
        _dashboardViewModel.summary?.systemStatus ?? const <dynamic>[];

    if (desktopShell) {
      return Scaffold(
        backgroundColor: AppColors.background,
        body: Column(
          children: [
            SystemStatusStrip(
              items: statusItems.cast(),
              compact: true,
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
                            padding: const EdgeInsets.symmetric(vertical: 6),
                          ),
                        )
                        .toList(growable: false),
                  ),
                  const VerticalDivider(width: 1),
                  Expanded(
                    child: SafeArea(
                      top: false,
                      bottom: false,
                      child: IndexedStack(
                        index: _currentIndex,
                        children: _pages,
                      ),
                    ),
                  ),
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
        child: IndexedStack(index: _currentIndex, children: _pages),
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
                child: Row(children: [Expanded(child: _buildAccountActions())]),
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
  }

  Widget _buildAccountActions({bool compact = false}) {
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

  void _onNavTap(int index) {
    if (_currentIndex == index) {
      return;
    }
    if (index == 3 && _pendingAiLabIntent == null) {
      final defaultAiIntent = _defaultAiLabIntent();
      if (defaultAiIntent != null) {
        setState(() {
          _pendingAiLabIntent = defaultAiIntent;
          _currentIndex = index;
        });
        return;
      }
    }
    setState(() {
      _currentIndex = index;
    });
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

  List<Widget> get _pages =>
      widget._customPages ??
      [
        // Default product pages always render as shell content.
        OperationsHubScreen(
          viewModel: _dashboardViewModel,
          onNavigateToTab: _onNavTap,
          onOpenAiLab: _openAiLabWithIntent,
          onOpenDataAnalysis: _openDataAnalysisWithIntent,
          onOpenOptimization: _openOptimizationWithIntent,
          surfaceMode: WorkbenchSurfaceMode.embedded,
        ),
        ModelingScreen(
          dashboardViewModel: _dashboardViewModel,
          launchIntent: _pendingOptimizationIntent,
          onLaunchIntentHandled: _clearOptimizationIntent,
          surfaceMode: WorkbenchSurfaceMode.embedded,
        ),
        DataAnalysisScreen(
          onOpenHistory: () => _onNavTap(4),
          onSendToAiLab: _openAiLabWithIntent,
          dashboardViewModel: _dashboardViewModel,
          launchIntent: _pendingDataAnalysisIntent,
          onLaunchIntentHandled: _clearDataAnalysisIntent,
          surfaceMode: WorkbenchSurfaceMode.embedded,
        ),
        AiLabScreen(
          dashboardViewModel: _dashboardViewModel,
          launchIntent: _pendingAiLabIntent,
          onLaunchIntentHandled: _clearAiLabIntent,
          isActive: _currentIndex == 3,
          surfaceMode: WorkbenchSurfaceMode.embedded,
        ),
        HistoryAuditScreen(
          dashboardViewModel: _dashboardViewModel,
          onOpenAiLab: _openAiLabWithIntent,
          onOpenDataAnalysis: _openDataAnalysisWithIntent,
          onOpenOptimization: _openOptimizationWithIntent,
          surfaceMode: WorkbenchSurfaceMode.embedded,
        ),
      ];

  void _openAiLabWithIntent(AiLabLaunchIntent intent) {
    setState(() {
      _pendingAiLabIntent = intent;
      _currentIndex = 3;
    });
  }

  void _openDataAnalysisWithIntent(DataAnalysisLaunchIntent intent) {
    setState(() {
      _pendingDataAnalysisIntent = intent;
      _currentIndex = 2;
    });
  }

  void _openOptimizationWithIntent(OptimizationLaunchIntent intent) {
    setState(() {
      _pendingOptimizationIntent = intent;
      _currentIndex = 1;
    });
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
