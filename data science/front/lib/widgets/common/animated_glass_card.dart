import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import '../../config/app_theme.dart';

/// 高级动态玻璃卡片
/// 支持鼠标悬停光泽效果、淡入动画和点击反馈。
/// Web 端保留样式反馈，但禁用缩放动画以降低 GPU 压力。
class AnimatedGlassCard extends StatefulWidget {
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

  final Widget child;
  final VoidCallback? onTap;
  final LinearGradient? gradientBorder;
  final EdgeInsets padding;
  final EdgeInsetsGeometry? margin;
  final double borderRadius;
  final bool enableHover;

  @override
  State<AnimatedGlassCard> createState() => _AnimatedGlassCardState();
}

class _AnimatedGlassCardState extends State<AnimatedGlassCard>
    with SingleTickerProviderStateMixin {
  bool _isHovered = false;
  late final AnimationController _controller;
  late final Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 200),
    );
    _scaleAnimation = Tween<double>(
      begin: 1.0,
      end: 1.02,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _setHoverState(bool isHovered) {
    if (!widget.enableHover || _isHovered == isHovered) {
      return;
    }

    setState(() => _isHovered = isHovered);

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
    return RepaintBoundary(
      child: MouseRegion(
        onEnter: (_) => _setHoverState(true),
        onExit: (_) => _setHoverState(false),
        cursor: widget.onTap != null
            ? SystemMouseCursors.click
            : MouseCursor.defer,
        child: Semantics(
          button: widget.onTap != null,
          child: GestureDetector(
            behavior: widget.onTap != null
                ? HitTestBehavior.opaque
                : HitTestBehavior.deferToChild,
            onTap: widget.onTap,
            child: _buildCard(),
          ),
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
              ? (widget.gradientBorder?.colors.first ?? Colors.white)
                    .withValues(alpha: 0.5)
              : AppColors.glassBorder,
          width: 1.5,
        ),
        child: widget.child,
      ),
    );

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
