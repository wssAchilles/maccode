part of '../app_theme.dart';

class AppTextStyles {
  AppTextStyles._();

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

  static TextStyle get headingFont =>
      _withCjkFallback(GoogleFonts.notoSansSc());
  static TextStyle get bodyFont => _withCjkFallback(GoogleFonts.notoSansSc());
  static TextStyle get codeFont => _withCjkFallback(GoogleFonts.firaCode());

  static TextStyle get h1 => _withCjkFallback(
    GoogleFonts.notoSansSc(
      fontSize: 32,
      fontWeight: FontWeight.bold,
      color: AppColors.textPrimary,
      height: 1.2,
    ),
  );

  static TextStyle get h2 => _withCjkFallback(
    GoogleFonts.notoSansSc(
      fontSize: 24,
      fontWeight: FontWeight.bold,
      color: AppColors.textPrimary,
      height: 1.3,
    ),
  );

  static TextStyle get h3 => _withCjkFallback(
    GoogleFonts.notoSansSc(
      fontSize: 20,
      fontWeight: FontWeight.w600,
      color: AppColors.textPrimary,
      height: 1.4,
    ),
  );

  static TextStyle get h4 => _withCjkFallback(
    GoogleFonts.notoSansSc(
      fontSize: 18,
      fontWeight: FontWeight.w600,
      color: AppColors.textPrimary,
    ),
  );

  static TextStyle get bodyLarge => _withCjkFallback(
    GoogleFonts.notoSansSc(
      fontSize: 16,
      fontWeight: FontWeight.normal,
      color: AppColors.textPrimary,
      height: 1.5,
    ),
  );

  static TextStyle get bodyMedium => _withCjkFallback(
    GoogleFonts.notoSansSc(
      fontSize: 14,
      fontWeight: FontWeight.normal,
      color: AppColors.textPrimary,
      height: 1.5,
    ),
  );

  static TextStyle get bodySmall => _withCjkFallback(
    GoogleFonts.notoSansSc(
      fontSize: 12,
      fontWeight: FontWeight.normal,
      color: AppColors.textSecondary,
      height: 1.4,
    ),
  );

  static TextStyle get labelLarge => _withCjkFallback(
    GoogleFonts.notoSansSc(
      fontSize: 14,
      fontWeight: FontWeight.w600,
      color: AppColors.textPrimary,
      letterSpacing: 0.5,
    ),
  );

  static TextStyle get labelMedium => _withCjkFallback(
    GoogleFonts.notoSansSc(
      fontSize: 12,
      fontWeight: FontWeight.w500,
      color: AppColors.textSecondary,
    ),
  );

  static TextStyle get labelSmall => _withCjkFallback(
    GoogleFonts.notoSansSc(
      fontSize: 10,
      fontWeight: FontWeight.w500,
      color: AppColors.textSecondary,
      letterSpacing: 0.5,
    ),
  );

  static TextStyle get button => _withCjkFallback(
    GoogleFonts.notoSansSc(
      fontSize: 16,
      fontWeight: FontWeight.w600,
      letterSpacing: 0.5,
    ),
  );
}
