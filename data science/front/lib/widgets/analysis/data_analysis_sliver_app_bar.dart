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
      expandedHeight: 120,
      floating: false,
      pinned: true,
      backgroundColor: AppColors.primary,
      foregroundColor: Colors.white,
      flexibleSpace: FlexibleSpaceBar(
        title: Text(
          '数据科学即服务',
          style: AppTextStyles.h4.copyWith(color: Colors.white),
        ),
        background: Container(
          decoration: const BoxDecoration(gradient: AppColors.primaryGradient),
        ),
      ),
      actions: [
        if (isLoggedIn) ...[
          IconButton(
            icon: const Icon(Icons.history_rounded),
            onPressed: onOpenHistory,
            tooltip: '分析历史',
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
