/// 深度学习兼容入口
/// 主产品路径已经统一到 AI Lab 工作台，这里只保留旧路由兼容。
library;

import 'package:flutter/material.dart';

import '../models/ai_lab_launch_intent.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../viewmodels/deep_learning_view_model.dart';
import 'ai_lab_screen.dart';

class DeepLearningScreen extends StatefulWidget {
  const DeepLearningScreen({
    super.key,
    this.storagePath,
    this.viewModel,
  });

  final String? storagePath;

  /// 保留参数仅用于旧调用点兼容。训练主路径已经迁移到 AI Lab。
  final DeepLearningViewModel? viewModel;

  @override
  State<DeepLearningScreen> createState() => _DeepLearningScreenState();
}

class _DeepLearningScreenState extends State<DeepLearningScreen> {
  late final DashboardViewModel _dashboardViewModel;

  @override
  void initState() {
    super.initState();
    _dashboardViewModel = DashboardViewModel();
  }

  @override
  void dispose() {
    _dashboardViewModel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AiLabScreen(
      dashboardViewModel: _dashboardViewModel,
      launchIntent: AiLabLaunchIntent.deepLearning(
        widget.storagePath ?? 'demo_data.csv',
        targetColumn: 'Load',
        sourceLabel: 'Legacy Deep Learning Route',
      ),
    );
  }
}
