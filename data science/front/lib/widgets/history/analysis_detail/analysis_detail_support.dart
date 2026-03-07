library;

import 'package:flutter/material.dart';

Map<String, dynamic>? analysisDetailAsMap(dynamic value) {
  if (value is Map<String, dynamic>) {
    return value;
  }

  if (value is Map) {
    return value.map((key, mapValue) => MapEntry(key.toString(), mapValue));
  }

  return null;
}

List<dynamic> analysisDetailAsList(dynamic value) {
  if (value is List) {
    return value;
  }

  return const [];
}

List<String> analysisDetailAsStringList(dynamic value) {
  return analysisDetailAsList(value).map((item) => item.toString()).toList();
}

double? analysisDetailAsNum(dynamic value) {
  if (value is num) {
    return value.toDouble();
  }

  if (value is String) {
    return double.tryParse(value);
  }

  return null;
}

String analysisDetailStringValue(dynamic value) {
  final text = value?.toString();
  if (text == null || text.isEmpty) {
    return '-';
  }
  return text;
}

Color analysisDetailQualityColor(double score) {
  if (score >= 90) return Colors.green;
  if (score >= 70) return Colors.orange;
  return Colors.red;
}

String analysisDetailQualityLabel(double score) {
  if (score >= 90) return '优秀';
  if (score >= 70) return '良好';
  if (score >= 50) return '一般';
  return '较差';
}

Color analysisDetailCorrelationColor(double correlation) {
  final abs = correlation.abs();
  if (abs >= 0.7) return Colors.red;
  if (abs >= 0.5) return Colors.orange;
  return Colors.blue;
}

class AnalysisCorrelationEntry {
  const AnalysisCorrelationEntry({
    required this.label,
    required this.correlation,
  });

  final String label;
  final double correlation;
}

List<AnalysisCorrelationEntry> buildAnalysisCorrelationEntries(
  Map<String, dynamic> correlationAnalysis,
) {
  final highCorrelations = analysisDetailAsList(
    correlationAnalysis['high_correlations'],
  );
  if (highCorrelations.isNotEmpty) {
    return highCorrelations
        .map(_buildEntryFromHighCorrelation)
        .whereType<AnalysisCorrelationEntry>()
        .toList();
  }

  final correlations = analysisDetailAsList(
    correlationAnalysis['correlations'],
  );
  return correlations
      .map(_buildEntryFromCorrelation)
      .whereType<AnalysisCorrelationEntry>()
      .toList();
}

AnalysisCorrelationEntry? _buildEntryFromHighCorrelation(dynamic value) {
  final pair = analysisDetailAsMap(value);
  if (pair == null) return null;

  final variables = analysisDetailAsStringList(pair['variables']);
  final label = variables.length >= 2
      ? '${variables[0]} ↔ ${variables[1]}'
      : '${analysisDetailStringValue(pair['column1'])} ↔ ${analysisDetailStringValue(pair['column2'])}';
  final correlation = analysisDetailAsNum(pair['correlation']);

  if (label == '- ↔ -' || correlation == null) {
    return null;
  }

  return AnalysisCorrelationEntry(label: label, correlation: correlation);
}

AnalysisCorrelationEntry? _buildEntryFromCorrelation(dynamic value) {
  final pair = analysisDetailAsMap(value);
  if (pair == null) return null;

  final variableX = analysisDetailStringValue(pair['variable_x']);
  final variableY = analysisDetailStringValue(pair['variable_y']);
  final pearson = analysisDetailAsMap(pair['pearson']);
  final correlation = analysisDetailAsNum(pearson?['correlation']);

  if (variableX == '-' || variableY == '-' || correlation == null) {
    return null;
  }

  return AnalysisCorrelationEntry(
    label: '$variableX ↔ $variableY',
    correlation: correlation,
  );
}

class AnalysisPreviewTableData {
  const AnalysisPreviewTableData({required this.columns, required this.rows});

  final List<String> columns;
  final List<List<String>> rows;
}

AnalysisPreviewTableData? normalizeAnalysisPreview(dynamic value) {
  if (value is Map) {
    final preview = analysisDetailAsMap(value);
    final columns = analysisDetailAsStringList(preview?['columns']);
    final data = analysisDetailAsList(preview?['data']);
    final rows = data
        .whereType<List>()
        .map(
          (row) => row.map((cell) => analysisDetailStringValue(cell)).toList(),
        )
        .toList();

    if (columns.isNotEmpty && rows.isNotEmpty) {
      return AnalysisPreviewTableData(columns: columns, rows: rows);
    }
  }

  if (value is List) {
    final rowMaps = value.whereType<Map>().toList();
    if (rowMaps.isEmpty) return null;

    final columns = rowMaps.first.keys.map((key) => key.toString()).toList();
    final rows = rowMaps
        .map(
          (row) => columns
              .map((column) => analysisDetailStringValue(row[column]))
              .toList(),
        )
        .toList();

    return AnalysisPreviewTableData(columns: columns, rows: rows);
  }

  return null;
}
