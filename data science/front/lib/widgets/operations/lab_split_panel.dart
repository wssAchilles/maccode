/// AI Lab 分栏容器
library;

import 'package:flutter/material.dart';

import '../../utils/responsive_helper.dart';

class LabSplitPanel extends StatelessWidget {
  const LabSplitPanel({
    super.key,
    required this.left,
    required this.right,
    this.spacing = 20,
  });

  final Widget left;
  final Widget right;
  final double spacing;

  @override
  Widget build(BuildContext context) {
    final stacked = !ResponsiveHelper.isDesktop(context);
    if (stacked) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          left,
          SizedBox(height: spacing),
          right,
        ],
      );
    }

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(flex: 5, child: left),
        SizedBox(width: spacing),
        Expanded(flex: 7, child: right),
      ],
    );
  }
}
