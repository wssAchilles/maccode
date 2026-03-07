/// 电池电量变化图表
/// 展示 SOC 趋势和电价时段
library;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../models/optimization_result.dart';
import '../utils/responsive_helper.dart';

part 'soc/soc_chart_view.dart';
part 'soc/soc_chart_helpers.dart';
part 'soc/soc_chart_legend.dart';
