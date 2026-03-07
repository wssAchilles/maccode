/// 数据分析结果展示组件
/// 将复杂结果渲染从页面中抽离，降低屏幕层复杂度。
library;

import 'package:flutter/material.dart';

import '../../models/analysis_result.dart';
import 'correlation_matrix_view.dart';
import 'quality_dashboard.dart';
import 'statistical_panel.dart';

part 'analysis_results/analysis_results_cards.dart';
part 'analysis_results/analysis_results_section_view.dart';
