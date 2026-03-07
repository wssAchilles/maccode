/// 深度学习页面头部信息组件
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../utils/responsive_helper.dart';
import '../common/animated_glass_card.dart';

class DeepLearningHeader extends StatelessWidget {
  const DeepLearningHeader({super.key});

  @override
  Widget build(BuildContext context) {
    return AnimatedGlassCard(
      enableHover: false,
      gradientBorder: AppColors.deepLearningGradient,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final stacked =
              constraints.maxWidth < ResponsiveHelper.mobileBreakpoint + 80;

          return Flex(
            direction: stacked ? Axis.vertical : Axis.horizontal,
            crossAxisAlignment: stacked
                ? CrossAxisAlignment.start
                : CrossAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF8B5CF6).withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
                ),
                child: const Icon(
                  Icons.psychology_rounded,
                  size: 32,
                  color: Color(0xFF8B5CF6),
                ),
              ),
              SizedBox(width: stacked ? 0 : 16, height: stacked ? 12 : 0),
              if (stacked)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Time Series Forecasting', style: AppTextStyles.h3),
                    Text(
                      'Powered by TensorFlow on Cloud Run (Heavy Core)',
                      style: AppTextStyles.bodySmall,
                    ),
                    const SizedBox(height: 12),
                    _buildStatusBadge(),
                  ],
                )
              else ...[
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Time Series Forecasting', style: AppTextStyles.h3),
                      Text(
                        'Powered by TensorFlow on Cloud Run (Heavy Core)',
                        style: AppTextStyles.bodySmall,
                      ),
                    ],
                  ),
                ),
                _buildStatusBadge(),
              ],
            ],
          );
        },
      ),
    );
  }

  Widget _buildStatusBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.successLight,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
        border: Border.all(color: AppColors.success),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.cloud_done_rounded,
            size: 16,
            color: AppColors.success,
          ),
          const SizedBox(width: 8),
          Text(
            'Cloud Run Active',
            style: AppTextStyles.labelMedium.copyWith(
              color: AppColors.success,
            ),
          ),
        ],
      ),
    );
  }
}
