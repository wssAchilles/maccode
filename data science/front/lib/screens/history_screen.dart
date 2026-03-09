/// Legacy history screen wrapper.
library;

import 'package:flutter/material.dart';

import '../viewmodels/history_view_model.dart';
import 'history_audit_screen.dart';

@Deprecated('Use HistoryAuditScreen instead.')
class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key, this.viewModel});

  final HistoryViewModel? viewModel;

  @override
  Widget build(BuildContext context) {
    return const HistoryAuditScreen();
  }
}
