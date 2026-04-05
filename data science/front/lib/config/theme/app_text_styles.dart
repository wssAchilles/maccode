part of '../app_theme.dart';

class AppTextStyles {
  AppTextStyles._();

  static const String _headingFamily = 'SpaceGrotesk';
  static const String _bodyFamily = 'DMSans';
  static const String _codeFamily = 'FiraCode';

  static const List<String> _cjkFallbacks = [
    'Noto Sans SC',
    'PingFang SC',
    'Hiragino Sans GB',
    'Microsoft YaHei',
    'Source Han Sans SC',
    'sans-serif',
  ];

  static TextStyle _withCjkFallback(TextStyle style) =>
      style.copyWith(fontFamilyFallback: _cjkFallbacks);

  static TextStyle _headingStyle({
    required double fontSize,
    required FontWeight fontWeight,
    required Color color,
    double? height,
    double? letterSpacing,
  }) => _withCjkFallback(
    TextStyle(
      fontFamily: _headingFamily,
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      height: height,
      letterSpacing: letterSpacing,
    ),
  );

  static TextStyle _bodyStyle({
    required double fontSize,
    required FontWeight fontWeight,
    required Color color,
    double? height,
    double? letterSpacing,
  }) => _withCjkFallback(
    TextStyle(
      fontFamily: _bodyFamily,
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      height: height,
      letterSpacing: letterSpacing,
    ),
  );

  static TextStyle get headingFont =>
      _withCjkFallback(const TextStyle(fontFamily: _headingFamily));
  static TextStyle get bodyFont =>
      _withCjkFallback(const TextStyle(fontFamily: _bodyFamily));
  static TextStyle get codeFont => _withCjkFallback(
    const TextStyle(fontFamily: _codeFamily),
  );

  static TextStyle get h1 => _headingStyle(
    fontSize: 32,
    fontWeight: FontWeight.bold,
    color: AppColors.textPrimary,
    height: 1.2,
  );

  static TextStyle get h2 => _headingStyle(
    fontSize: 24,
    fontWeight: FontWeight.bold,
    color: AppColors.textPrimary,
    height: 1.3,
  );

  static TextStyle get h3 => _headingStyle(
    fontSize: 20,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
    height: 1.4,
  );

  static TextStyle get h4 => _headingStyle(
    fontSize: 18,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  );

  static TextStyle get bodyLarge => _bodyStyle(
    fontSize: 16,
    fontWeight: FontWeight.normal,
    color: AppColors.textPrimary,
    height: 1.5,
  );

  static TextStyle get bodyMedium => _bodyStyle(
    fontSize: 14,
    fontWeight: FontWeight.normal,
    color: AppColors.textPrimary,
    height: 1.5,
  );

  static TextStyle get bodySmall => _bodyStyle(
    fontSize: 12,
    fontWeight: FontWeight.normal,
    color: AppColors.textSecondary,
    height: 1.4,
  );

  static TextStyle get labelLarge => _bodyStyle(
    fontSize: 14,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
    letterSpacing: 0.5,
  );

  static TextStyle get labelMedium => _bodyStyle(
    fontSize: 12,
    fontWeight: FontWeight.w500,
    color: AppColors.textSecondary,
  );

  static TextStyle get labelSmall => _bodyStyle(
    fontSize: 10,
    fontWeight: FontWeight.w500,
    color: AppColors.textSecondary,
    letterSpacing: 0.5,
  );

  static TextStyle get button => _bodyStyle(
    fontSize: 16,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
    letterSpacing: 0.5,
  );
}
