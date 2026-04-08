library;

import 'package:flutter/material.dart';

typedef WorkspacePageBuilder =
    Widget Function(BuildContext context, int index, bool isActive);

/// Lazily mounts workspaces on first visit while preserving state for
/// previously visited tabs.
class LazyWorkspaceStack extends StatefulWidget {
  const LazyWorkspaceStack({
    super.key,
    required this.currentIndex,
    required this.pageCount,
    required this.pageBuilder,
  });

  final int currentIndex;
  final int pageCount;
  final WorkspacePageBuilder pageBuilder;

  @override
  State<LazyWorkspaceStack> createState() => _LazyWorkspaceStackState();
}

class _LazyWorkspaceStackState extends State<LazyWorkspaceStack> {
  late final Set<int> _visitedIndexes = <int>{widget.currentIndex};

  @override
  void didUpdateWidget(covariant LazyWorkspaceStack oldWidget) {
    super.didUpdateWidget(oldWidget);
    _visitedIndexes.add(widget.currentIndex);
    if (widget.pageCount != oldWidget.pageCount) {
      _visitedIndexes.removeWhere((index) => index >= widget.pageCount);
    }
  }

  @override
  Widget build(BuildContext context) {
    return IndexedStack(
      index: widget.currentIndex,
      children: List<Widget>.generate(widget.pageCount, (index) {
        if (!_visitedIndexes.contains(index)) {
          return const SizedBox.shrink();
        }
        return KeyedSubtree(
          key: ValueKey<int>(index),
          child: widget.pageBuilder(
            context,
            index,
            widget.currentIndex == index,
          ),
        );
      }, growable: false),
    );
  }
}
