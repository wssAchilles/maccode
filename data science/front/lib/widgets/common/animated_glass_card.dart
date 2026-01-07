import 'package:flutter/material.dart';
import '../../config/app_theme.dart';
// Note: Removed unused import constants.dart
// Note: Removed unused import

/// 高级动态玻璃卡片
/// 支持鼠标悬停光泽效果、淡入动画和点击反馈
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
    if (isHovered) {
      _controller.forward();
    } else {
      _controller.reverse();
    }
  }

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => _onHover(true),
      onExit: (_) => _onHover(false),
      cursor: widget.onTap != null ? SystemMouseCursors.click : SystemMouseCursors.basic,
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedBuilder(
          animation: _controller,
          builder: (context, child) {
            return Transform.scale(
              scale: _scaleAnimation.value,
              child: Container(
                margin: widget.margin,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(widget.borderRadius),
                  boxShadow: _isHovered
                      ? AppDecorations.shadowLg // 悬停时阴影加深
                      : AppDecorations.shadowMd,
                ),
                child: GlassContainer(
                  borderRadius: BorderRadius.circular(widget.borderRadius),
                  padding: widget.padding,
                  // 动态边框颜色
                  border: Border.all(
                    color: _isHovered 
                        ? (widget.gradientBorder?.colors.first ?? Colors.white).withValues(alpha: 0.5)
                        : AppColors.glassBorder,
                    width: 1.5,
                  ),
                  child: widget.child,
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
