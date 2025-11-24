/// 主导航页 - 登录后的总仪表盘
/// 使用底部导航栏整合三个主要功能模块
library;

import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
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

  /// 退出登录
  Future<void> _handleSignOut() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认退出'),
        content: const Text('确定要退出登录吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(
              foregroundColor: Colors.red,
            ),
            child: const Text('退出'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      try {
        await _authService.signOut();
        // AuthWrapper 会自动监听到状态变化并跳转到登录页
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('已退出登录'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('退出失败: $e'),
              backgroundColor: Colors.red,
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
        title: const Row(
          children: [
            Icon(Icons.account_circle, color: Colors.blue),
            SizedBox(width: 8),
            Text('用户信息'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildInfoRow('邮箱', user.email ?? '未设置'),
            const SizedBox(height: 8),
            _buildInfoRow('用户ID', user.uid),
            const SizedBox(height: 8),
            _buildInfoRow(
              '邮箱验证',
              user.emailVerified ? '已验证' : '未验证',
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

  Widget _buildInfoRow(String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 80,
          child: Text(
            label,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              color: Colors.grey,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontSize: 14),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          _titles[_currentIndex],
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        elevation: 2,
        backgroundColor: _getAppBarColor(),
        actions: [
          // 用户信息按钮
          IconButton(
            icon: const Icon(Icons.account_circle),
            onPressed: _showUserInfo,
            tooltip: '用户信息',
          ),
          // 退出登录按钮
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: _handleSignOut,
            tooltip: '退出登录',
          ),
        ],
      ),
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        type: BottomNavigationBarType.fixed,
        selectedItemColor: _getSelectedColor(),
        unselectedItemColor: Colors.grey,
        selectedFontSize: 14,
        unselectedFontSize: 12,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.auto_graph),
            activeIcon: Icon(Icons.auto_graph, size: 28),
            label: '智能调度',
            tooltip: '能源优化调度',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.analytics),
            activeIcon: Icon(Icons.analytics, size: 28),
            label: '数据分析',
            tooltip: 'CSV数据分析',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.history),
            activeIcon: Icon(Icons.history, size: 28),
            label: '历史记录',
            tooltip: '查看历史记录',
          ),
        ],
      ),
    );
  }

  /// 根据当前 Tab 返回不同的 AppBar 颜色
  Color _getAppBarColor() {
    switch (_currentIndex) {
      case 0:
        return Colors.blue[700]!; // 智能调度 - 蓝色
      case 1:
        return Colors.green[700]!; // 数据分析 - 绿色
      case 2:
        return Colors.orange[700]!; // 历史记录 - 橙色
      default:
        return Colors.blue[700]!;
    }
  }

  /// 根据当前 Tab 返回选中颜色
  Color _getSelectedColor() {
    switch (_currentIndex) {
      case 0:
        return Colors.blue[700]!;
      case 1:
        return Colors.green[700]!;
      case 2:
        return Colors.orange[700]!;
      default:
        return Colors.blue[700]!;
    }
  }
}
