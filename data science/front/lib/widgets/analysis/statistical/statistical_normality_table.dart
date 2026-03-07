part of '../statistical_panel.dart';

class _StatisticalNormalityTable extends StatelessWidget {
  const _StatisticalNormalityTable({required this.tests});

  final Map<String, NormalityTest> tests;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '正态性检验详情',
          style: Theme.of(
            context,
          ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            headingRowColor: WidgetStatePropertyAll(Colors.grey.shade100),
            dataRowMinHeight: 48,
            dataRowMaxHeight: 64,
            columns: const [
              DataColumn(
                label: Text(
                  '变量名',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              DataColumn(
                label: Text(
                  '检验方法',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              DataColumn(
                label: Text(
                  'p-value',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              DataColumn(
                label: Text(
                  '结果',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              DataColumn(
                label: Text(
                  '偏度',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              DataColumn(
                label: Text(
                  '峰度',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              DataColumn(
                label: Text(
                  '样本数',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
            ],
            rows: tests.entries
                .map(
                  (entry) => entry.value.error != null
                      ? _buildErrorRow(entry.key, entry.value)
                      : _buildResultRow(entry.key, entry.value),
                )
                .toList(growable: false),
          ),
        ),
      ],
    );
  }
}

DataRow _buildErrorRow(String columnName, NormalityTest test) {
  return DataRow(
    cells: [
      DataCell(Text(columnName)),
      DataCell(Text(test.error!, style: const TextStyle(color: Colors.red))),
      const DataCell(Text('-')),
      const DataCell(Text('-')),
      const DataCell(Text('-')),
      const DataCell(Text('-')),
      const DataCell(Text('-')),
    ],
  );
}

DataRow _buildResultRow(String columnName, NormalityTest test) {
  final isNormal = test.isNormal ?? false;
  final rowColor = isNormal ? null : Colors.red.shade50;
  final pValue = test.pValue;
  final skewness = test.skewness;

  return DataRow(
    color: WidgetStatePropertyAll(rowColor),
    cells: [
      DataCell(
        Text(columnName, style: const TextStyle(fontWeight: FontWeight.w500)),
      ),
      DataCell(Text(test.testName ?? '-')),
      DataCell(
        Text(
          pValue != null
              ? (pValue < 0.001 ? '<0.001' : pValue.toStringAsFixed(4))
              : '-',
          style: TextStyle(
            color: (pValue ?? 1.0) < 0.05 ? Colors.red : Colors.green,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      DataCell(_NormalityResultBadge(test: test, isNormal: isNormal)),
      DataCell(
        Text(
          skewness != null ? skewness.toStringAsFixed(2) : '-',
          style: TextStyle(
            color: (skewness?.abs() ?? 0) > 1 ? Colors.orange : Colors.black,
          ),
        ),
      ),
      DataCell(
        Text(test.kurtosis != null ? test.kurtosis!.toStringAsFixed(2) : '-'),
      ),
      DataCell(Text(test.nSamples?.toString() ?? '-')),
    ],
  );
}

class _NormalityResultBadge extends StatelessWidget {
  const _NormalityResultBadge({required this.test, required this.isNormal});

  final NormalityTest test;
  final bool isNormal;

  @override
  Widget build(BuildContext context) {
    final color = isNormal ? Colors.green : Colors.red;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(isNormal ? Icons.check : Icons.close, size: 16, color: color),
          const SizedBox(width: 4),
          Text(
            test.distribution ?? '-',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
