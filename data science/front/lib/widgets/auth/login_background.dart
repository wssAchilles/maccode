/// 登录页背景装饰组件
library;

import 'dart:ui';

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';

class LoginBackground extends StatelessWidget {
  const LoginBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: double.infinity,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFFEAF3FF), Color(0xFFF6FAFF)],
        ),
      ),
      child: Stack(
        children: [
          Positioned(
            top: -120,
            left: -110,
            child: _buildBlurOrb(
              size: 460,
              color: const Color(0xFF4A92FD).withValues(alpha: 0.12),
            ),
          ),
          Positioned(
            right: -72,
            top: 210,
            child: _buildBlurOrb(
              size: 360,
              color: const Color(0xFFFF7A1A).withValues(alpha: 0.12),
            ),
          ),
          Positioned(
            right: -40,
            top: 64,
            child: _buildSoftDisc(
              size: 200,
              color: const Color(0xFFD7E6FF).withValues(alpha: 0.55),
            ),
          ),
          Positioned(
            left: -30,
            bottom: -44,
            child: _buildSoftDisc(
              size: 140,
              color: const Color(0xFFFFE3CC).withValues(alpha: 0.65),
            ),
          ),
          child,
        ],
      ),
    );
  }

  Widget _buildBlurOrb({required double size, required Color color}) {
    return IgnorePointer(
      child: ImageFiltered(
        imageFilter: ImageFilter.blur(sigmaX: 60, sigmaY: 60),
        child: Container(
          width: size,
          height: size * 0.8,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
          ),
        ),
      ),
    );
  }

  Widget _buildSoftDisc({required double size, required Color color}) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(shape: BoxShape.circle, color: color),
      ),
    );
  }
}
