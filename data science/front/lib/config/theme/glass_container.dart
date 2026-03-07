part of '../app_theme.dart';

class GlassContainer extends StatelessWidget {
  const GlassContainer({
    super.key,
    required this.child,
    this.borderRadius,
    this.blur = 10.0,
    this.opacity = 0.8,
    this.padding,
    this.margin,
    this.border,
  });

  final Widget child;
  final BorderRadius? borderRadius;
  final double blur;
  final double opacity;
  final EdgeInsets? padding;
  final EdgeInsets? margin;
  final BoxBorder? border;

  @override
  Widget build(BuildContext context) {
    final resolvedBorderRadius =
        borderRadius ?? BorderRadius.circular(AppDecorations.radiusLg);

    return Container(
      margin: margin,
      child: ClipRRect(
        borderRadius: resolvedBorderRadius,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
          child: Container(
            padding: padding,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: opacity),
              borderRadius: resolvedBorderRadius,
              border:
                  border ??
                  Border.all(
                    color: Colors.white.withValues(alpha: 0.2),
                    width: 1,
                  ),
              boxShadow: AppDecorations.shadowMd,
            ),
            child: child,
          ),
        ),
      ),
    );
  }
}
