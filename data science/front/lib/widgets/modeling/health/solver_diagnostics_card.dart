part of '../modeling_health_section.dart';

class SolverDiagnosticsCard extends StatelessWidget {
  const SolverDiagnosticsCard({super.key, required this.optimization});

  final OptimizationData optimization;

  @override
  Widget build(BuildContext context) {
    final diagnostics = optimization.diagnostics;
    final hits = optimization.constraintHits;
    if (diagnostics == null && hits == null) {
      return const SizedBox.shrink();
    }

    return Card(
      elevation: 3,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.speed, color: Colors.blue[700]),
                const SizedBox(width: 8),
                const Text(
                  '求解器健康度',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _SolverRuntimeStats(diagnostics: diagnostics),
            if (hits != null) ...[
              const SizedBox(height: 12),
              _ConstraintHitsStats(hits: hits),
            ],
          ],
        ),
      ),
    );
  }
}

class _SolverRuntimeStats extends StatelessWidget {
  const _SolverRuntimeStats({required this.diagnostics});

  final SolverDiagnostics? diagnostics;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: ModelingStatItem(
                icon: Icons.timer,
                label: '求解耗时',
                value: diagnostics?.runtimeLabel ?? 'N/A',
                color: Colors.blue[700]!,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ModelingStatItem(
                icon: Icons.data_usage,
                label: 'MIP Gap',
                value: diagnostics?.mipGap != null
                    ? '${(diagnostics!.mipGap! * 100).toStringAsFixed(2)}%'
                    : 'N/A',
                color: Colors.deepOrange[700]!,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: ModelingStatItem(
                icon: Icons.account_tree,
                label: 'Node',
                value: diagnostics?.nodeCount?.toString() ?? '—',
                color: Colors.teal[700]!,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ModelingStatItem(
                icon: Icons.loop,
                label: '迭代',
                value: diagnostics?.iterCount?.toString() ?? '—',
                color: Colors.indigo[700]!,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ConstraintHitsStats extends StatelessWidget {
  const _ConstraintHitsStats({required this.hits});

  final ConstraintHits hits;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: ModelingStatItem(
                icon: Icons.battery_alert,
                label: 'SOC 下限命中',
                value: '${hits.socMinHits} 次',
                color: Colors.red[600]!,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ModelingStatItem(
                icon: Icons.battery_full,
                label: 'SOC 上限命中',
                value: '${hits.socMaxHits} 次',
                color: Colors.green[700]!,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: ModelingStatItem(
                icon: Icons.flash_on,
                label: '充电功率封顶',
                value: '${hits.maxChargeHits} 小时',
                color: Colors.orange[700]!,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ModelingStatItem(
                icon: Icons.bolt,
                label: '放电功率封顶',
                value: '${hits.maxDischargeHits} 小时',
                color: Colors.blueGrey[700]!,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
