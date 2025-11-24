/// 响应式设计辅助工具
/// 提供统一的断点和尺寸计算方法
library;

import 'package:flutter/material.dart';

class ResponsiveHelper {
  /// 屏幕断点定义
  static const double mobileBreakpoint = 600;
  static const double tabletBreakpoint = 900;
  static const double desktopBreakpoint = 1200;
  
  /// 获取屏幕类型
  static ScreenType getScreenType(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    
    if (width < mobileBreakpoint) {
      return ScreenType.mobile;
    } else if (width < tabletBreakpoint) {
      return ScreenType.tablet;
    } else if (width < desktopBreakpoint) {
      return ScreenType.desktop;
    } else {
      return ScreenType.largeDesktop;
    }
  }
  
  /// 判断是否为移动端
  static bool isMobile(BuildContext context) {
    return MediaQuery.of(context).size.width < mobileBreakpoint;
  }
  
  /// 判断是否为平板
  static bool isTablet(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    return width >= mobileBreakpoint && width < tabletBreakpoint;
  }
  
  /// 判断是否为桌面端
  static bool isDesktop(BuildContext context) {
    return MediaQuery.of(context).size.width >= tabletBreakpoint;
  }
  
  /// 获取响应式值
  /// 根据屏幕大小返回不同的值
  static T getResponsiveValue<T>(
    BuildContext context, {
    required T mobile,
    T? tablet,
    T? desktop,
    T? largeDesktop,
  }) {
    final screenType = getScreenType(context);
    
    switch (screenType) {
      case ScreenType.mobile:
        return mobile;
      case ScreenType.tablet:
        return tablet ?? mobile;
      case ScreenType.desktop:
        return desktop ?? tablet ?? mobile;
      case ScreenType.largeDesktop:
        return largeDesktop ?? desktop ?? tablet ?? mobile;
    }
  }
  
  /// 获取响应式字体大小
  static double getResponsiveFontSize(
    BuildContext context, {
    required double mobile,
    double? tablet,
    double? desktop,
  }) {
    return getResponsiveValue(
      context,
      mobile: mobile,
      tablet: tablet,
      desktop: desktop,
    );
  }
  
  /// 获取响应式间距
  static double getResponsiveSpacing(
    BuildContext context, {
    required double mobile,
    double? tablet,
    double? desktop,
  }) {
    return getResponsiveValue(
      context,
      mobile: mobile,
      tablet: tablet,
      desktop: desktop,
    );
  }
  
  /// 获取网格列数
  static int getGridColumns(BuildContext context, {
    int mobile = 1,
    int tablet = 2,
    int desktop = 3,
  }) {
    return getResponsiveValue(
      context,
      mobile: mobile,
      tablet: tablet,
      desktop: desktop,
    );
  }
  
  /// 获取内容最大宽度
  static double getMaxContentWidth(BuildContext context) {
    return getResponsiveValue(
      context,
      mobile: double.infinity,
      tablet: 800,
      desktop: 1200,
      largeDesktop: 1400,
    );
  }
  
  /// 获取卡片边距
  static EdgeInsets getCardPadding(BuildContext context) {
    return EdgeInsets.all(
      getResponsiveValue(
        context,
        mobile: 12.0,
        tablet: 16.0,
        desktop: 20.0,
      ),
    );
  }
  
  /// 获取页面边距
  static EdgeInsets getPagePadding(BuildContext context) {
    return EdgeInsets.all(
      getResponsiveValue(
        context,
        mobile: 16.0,
        tablet: 24.0,
        desktop: 32.0,
      ),
    );
  }
}

/// 屏幕类型枚举
enum ScreenType {
  mobile,
  tablet,
  desktop,
  largeDesktop,
}

/// 响应式布局构建器
class ResponsiveBuilder extends StatelessWidget {
  final Widget Function(BuildContext context, ScreenType screenType) builder;
  
  const ResponsiveBuilder({
    super.key,
    required this.builder,
  });
  
  @override
  Widget build(BuildContext context) {
    final screenType = ResponsiveHelper.getScreenType(context);
    return builder(context, screenType);
  }
}

/// 响应式网格视图
class ResponsiveGrid extends StatelessWidget {
  final List<Widget> children;
  final int mobileColumns;
  final int tabletColumns;
  final int desktopColumns;
  final double spacing;
  final double runSpacing;
  
  const ResponsiveGrid({
    super.key,
    required this.children,
    this.mobileColumns = 1,
    this.tabletColumns = 2,
    this.desktopColumns = 3,
    this.spacing = 16.0,
    this.runSpacing = 16.0,
  });
  
  @override
  Widget build(BuildContext context) {
    final columns = ResponsiveHelper.getGridColumns(
      context,
      mobile: mobileColumns,
      tablet: tabletColumns,
      desktop: desktopColumns,
    );
    
    return GridView.count(
      crossAxisCount: columns,
      crossAxisSpacing: spacing,
      mainAxisSpacing: runSpacing,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      children: children,
    );
  }
}
