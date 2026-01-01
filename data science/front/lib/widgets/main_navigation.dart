/// 主导航页 - Glassmorphism 设计
/// 使用底部导航栏整合三个主要功能模块
library;

import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../config/app_theme.dart';
import '../screens/modeling_screen.dart';
import '../screens/data_analysis_screen.dart';
import '../screens/history_screen.dart';
import '../services/auth_service.dart';

class MainNavigation extends StatefulWidget {
  const MainNavigation({super.key});

  @override
  State<MainNavigation> createState() => _MainNavigationState();
}

class _MainNavigationState extends State<MainNavigation> {
  int _currentIndex = 0;
  final _authService = AuthService();

  // 页面列表 - 使用 IndexedStack 保持状态
  final List<Widget> _pages = const [
    ModelingScreen(),      // 智能调度
    DataAnalysisScreen(),  // 数据分析
    HistoryScreen(),       // 历史记录
  ];

  // 页面标题
  final List<String> _titles = const [
    '能源优化',
    '数据分析',
    '历史记录',
  ];
  
  // 页面图标
  final List<IconData> _icons = const [
    Icons.bolt_rounded,
    Icons.analytics_rounded,
    Icons.history_rounded,
  ];

  /// 退出登录
  Future<void> _handleSignOut() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        ),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppColors.warningLight,
                borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              ),
              child: const Icon(Icons.logout_rounded, color: AppColors.warning),
            ),
            const SizedBox(width: 12),
            const Text('确认退出'),
          ],
        ),
        content: const Text('确定要退出登录吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.error,
            ),
            child: const Text('退出'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      try {
        await _authService.signOut();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: const Row(
                children: [
                  Icon(Icons.check_circle, color: Colors.white),
                  SizedBox(width: 8),
                  Text('已退出登录'),
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
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('退出失败: $e'),
              backgroundColor: AppColors.error,
              behavior: SnackBarBehavior.floating,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              ),
            ),
          );
        }
      }
    }
  }

  /// 显示用户信息
  void _showUserInfo() {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        ),
        title: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                gradient: AppColors.primaryGradient,
                borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              ),
              child: const Icon(Icons.person_rounded, color: Colors.white, size: 28),
            ),
            const SizedBox(width: 12),
            const Text('用户信息'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildInfoRow(Icons.email_outlined, '邮箱', user.email ?? '未设置'),
            const SizedBox(height: 12),
            _buildInfoRow(Icons.fingerprint, 'UID', user.uid.substring(0, 8) + '...'),
            const SizedBox(height: 12),
            _buildInfoRow(
              user.emailVerified ? Icons.verified_rounded : Icons.warning_rounded,
              '状态',
              user.emailVerified ? '已验证' : '未验证',
              statusColor: user.emailVerified ? AppColors.success : AppColors.warning,
            ),
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

  Widget _buildInfoRow(IconData icon, String label, String value, {Color? statusColor}) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20, color: statusColor ?? AppColors.textMuted),
          const SizedBox(width: 12),
          SizedBox(
            width: 48,
            child: Text(
              label,
              style: AppTextStyles.labelMedium.copyWith(color: AppColors.textMuted),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: AppTextStyles.bodyMedium.copyWith(
                color: statusColor ?? AppColors.textPrimary,
                fontWeight: statusColor != null ? FontWeight.w600 : FontWeight.normal,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: _buildAppBar(),
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
      bottomNavigationBar: _buildBottomNavBar(),
    );
  }
  
  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      title: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.2),
              borderRadius: BorderRadius.circular(AppDecorations.radiusSm),
            ),
            child: Icon(_icons[_currentIndex], size: 18, color: Colors.white),
          ),
          const SizedBox(width: 12),
          Text(
            _titles[_currentIndex],
            style: AppTextStyles.h4.copyWith(color: Colors.white),
          ),
        ],
      ),
      elevation: 0,
      backgroundColor: AppColors.primary,
      actions: [
        // 用户信息按钮
        IconButton(
          icon: const Icon(Icons.account_circle_outlined),
          onPressed: _showUserInfo,
          tooltip: '用户信息',
        ),
        // 退出登录按钮
        IconButton(
          icon: const Icon(Icons.logout_rounded),
          onPressed: _handleSignOut,
          tooltip: '退出登录',
        ),
        const SizedBox(width: 8),
      ],
    );
  }
  
  Widget _buildBottomNavBar() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.08),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: List.generate(3, (index) => _buildNavItem(index)),
          ),
        ),
      ),
    );
  }
  
  Widget _buildNavItem(int index) {
    final isSelected = _currentIndex == index;
    final color = isSelected ? AppColors.primary : AppColors.textMuted;
    
    return GestureDetector(
      onTap: () {
        setState(() {
          _currentIndex = index;
        });
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
        padding: EdgeInsets.symmetric(
          horizontal: isSelected ? 20 : 16,
          vertical: 8,
        ),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.primary.withOpacity(0.1) : Colors.transparent,
          borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(_icons[index], color: color, size: 22),
            if (isSelected) ...[
              const SizedBox(width: 8),
              Text(
                _titles[index],
                style: AppTextStyles.labelMedium.copyWith(
                  color: AppColors.primary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
