part of '../app_theme.dart';

class AppDecorations {
  AppDecorations._();

  static const double radiusXs = 4.0;
  static const double radiusSm = 6.0;
  static const double radiusMd = 8.0;
  static const double radiusLg = 12.0;
  static const double radiusXl = 16.0;
  static const double radius2xl = 20.0;
  static const double radiusFull = 9999.0;

  static List<BoxShadow> get shadowXs => [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.03),
      blurRadius: 2,
      offset: const Offset(0, 1),
    ),
  ];

  static List<BoxShadow> get shadowSm => [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.05),
      blurRadius: 4,
      offset: const Offset(0, 2),
    ),
  ];

  static List<BoxShadow> get shadowMd => [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.1),
      blurRadius: 6,
      offset: const Offset(0, 4),
    ),
  ];

  static List<BoxShadow> get shadowLg => [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.1),
      blurRadius: 15,
      offset: const Offset(0, 8),
    ),
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.04),
      blurRadius: 6,
      offset: const Offset(0, 4),
    ),
  ];

  static List<BoxShadow> get shadowXl => [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.15),
      blurRadius: 25,
      offset: const Offset(0, 12),
    ),
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.08),
      blurRadius: 10,
      offset: const Offset(0, 6),
    ),
  ];

  static const Duration animationFast = Duration(milliseconds: 150);
  static const Duration animationNormal = Duration(milliseconds: 300);
  static const Duration animationSlow = Duration(milliseconds: 500);
  static const Curve animationCurve = Curves.easeOutCubic;

  static BoxDecoration get glassCard => BoxDecoration(
    color: AppColors.glassWhite,
    borderRadius: BorderRadius.circular(radiusLg),
    border: Border.all(color: AppColors.glassBorder, width: 1),
    boxShadow: shadowMd,
  );

  static BoxDecoration get card => BoxDecoration(
    color: AppColors.surface,
    borderRadius: BorderRadius.circular(radiusLg),
    border: Border.all(color: AppColors.border, width: 1),
    boxShadow: shadowSm,
  );

  static BoxDecoration get elevatedCard => BoxDecoration(
    color: AppColors.surface,
    borderRadius: BorderRadius.circular(radiusLg),
    boxShadow: shadowLg,
  );

  static BoxDecoration gradientCard(LinearGradient gradient) => BoxDecoration(
    gradient: gradient,
    borderRadius: BorderRadius.circular(radiusLg),
    boxShadow: shadowMd,
  );

  static BoxDecoration get dashedBorder => BoxDecoration(
    color: AppColors.surfaceVariant,
    borderRadius: BorderRadius.circular(radiusLg),
    border: Border.all(color: AppColors.border, width: 2),
  );
}
