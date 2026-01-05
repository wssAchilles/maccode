/// 玻璃效果卡片组件
/// 支持 Glassmorphism 效果的可复用卡片
library;

import 'dart:ui';
import 'package:flutter/material.dart';
import '../../config/app_theme.dart';

/// 玻璃卡片组件 - 用于整个应用的统一卡片样式
class GlassCard extends StatefulWidget {
  const GlassCard({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.borderRadius,
    this.blur = 10.0,
    this.opacity = 0.85,
    this.gradient,
    this.onTap,
    this.enableHover = true,
  });

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final BorderRadius? borderRadius;
  final double blur;
  final double opacity;
  final LinearGradient? gradient;
  final VoidCallback? onTap;
  final bool enableHover;

  @override
  State<GlassCard> createState() => _GlassCardState();
}

class _GlassCardState extends State<GlassCard> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final radius = widget.borderRadius ?? 
        BorderRadius.circular(AppDecorations.radiusLg);
    
    return MouseRegion(
      onEnter: widget.enableHover ? (_) => setState(() => _isHovered = true) : null,
      onExit: widget.enableHover ? (_) => setState(() => _isHovered = false) : null,
      child: AnimatedContainer(
        duration: AppDecorations.animationFast,
        curve: AppDecorations.animationCurve,
        margin: widget.margin,
        transform: Matrix4.identity()
          ..scale(_isHovered && widget.enableHover ? 1.01 : 1.0),
        child: GestureDetector(
          onTap: widget.onTap,
          child: ClipRRect(
            borderRadius: radius,
            child: BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: widget.blur,
                sigmaY: widget.blur,
              ),
              child: AnimatedContainer(
                duration: AppDecorations.animationFast,
                padding: widget.padding ?? const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  gradient: widget.gradient,
                  color: widget.gradient == null 
                      ? Colors.white.withValues(alpha: widget.opacity)
                      : null,
                  borderRadius: radius,
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.2),
                    width: 1,
                  ),
                  boxShadow: _isHovered 
                      ? AppDecorations.shadowLg 
                      : AppDecorations.shadowMd,
                ),
                child: widget.child,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// 统计数值卡片 - 用于展示关键指标
class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.value,
    required this.label,
    this.icon,
    this.trend,
    this.trendValue,
    this.gradient,
    this.onTap,
  });

  final String value;
  final String label;
  final IconData? icon;
  final TrendDirection? trend;
  final String? trendValue;
  final LinearGradient? gradient;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      gradient: gradient,
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // 图标和趋势
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              if (icon != null)
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: gradient != null 
                        ? Colors.white.withValues(alpha: 0.2)
                        : AppColors.primary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                  ),
                  child: Icon(
                    icon,
                    size: 20,
                    color: gradient != null ? Colors.white : AppColors.primary,
                  ),
                ),
              if (trend != null && trendValue != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getTrendColor().withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        _getTrendIcon(),
                        size: 12,
                        color: _getTrendColor(),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        trendValue!,
                        style: AppTextStyles.labelMedium.copyWith(
                          color: _getTrendColor(),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          // 数值
          Text(
            value,
            style: AppTextStyles.h2.copyWith(
              color: gradient != null ? Colors.white : AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          // 标签
          Text(
            label,
            style: AppTextStyles.bodySmall.copyWith(
              color: gradient != null 
                  ? Colors.white.withValues(alpha: 0.8)
                  : AppColors.textMuted,
            ),
          ),
        ],
      ),
    );
  }

  Color _getTrendColor() {
    switch (trend) {
      case TrendDirection.up:
        return AppColors.success;
      case TrendDirection.down:
        return AppColors.error;
      case TrendDirection.neutral:
      case null:
        return AppColors.textMuted;
    }
  }

  IconData _getTrendIcon() {
    switch (trend) {
      case TrendDirection.up:
        return Icons.trending_up_rounded;
      case TrendDirection.down:
        return Icons.trending_down_rounded;
      case TrendDirection.neutral:
      case null:
        return Icons.trending_flat_rounded;
    }
  }
}

/// 趋势方向枚举
enum TrendDirection { up, down, neutral }

/// 虚线边框绘制器 - 用于拖放区域
class DashedBorderPainter extends CustomPainter {
  final Color color;
  final double strokeWidth;
  final double dashWidth;
  final double dashSpace;
  final double borderRadius;

  DashedBorderPainter({
    this.color = const Color(0xFFE2E8F0),
    this.strokeWidth = 2.0,
    this.dashWidth = 6.0,
    this.dashSpace = 4.0,
    this.borderRadius = 12.0,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke;

    final rrect = RRect.fromRectAndRadius(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Radius.circular(borderRadius),
    );

    final path = Path()..addRRect(rrect);
    final dashPath = _createDashedPath(path);
    canvas.drawPath(dashPath, paint);
  }

  Path _createDashedPath(Path source) {
    final dashPath = Path();
    for (final metric in source.computeMetrics()) {
      double distance = 0.0;
      while (distance < metric.length) {
        final len = dashWidth;
        dashPath.addPath(
          metric.extractPath(distance, distance + len),
          Offset.zero,
        );
        distance += dashWidth + dashSpace;
      }
    }
    return dashPath;
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/// 拖放区域容器
class DropZoneContainer extends StatefulWidget {
  const DropZoneContainer({
    super.key,
    required this.child,
    this.onTap,
    this.isActive = false,
  });

  final Widget child;
  final VoidCallback? onTap;
  final bool isActive;

  @override
  State<DropZoneContainer> createState() => _DropZoneContainerState();
}

class _DropZoneContainerState extends State<DropZoneContainer> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final isHighlighted = _isHovered || widget.isActive;
    
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: AppDecorations.animationFast,
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: isHighlighted 
                ? AppColors.primary.withValues(alpha: 0.05)
                : AppColors.surfaceVariant,
            borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
          ),
          child: CustomPaint(
            painter: DashedBorderPainter(
              color: isHighlighted ? AppColors.primary : AppColors.border,
              borderRadius: AppDecorations.radiusLg,
            ),
            child: widget.child,
          ),
        ),
      ),
    );
  }
}
