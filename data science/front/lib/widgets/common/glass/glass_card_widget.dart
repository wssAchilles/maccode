part of '../glass_card.dart';

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

  void _updateHover(bool value) {
    if (!widget.enableHover || _isHovered == value) {
      return;
    }

    setState(() => _isHovered = value);
  }

  @override
  Widget build(BuildContext context) {
    final radius =
        widget.borderRadius ?? BorderRadius.circular(AppDecorations.radiusLg);

    final content = AnimatedContainer(
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
    );

    final card = ClipRRect(
      borderRadius: radius,
      child: kIsWeb
          ? content
          : BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: widget.blur,
                sigmaY: widget.blur,
              ),
              child: content,
            ),
    );

    return RepaintBoundary(
      child: Container(
        margin: widget.margin,
        child: MouseRegion(
          cursor: widget.onTap != null
              ? SystemMouseCursors.click
              : MouseCursor.defer,
          onEnter: widget.enableHover ? (_) => _updateHover(true) : null,
          onExit: widget.enableHover ? (_) => _updateHover(false) : null,
          child: Semantics(
            button: widget.onTap != null,
            child: GestureDetector(
              behavior: widget.onTap != null
                  ? HitTestBehavior.opaque
                  : HitTestBehavior.deferToChild,
              onTap: widget.onTap,
              child: AnimatedScale(
                scale: _isHovered && widget.enableHover ? 1.01 : 1.0,
                duration: AppDecorations.animationFast,
                curve: AppDecorations.animationCurve,
                child: card,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
