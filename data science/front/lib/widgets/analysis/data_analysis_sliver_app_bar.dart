/// 数据分析页顶部 SliverAppBar 组件
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';

class DataAnalysisSliverAppBar extends StatelessWidget {
  const DataAnalysisSliverAppBar({
    super.key,
    required this.isLoggedIn,
    required this.onOpenHistory,
    required this.onSignOut,
  });

  final bool isLoggedIn;
  final VoidCallback onOpenHistory;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) {
    return SliverAppBar(
      expandedHeight: 136,
      floating: false,
      pinned: true,
      backgroundColor: AppColors.surface,
      foregroundColor: AppColors.textPrimary,
      flexibleSpace: FlexibleSpaceBar(
        title: Text('Data Analysis Workbench', style: AppTextStyles.h4),
        background: Container(
          decoration: const BoxDecoration(
            gradient: AppColors.backgroundGradient,
          ),
        ),
      ),
      actions: [
        if (isLoggedIn) ...[
          IconButton(
            icon: const Icon(Icons.history_rounded),
            onPressed: onOpenHistory,
            tooltip: '历史与审计',
          ),
          IconButton(
            icon: const Icon(Icons.logout_rounded),
            onPressed: onSignOut,
            tooltip: '登出',
          ),
          const SizedBox(width: 8),
        ],
      ],
    );
  }
}
