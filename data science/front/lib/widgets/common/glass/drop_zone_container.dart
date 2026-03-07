part of '../glass_card.dart';

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

  void _updateHover(bool value) {
    if (_isHovered == value) {
      return;
    }

    setState(() => _isHovered = value);
  }

  @override
  Widget build(BuildContext context) {
    final isHighlighted = _isHovered || widget.isActive;

    return MouseRegion(
      cursor: widget.onTap != null
          ? SystemMouseCursors.click
          : MouseCursor.defer,
      onEnter: (_) => _updateHover(true),
      onExit: (_) => _updateHover(false),
      child: GestureDetector(
        behavior: widget.onTap != null
            ? HitTestBehavior.opaque
            : HitTestBehavior.deferToChild,
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
