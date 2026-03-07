/// 登录页背景装饰组件
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';

class LoginBackground extends StatelessWidget {
  const LoginBackground({
    super.key,
    required this.child,
  });

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: double.infinity,
      decoration: const BoxDecoration(
        gradient: AppColors.backgroundGradient,
      ),
      child: Stack(
        children: [
          Positioned(
            top: -100,
            right: -100,
            child: _buildOrb(300, AppColors.primary.withValues(alpha: 0.1)),
          ),
          Positioned(
            bottom: -50,
            left: -50,
            child: _buildOrb(200, AppColors.cta.withValues(alpha: 0.1)),
          ),
          child,
        ],
      ),
    );
  }

  Widget _buildOrb(double size, Color color) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color,
        ),
      ),
    );
  }
}
