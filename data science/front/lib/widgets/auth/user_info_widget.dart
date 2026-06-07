/// 用户信息组件 - 从 DataAnalysisScreen 提取
/// 【性能优化】独立组件减少不必要的重建
library;

import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../../config/app_theme.dart';
import '../common/glass_card.dart';

/// 用户信息展示组件（已登录状态）
class UserInfoWidget extends StatelessWidget {
  final User user;

  const UserInfoWidget({super.key, required this.user});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          // 头像
          _buildAvatar(),
          const SizedBox(width: 12),
          // 用户信息
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  user.displayName ?? user.email ?? '用户',
                  style: AppTextStyles.labelLarge,
                ),
                Text(user.email ?? '', style: AppTextStyles.bodySmall),
              ],
            ),
          ),
          // 验证徽章
          _buildVerifiedBadge(),
        ],
      ),
    );
  }

  Widget _buildAvatar() {
    return Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        gradient: AppColors.primaryGradient,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: user.photoURL != null
          ? ClipRRect(
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              child: Image.network(user.photoURL!, fit: BoxFit.cover),
            )
          : const Icon(Icons.person_rounded, color: Colors.white),
    );
  }

  Widget _buildVerifiedBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.successLight,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.check_circle, size: 14, color: AppColors.success),
          const SizedBox(width: 4),
          Text(
            '已登录',
            style: AppTextStyles.labelMedium.copyWith(color: AppColors.success),
          ),
        ],
      ),
    );
  }
}
