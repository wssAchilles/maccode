library;

import 'package:flutter/material.dart';

import 'analysis_detail_support.dart';

class AnalysisBasicInfoSection extends StatelessWidget {
  const AnalysisBasicInfoSection({super.key, required this.basicInfo});

  final Map<String, dynamic> basicInfo;

  @override
  Widget build(BuildContext context) {
    final columnTypes = analysisDetailAsMap(basicInfo['column_types']);

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _MetricRow(
              label: '数据行数',
              value: analysisDetailStringValue(basicInfo['rows']),
            ),
            _MetricRow(
              label: '数据列数',
              value: analysisDetailStringValue(basicInfo['columns']),
            ),
            _MetricRow(
              label: '内存使用',
              value: analysisDetailStringValue(basicInfo['memory_usage']),
            ),
            if (columnTypes != null && columnTypes.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text(
                '列类型',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              ...columnTypes.entries.map(
                (entry) => Padding(
                  padding: const EdgeInsets.only(bottom: 4.0),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          entry.key,
                          style: const TextStyle(fontSize: 13),
                        ),
                      ),
                      Chip(
                        label: Text(
                          entry.value.toString(),
                          style: const TextStyle(fontSize: 11),
                        ),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 0,
                        ),
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class AnalysisDataPreviewSection extends StatelessWidget {
  const AnalysisDataPreviewSection({super.key, required this.preview});

  final dynamic preview;

  @override
  Widget build(BuildContext context) {
    final table = normalizeAnalysisPreview(preview);
    if (table == null || table.columns.isEmpty || table.rows.isEmpty) {
      return const Card(
        child: Padding(padding: EdgeInsets.all(16.0), child: Text('无数据预览')),
      );
    }

    return Card(
      elevation: 2,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: DataTable(
            columns: table.columns
                .map(
                  (column) => DataColumn(
                    label: Text(
                      column,
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ),
                )
                .toList(),
            rows: table.rows
                .take(10)
                .map(
                  (row) => DataRow(
                    cells: row
                        .map(
                          (cell) => DataCell(
                            Text(cell, style: const TextStyle(fontSize: 13)),
                          ),
                        )
                        .toList(),
                  ),
                )
                .toList(),
          ),
        ),
      ),
    );
  }
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(fontSize: 14, color: Colors.grey.shade700),
          ),
          Text(
            value,
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
