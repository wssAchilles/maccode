/// 统一值班区块包裹器
library;

import 'package:flutter/material.dart';

import 'section_intro.dart';

class DutySectionBlock extends StatelessWidget {
  const DutySectionBlock({
    super.key,
    required this.title,
    required this.subtitle,
    required this.child,
    this.trailing,
    this.spacing = 12,
  });

  final String title;
  final String subtitle;
  final Widget child;
  final Widget? trailing;
  final double spacing;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionIntro(title: title, subtitle: subtitle, trailing: trailing),
        SizedBox(height: spacing),
        child,
      ],
    );
  }
}
