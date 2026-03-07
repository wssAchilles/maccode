import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';

import 'package:front/config/app_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  GoogleFonts.config.allowRuntimeFetching = false;

  group('AppTheme.lightTheme', () {
    testWidgets('maps core design tokens into ThemeData', (
      WidgetTester tester,
    ) async {
      final theme = AppTheme.lightTheme;
      await GoogleFonts.pendingFonts();

      final elevatedStyle = theme.elevatedButtonTheme.style;
      final inputTheme = theme.inputDecorationTheme;
      final focusedBorder = inputTheme.focusedBorder as OutlineInputBorder;

      expect(theme.useMaterial3, isTrue);
      expect(theme.colorScheme.primary, AppColors.primary);
      expect(theme.scaffoldBackgroundColor, AppColors.background);
      expect(
        theme.bottomNavigationBarTheme.selectedItemColor,
        AppColors.primary,
      );
      expect(
        elevatedStyle?.backgroundColor?.resolve(<WidgetState>{}),
        AppColors.cta,
      );
      expect(inputTheme.fillColor, AppColors.surfaceVariant);
      expect(
        focusedBorder.borderRadius,
        BorderRadius.circular(AppDecorations.radiusMd),
      );
      expect(focusedBorder.borderSide.color, AppColors.primary);
      expect(focusedBorder.borderSide.width, 2);
    });

    testWidgets('exposes the configured typography scale', (
      WidgetTester tester,
    ) async {
      final textTheme = AppTheme.lightTheme.textTheme;
      await GoogleFonts.pendingFonts();

      expect(textTheme.displayLarge?.fontSize, 32);
      expect(textTheme.bodyMedium?.fontSize, 14);
      expect(textTheme.labelMedium?.fontSize, 12);
      expect(textTheme.displaySmall?.fontWeight, FontWeight.w600);
    });
  });
}
