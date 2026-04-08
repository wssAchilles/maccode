library;

import 'compute_governance_activity_entry.dart';
import 'compute_rollout_policy.dart';
import 'control_task_record.dart';
import 'dashboard_summary.dart';
import 'job_record.dart';

class ShellRuntimeSnapshot {
  const ShellRuntimeSnapshot({
    required this.projectionVersion,
    required this.generatedAt,
    required this.summary,
    required this.approvalJobs,
    required this.controlTasks,
    required this.computePolicy,
    required this.computeActivity,
    this.degradedSections = const <ShellRuntimeDegradedSection>[],
  });

  final String projectionVersion;
  final DateTime? generatedAt;
  final DashboardSummary? summary;
  final List<JobRecord> approvalJobs;
  final List<ControlTaskRecord> controlTasks;
  final ComputeRolloutPolicy computePolicy;
  final List<ComputeGovernanceActivityEntry> computeActivity;
  final List<ShellRuntimeDegradedSection> degradedSections;

  factory ShellRuntimeSnapshot.fromJson(Map<String, dynamic> json) {
    final summaryJson = json['summary'];
    final approvalQueue = json['approval_queue'];
    final controlTasks = json['control_tasks'];
    final computeGovernance = json['compute_governance'];
    final degraded = json['degraded_sections'];
    return ShellRuntimeSnapshot(
      projectionVersion: (json['projection_version'] ?? 'shell-runtime-v1')
          .toString(),
      generatedAt: _parseDateTime(json['generated_at']),
      summary: summaryJson is Map<String, dynamic>
          ? DashboardSummary.fromJson(summaryJson)
          : summaryJson is Map
          ? DashboardSummary.fromJson(Map<String, dynamic>.from(summaryJson))
          : null,
      approvalJobs: _parseJobs(
        approvalQueue is Map ? approvalQueue['jobs'] : null,
      ),
      controlTasks: _parseControlTasks(
        controlTasks is Map ? controlTasks['items'] : null,
      ),
      computePolicy: _parsePolicy(
        computeGovernance is Map ? computeGovernance['policy'] : null,
      ),
      computeActivity: _parseActivity(
        computeGovernance is Map ? computeGovernance['activity'] : null,
      ),
      degradedSections: degraded is List
          ? degraded
                .map((item) {
                  if (item is Map<String, dynamic>) {
                    return ShellRuntimeDegradedSection.fromJson(item);
                  }
                  if (item is Map) {
                    return ShellRuntimeDegradedSection.fromJson(
                      Map<String, dynamic>.from(item),
                    );
                  }
                  return null;
                })
                .whereType<ShellRuntimeDegradedSection>()
                .toList(growable: false)
          : const <ShellRuntimeDegradedSection>[],
    );
  }
}

class ShellRuntimeDegradedSection {
  const ShellRuntimeDegradedSection({
    required this.section,
    required this.message,
  });

  final String section;
  final String message;

  factory ShellRuntimeDegradedSection.fromJson(Map<String, dynamic> json) {
    return ShellRuntimeDegradedSection(
      section: (json['section'] ?? '').toString(),
      message: (json['message'] ?? '').toString(),
    );
  }
}

DateTime? _parseDateTime(Object? value) {
  if (value == null) {
    return null;
  }
  return DateTime.tryParse(value.toString())?.toLocal();
}

List<JobRecord> _parseJobs(Object? value) {
  if (value is! List) {
    return const <JobRecord>[];
  }
  return value
      .map((item) {
        if (item is Map<String, dynamic>) {
          return JobRecord.fromJson(item);
        }
        if (item is Map) {
          return JobRecord.fromJson(Map<String, dynamic>.from(item));
        }
        return null;
      })
      .whereType<JobRecord>()
      .toList(growable: false);
}

List<ControlTaskRecord> _parseControlTasks(Object? value) {
  if (value is! List) {
    return const <ControlTaskRecord>[];
  }
  return value
      .map((item) {
        if (item is Map<String, dynamic>) {
          return ControlTaskRecord.fromJson(item);
        }
        if (item is Map) {
          return ControlTaskRecord.fromJson(Map<String, dynamic>.from(item));
        }
        return null;
      })
      .whereType<ControlTaskRecord>()
      .toList(growable: false);
}

ComputeRolloutPolicy _parsePolicy(Object? value) {
  if (value is Map<String, dynamic>) {
    return ComputeRolloutPolicy.fromJson(value);
  }
  if (value is Map) {
    return ComputeRolloutPolicy.fromJson(Map<String, dynamic>.from(value));
  }
  return const ComputeRolloutPolicy.empty();
}

List<ComputeGovernanceActivityEntry> _parseActivity(Object? value) {
  if (value is! List) {
    return const <ComputeGovernanceActivityEntry>[];
  }
  return value
      .map((item) {
        if (item is Map<String, dynamic>) {
          return ComputeGovernanceActivityEntry.fromJson(item);
        }
        if (item is Map) {
          return ComputeGovernanceActivityEntry.fromJson(
            Map<String, dynamic>.from(item),
          );
        }
        return null;
      })
      .whereType<ComputeGovernanceActivityEntry>()
      .toList(growable: false);
}
