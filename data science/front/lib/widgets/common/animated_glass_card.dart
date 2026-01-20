import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import '../../config/app_theme.dart';
// Note: Removed unused import constants.dart
// Note: Removed unused import

/// 高级动态玻璃卡片
/// 支持鼠标悬停光泽效果、淡入动画和点击反馈
/// 【性能优化】Web 端禁用动画以提升性能
class AnimatedGlassCard extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final LinearGradient? gradientBorder;
  final EdgeInsets padding;
  final EdgeInsetsGeometry? margin;
  final double borderRadius;
  final bool enableHover;

  const AnimatedGlassCard({
    super.key,
    required this.child,
    this.onTap,
    this.gradientBorder,
    this.padding = const EdgeInsets.all(20),
    this.margin,
    this.borderRadius = AppDecorations.radiusLg,
    this.enableHover = true,
  });

  @override
  State<AnimatedGlassCard> createState() => _AnimatedGlassCardState();
}

class _AnimatedGlassCardState extends State<AnimatedGlassCard>
    with SingleTickerProviderStateMixin {
  bool _isHovered = false;
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 200),
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 1.02).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onHover(bool isHovered) {
    if (!widget.enableHover) return;
    setState(() {
      _isHovered = isHovered;
    });
    // 【性能优化】Web 端禁用动画
    if (!kIsWeb) {
      if (isHovered) {
        _controller.forward();
      } else {
        _controller.reverse();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // 【性能优化】使用 RepaintBoundary 隔离动画区域
    return RepaintBoundary(
      child: MouseRegion(
        onEnter: (_) => _onHover(true),
        onExit: (_) => _onHover(false),
        cursor: widget.onTap != null ? SystemMouseCursors.click : SystemMouseCursors.basic,
        child: GestureDetector(
          onTap: widget.onTap,
          child: _buildCard(),
        ),
      ),
    );
  }

  Widget _buildCard() {
    final cardContent = Container(
      margin: widget.margin,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(widget.borderRadius),
        boxShadow: _isHovered
            ? AppDecorations.shadowLg
            : AppDecorations.shadowMd,
      ),
      child: GlassContainer(
        borderRadius: BorderRadius.circular(widget.borderRadius),
        padding: widget.padding,
        border: Border.all(
          color: _isHovered 
              ? (widget.gradientBorder?.colors.first ?? Colors.white).withValues(alpha: 0.5)
              : AppColors.glassBorder,
          width: 1.5,
        ),
        child: widget.child,
      ),
    );

    // 【性能优化】Web 端禁用 Transform.scale 动画
    if (kIsWeb) {
      return cardContent;
    }

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Transform.scale(
          scale: _scaleAnimation.value,
          child: cardContent,
        );
      },
    );
  }
}
