import 'package:flutter/material.dart';

/// A wrapper widget that makes the content responsive.
/// 
/// It constrains the maximum width of the content on larger screens
/// to prevent UI elements from stretching too wide.
class ResponsiveWrapper extends StatelessWidget {
  final Widget child;
  final double maxWidth;
  final double mobileBreakpoint;

  const ResponsiveWrapper({
    super.key,
    required this.child,
    this.maxWidth = 1000.0,
    this.mobileBreakpoint = 800.0,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth > mobileBreakpoint) {
          return Center(
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: maxWidth),
              child: child,
            ),
          );
        }
        return child;
      },
    );
  }
}
