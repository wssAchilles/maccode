part of '../analysis_results_section.dart';

class _BasicInfoCard extends StatelessWidget {
  const _BasicInfoCard({required this.result});

  final AnalysisResult result;

  @override
  Widget build(BuildContext context) {
    final basicInfo = result.basicInfo;

    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.info_outline, size: 28),
                SizedBox(width: 8),
                Text(
                  '基本信息',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const Divider(),
            const SizedBox(height: 8),
            _AnalysisInfoRow(label: '行数', value: '${basicInfo.rows}'),
            _AnalysisInfoRow(label: '列数', value: '${basicInfo.columns}'),
            const SizedBox(height: 12),
            const Text(
              '列名与类型:',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: basicInfo.columnNames
                  .map(
                    (column) => Tooltip(
                      message:
                          '类型: ${basicInfo.columnTypes[column] ?? "unknown"}',
                      child: Chip(
                        avatar: Icon(
                          _columnTypeIcon(basicInfo.columnTypes[column]),
                          size: 16,
                        ),
                        label: Text(column),
                        backgroundColor: _columnTypeColor(
                          basicInfo.columnTypes[column],
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
        ),
      ),
    );
  }
}

class _PreviewCard extends StatelessWidget {
  const _PreviewCard({required this.preview, required this.columns});

  final List<Map<String, dynamic>> preview;
  final List<String> columns;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '数据预览 (前5行)',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const Divider(),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                key: const ValueKey('analysis-preview-table'),
                columns: columns
                    .map(
                      (column) => DataColumn(
                        label: Text(
                          column,
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ),
                    )
                    .toList(),
                rows: preview
                    .map(
                      (row) => DataRow(
                        cells: columns
                            .map(
                              (column) =>
                                  DataCell(Text(row[column]?.toString() ?? '')),
                            )
                            .toList(),
                      ),
                    )
                    .toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AnalysisInfoRow extends StatelessWidget {
  const _AnalysisInfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
          Text(value),
        ],
      ),
    );
  }
}

IconData _columnTypeIcon(String? type) {
  final normalizedType = (type ?? '').toLowerCase();
  if (normalizedType.contains('int') || normalizedType.contains('float')) {
    return Icons.numbers;
  }
  if (normalizedType.contains('object') || normalizedType.contains('string')) {
    return Icons.text_fields;
  }
  if (normalizedType.contains('datetime')) {
    return Icons.calendar_today;
  }
  if (normalizedType.contains('bool')) {
    return Icons.toggle_on;
  }
  return Icons.help_outline;
}

Color _columnTypeColor(String? type) {
  final normalizedType = (type ?? '').toLowerCase();
  if (normalizedType.contains('int') || normalizedType.contains('float')) {
    return Colors.blue.shade50;
  }
  if (normalizedType.contains('object') || normalizedType.contains('string')) {
    return Colors.green.shade50;
  }
  if (normalizedType.contains('datetime')) {
    return Colors.purple.shade50;
  }
  if (normalizedType.contains('bool')) {
    return Colors.orange.shade50;
  }
  return Colors.grey.shade50;
}
