"""
数据分析服务
使用 Pandas 对用户上传的数据进行分析
"""

import pandas as pd
import numpy as np
import io
from typing import Dict, Any, Optional, List, Tuple
from werkzeug.datastructures import FileStorage
from scipy import stats


def convert_to_json_serializable(obj):
    """
    将 numpy/pandas 类型转换为 JSON 可序列化的 Python 原生类型
    
    Args:
        obj: 需要转换的对象
        
    Returns:
        转换后的对象
    """
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif pd.isna(obj):
        return None
    return obj


class AnalysisService:
    """数据分析服务类"""
    
    @staticmethod
    def analyze_csv(file_stream, filename: str, uid: str) -> Dict[str, Any]:
        """
        分析 CSV 文件并返回统计信息
        
        Args:
            file_stream: 文件流 (FileStorage.stream 或 io.BytesIO)
            filename: 文件名
            uid: 用户ID
            
        Returns:
            dict: 包含分析结果的字典
        """
        try:
            # 直接从内存读取 CSV 文件
            df = pd.read_csv(file_stream)
            
            # 基本信息
            basic_info = {
                'rows': int(df.shape[0]),
                'columns': int(df.shape[1]),
                'column_names': df.columns.tolist(),
                'column_types': {col: str(dtype) for col, dtype in df.dtypes.items()}
            }
            
            # 描述性统计（数值列）
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            descriptive_stats = {}
            
            if numeric_cols:
                desc = df[numeric_cols].describe()
                descriptive_stats = {
                    'statistics': desc.to_dict(),
                    'numeric_columns': numeric_cols
                }
            
            # 缺失值统计
            missing_data = {
                col: {
                    'count': int(df[col].isna().sum()),
                    'percentage': float(df[col].isna().sum() / len(df) * 100)
                }
                for col in df.columns
                if df[col].isna().sum() > 0
            }
            
            # 数据类型分布
            type_distribution = df.dtypes.value_counts().to_dict()
            type_distribution = {str(k): int(v) for k, v in type_distribution.items()}
            
            # 前5行数据预览
            preview_data = df.head(5).to_dict(orient='records')
            
            # 数值列的相关性矩阵（如果有多个数值列）
            correlation_matrix = None
            if len(numeric_cols) > 1:
                corr = df[numeric_cols].corr()
                correlation_matrix = corr.to_dict()
            
            # 组装结果
            result = {
                'success': True,
                'user_id': uid,
                'filename': filename,
                'basic_info': basic_info,
                'descriptive_statistics': descriptive_stats,
                'missing_data': missing_data,
                'type_distribution': type_distribution,
                'preview': preview_data,
                'correlation_matrix': correlation_matrix,
                'message': f'成功分析数据集：{df.shape[0]} 行 x {df.shape[1]} 列'
            }
            
            # 转换所有数据为 JSON 可序列化格式
            result = convert_to_json_serializable(result)
            
            return result
            
        except pd.errors.EmptyDataError:
            return {
                'success': False,
                'error': 'EMPTY_FILE',
                'message': '上传的文件为空'
            }
        except pd.errors.ParserError as e:
            return {
                'success': False,
                'error': 'PARSE_ERROR',
                'message': f'无法解析CSV文件：{str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': 'ANALYSIS_ERROR',
                'message': f'分析过程出错：{str(e)}'
            }
    
    @staticmethod
    def analyze_excel(file_stream, filename: str, uid: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """
        分析 Excel 文件
        
        Args:
            file_stream: 文件流
            filename: 文件名
            uid: 用户ID
            sheet_name: 工作表名称（可选）
            
        Returns:
            dict: 包含分析结果的字典
        """
        try:
            # 读取 Excel 文件
            if sheet_name:
                df = pd.read_excel(file_stream, sheet_name=sheet_name)
            else:
                # 读取第一个工作表
                df = pd.read_excel(file_stream)
            
            # 使用相同的分析逻辑
            # （为了代码复用，可以将分析逻辑提取为独立方法）
            return AnalysisService._perform_analysis(df, uid, filename)
            
        except Exception as e:
            return {
                'success': False,
                'error': 'ANALYSIS_ERROR',
                'message': f'分析Excel文件出错：{str(e)}'
            }
    
    @staticmethod
    def _perform_analysis(df: pd.DataFrame, uid: str, filename: str) -> Dict[str, Any]:
        """
        执行数据分析（内部方法）
        
        Args:
            df: Pandas DataFrame
            uid: 用户ID
            filename: 文件名
            
        Returns:
            dict: 分析结果
        """
        # 基本信息
        basic_info = {
            'rows': int(df.shape[0]),
            'columns': int(df.shape[1]),
            'column_names': df.columns.tolist(),
            'column_types': {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
        
        # 描述性统计
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        descriptive_stats = {}
        
        if numeric_cols:
            desc = df[numeric_cols].describe()
            descriptive_stats = {
                'statistics': desc.to_dict(),
                'numeric_columns': numeric_cols
            }
        
        # 缺失值统计
        missing_data = {
            col: {
                'count': int(df[col].isna().sum()),
                'percentage': float(df[col].isna().sum() / len(df) * 100)
            }
            for col in df.columns
            if df[col].isna().sum() > 0
        }
        
        # 数据类型分布
        type_distribution = df.dtypes.value_counts().to_dict()
        type_distribution = {str(k): int(v) for k, v in type_distribution.items()}
        
        # 前5行预览
        preview_data = df.head(5).to_dict(orient='records')
        
        # 相关性矩阵
        correlation_matrix = None
        if len(numeric_cols) > 1:
            corr = df[numeric_cols].corr()
            correlation_matrix = corr.to_dict()
        
        return convert_to_json_serializable({
            'success': True,
            'user_id': uid,
            'filename': filename,
            'basic_info': basic_info,
            'descriptive_statistics': descriptive_stats,
            'missing_data': missing_data,
            'type_distribution': type_distribution,
            'preview': preview_data,
            'correlation_matrix': correlation_matrix,
            'message': f'成功分析数据集：{df.shape[0]} 行 x {df.shape[1]} 列'
        })
    
    @staticmethod
    def perform_quality_check(df: pd.DataFrame) -> Dict[str, Any]:
        """
        生成详细的数据质量报告
        Phase 1: 数据预处理与质量评估 (Week 03 & Week 13)
        
        Args:
            df: Pandas DataFrame
            
        Returns:
            dict: 包含质量评估结果的字典，包括：
                - missing_analysis: 缺失值分析
                - outlier_detection: 异常值检测
                - duplicate_check: 重复数据检查
                - data_summary: 数据摘要
                - quality_score: 质量分数 (0-100)
        """
        try:
            total_rows = len(df)
            total_cells = df.shape[0] * df.shape[1]
            
            # 1. 缺失值分析 (Week 03: Garbage in, garbage out)
            missing_analysis = {}
            high_risk_columns = []
            total_missing = 0
            
            for col in df.columns:
                missing_count = df[col].isna().sum()
                missing_rate = (missing_count / total_rows * 100) if total_rows > 0 else 0
                
                if missing_count > 0:
                    # 判断缺失机制
                    risk_level = "High Missing Risk" if missing_rate > 5 else "Low Missing Risk"
                    
                    missing_analysis[col] = {
                        'count': int(missing_count),
                        'percentage': float(round(missing_rate, 2)),
                        'risk_level': risk_level
                    }
                    
                    if missing_rate > 5:
                        high_risk_columns.append(col)
                    
                    total_missing += missing_count
            
            # 2. 异常值检测 (Week 03 Mathematical Essence: IQR方法)
            outlier_detection = {}
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            total_outliers = 0
            
            for col in numeric_cols:
                try:
                    # 移除NaN值进行计算
                    col_data = df[col].dropna()
                    
                    if len(col_data) > 0:
                        Q1 = col_data.quantile(0.25)
                        Q3 = col_data.quantile(0.75)
                        IQR = Q3 - Q1
                        
                        # IQR方法：异常值定义为 < Q1 - 1.5*IQR 或 > Q3 + 1.5*IQR
                        lower_bound = Q1 - 1.5 * IQR
                        upper_bound = Q3 + 1.5 * IQR
                        
                        outliers = col_data[(col_data < lower_bound) | (col_data > upper_bound)]
                        outlier_indices = outliers.index.tolist()
                        outlier_count = len(outliers)
                        outlier_ratio = (outlier_count / len(col_data) * 100) if len(col_data) > 0 else 0
                        
                        if outlier_count > 0:
                            outlier_detection[col] = {
                                'count': int(outlier_count),
                                'percentage': float(round(outlier_ratio, 2)),
                                'indices': outlier_indices[:100],  # 限制返回前100个索引
                                'bounds': {
                                    'lower': float(lower_bound),
                                    'upper': float(upper_bound)
                                }
                            }
                            total_outliers += outlier_count
                except Exception as e:
                    outlier_detection[col] = {
                        'error': f'无法计算异常值: {str(e)}'
                    }
            
            # 3. 重复数据检查
            duplicate_rows = df.duplicated()
            duplicate_count = duplicate_rows.sum()
            duplicate_ratio = (duplicate_count / total_rows * 100) if total_rows > 0 else 0
            
            duplicate_check = {
                'count': int(duplicate_count),
                'percentage': float(round(duplicate_ratio, 2)),
                'indices': df[duplicate_rows].index.tolist()[:100]  # 限制返回前100个索引
            }
            
            # 4. 数据摘要 (按列类型)
            data_summary = {
                'numeric_columns': {},
                'categorical_columns': {},
                'datetime_columns': {}
            }
            
            # 数值列摘要：Skewness, Kurtosis
            for col in numeric_cols:
                try:
                    col_data = df[col].dropna()
                    if len(col_data) > 0:
                        data_summary['numeric_columns'][col] = {
                            'mean': float(col_data.mean()),
                            'median': float(col_data.median()),
                            'std': float(col_data.std()),
                            'skewness': float(col_data.skew()),
                            'kurtosis': float(col_data.kurtosis()),
                            'min': float(col_data.min()),
                            'max': float(col_data.max())
                        }
                except Exception as e:
                    data_summary['numeric_columns'][col] = {'error': str(e)}
            
            # 类别列摘要：Unique count, Top values
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            for col in categorical_cols:
                try:
                    value_counts = df[col].value_counts()
                    unique_count = df[col].nunique()
                    
                    data_summary['categorical_columns'][col] = {
                        'unique_count': int(unique_count),
                        'top_values': value_counts.head(5).to_dict(),
                        'most_common': str(value_counts.index[0]) if len(value_counts) > 0 else None
                    }
                except Exception as e:
                    data_summary['categorical_columns'][col] = {'error': str(e)}
            
            # 时间列摘要
            datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
            for col in datetime_cols:
                try:
                    col_data = df[col].dropna()
                    if len(col_data) > 0:
                        data_summary['datetime_columns'][col] = {
                            'min': str(col_data.min()),
                            'max': str(col_data.max()),
                            'range_days': (col_data.max() - col_data.min()).days
                        }
                except Exception as e:
                    data_summary['datetime_columns'][col] = {'error': str(e)}
            
            # 5. 计算质量分数 (0-100)
            # 基于缺失率和异常值比例计算
            missing_penalty = (total_missing / total_cells * 100) if total_cells > 0 else 0
            outlier_penalty = (total_outliers / (total_rows * len(numeric_cols)) * 50) if (total_rows * len(numeric_cols)) > 0 else 0
            duplicate_penalty = duplicate_ratio * 0.5
            
            quality_score = max(0, 100 - missing_penalty - outlier_penalty - duplicate_penalty)
            
            return convert_to_json_serializable({
                'success': True,
                'missing_analysis': missing_analysis,
                'high_risk_columns': high_risk_columns,
                'outlier_detection': outlier_detection,
                'duplicate_check': duplicate_check,
                'data_summary': data_summary,
                'quality_score': round(quality_score, 2),
                'quality_metrics': {
                    'total_cells': total_cells,
                    'total_missing': int(total_missing),
                    'missing_rate': round((total_missing / total_cells * 100) if total_cells > 0 else 0, 2),
                    'total_outliers': int(total_outliers),
                    'duplicate_rows': int(duplicate_count)
                },
                'recommendations': AnalysisService._generate_quality_recommendations(
                    high_risk_columns, duplicate_count, total_outliers
                )
            })
            
        except Exception as e:
            return {
                'success': False,
                'error': 'QUALITY_CHECK_ERROR',
                'message': f'质量检查出错：{str(e)}'
            }
    
    @staticmethod
    def calculate_correlations(df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算变量间的相关性
        Phase 2: 统计分析与相关性 (Week 05: Correlation reveals association)
        
        Args:
            df: Pandas DataFrame
            
        Returns:
            dict: 包含相关性分析结果的字典
        """
        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_cols) < 2:
                return {
                    'success': False,
                    'message': '需要至少2个数值列才能计算相关性'
                }
            
            correlations = []
            high_correlations = []
            
            # 计算Pearson和Spearman相关系数
            for i, var_x in enumerate(numeric_cols):
                for var_y in numeric_cols[i+1:]:
                    try:
                        # 移除缺失值
                        valid_data = df[[var_x, var_y]].dropna()
                        
                        if len(valid_data) > 2:
                            # Pearson相关系数
                            pearson_corr, pearson_p = stats.pearsonr(valid_data[var_x], valid_data[var_y])
                            
                            # Spearman相关系数
                            spearman_corr, spearman_p = stats.spearmanr(valid_data[var_x], valid_data[var_y])
                            
                            corr_data = {
                                'variable_x': var_x,
                                'variable_y': var_y,
                                'pearson': {
                                    'correlation': float(round(pearson_corr, 4)),
                                    'p_value': float(round(pearson_p, 6)),
                                    'significant': pearson_p < 0.05
                                },
                                'spearman': {
                                    'correlation': float(round(spearman_corr, 4)),
                                    'p_value': float(round(spearman_p, 6)),
                                    'significant': spearman_p < 0.05
                                },
                                'n_samples': len(valid_data)
                            }
                            
                            correlations.append(corr_data)
                            
                            # 检测高相关性 (|correlation| > 0.7)
                            if abs(pearson_corr) > 0.7:
                                high_correlations.append({
                                    'variables': [var_x, var_y],
                                    'correlation': float(round(pearson_corr, 4)),
                                    'type': 'positive' if pearson_corr > 0 else 'negative'
                                })
                    
                    except Exception as e:
                        correlations.append({
                            'variable_x': var_x,
                            'variable_y': var_y,
                            'error': f'计算失败: {str(e)}'
                        })
            
            # 生成相关性矩阵（用于热力图）
            pearson_matrix = df[numeric_cols].corr(method='pearson').to_dict()
            spearman_matrix = df[numeric_cols].corr(method='spearman').to_dict()
            
            # 生成建议
            suggestions = AnalysisService._generate_correlation_suggestions(high_correlations)
            
            return convert_to_json_serializable({
                'success': True,
                'correlations': correlations,
                'high_correlations': high_correlations,
                'pearson_matrix': pearson_matrix,
                'spearman_matrix': spearman_matrix,
                'suggestions': suggestions,
                'numeric_columns': numeric_cols
            })
            
        except Exception as e:
            return {
                'success': False,
                'error': 'CORRELATION_ERROR',
                'message': f'相关性计算出错：{str(e)}'
            }
    
    @staticmethod
    def perform_statistical_tests(df: pd.DataFrame) -> Dict[str, Any]:
        """
        执行统计检验
        Phase 2: 分布检验与假设检验 (Week 04 & Week 05)
        
        Args:
            df: Pandas DataFrame
            
        Returns:
            dict: 包含统计检验结果的字典
        """
        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_cols) == 0:
                return {
                    'success': False,
                    'message': '没有数值列可以进行统计检验'
                }
            
            normality_tests = {}
            non_normal_columns = []
            
            # 对每个数值列进行正态性检验 (Week 04 Implementation Tips)
            for col in numeric_cols:
                try:
                    col_data = df[col].dropna()
                    
                    if len(col_data) < 3:
                        normality_tests[col] = {
                            'error': '样本量不足（需要至少3个观测值）'
                        }
                        continue
                    
                    # Shapiro-Wilk检验（适合小样本，n < 5000）
                    if len(col_data) < 5000:
                        statistic, p_value = stats.shapiro(col_data)
                        test_name = 'Shapiro-Wilk'
                    else:
                        # Normaltest (基于偏度和峰度，适合大样本)
                        statistic, p_value = stats.normaltest(col_data)
                        test_name = 'D\'Agostino-Pearson'
                    
                    is_normal = p_value >= 0.05
                    
                    normality_tests[col] = {
                        'test_name': test_name,
                        'statistic': float(round(statistic, 6)),
                        'p_value': float(round(p_value, 6)),
                        'is_normal': is_normal,
                        'distribution': '正态分布' if is_normal else '非正态分布',
                        'n_samples': len(col_data),
                        'skewness': float(round(col_data.skew(), 4)),
                        'kurtosis': float(round(col_data.kurtosis(), 4))
                    }
                    
                    if not is_normal:
                        non_normal_columns.append(col)
                
                except Exception as e:
                    normality_tests[col] = {
                        'error': f'检验失败: {str(e)}'
                    }
            
            # 生成统计建议
            suggestions = AnalysisService._generate_statistical_suggestions(
                non_normal_columns, normality_tests
            )
            
            return convert_to_json_serializable({
                'success': True,
                'normality_tests': normality_tests,
                'non_normal_columns': non_normal_columns,
                'summary': {
                    'total_numeric_columns': len(numeric_cols),
                    'normal_distribution_count': len(numeric_cols) - len(non_normal_columns),
                    'non_normal_distribution_count': len(non_normal_columns)
                },
                'suggestions': suggestions
            })
            
        except Exception as e:
            return {
                'success': False,
                'error': 'STATISTICAL_TEST_ERROR',
                'message': f'统计检验出错：{str(e)}'
            }
    
    @staticmethod
    def _generate_quality_recommendations(high_risk_columns: List[str], 
                                         duplicate_count: int, 
                                         total_outliers: int) -> List[str]:
        """生成数据质量建议"""
        recommendations = []
        
        if high_risk_columns:
            recommendations.append(
                f"警告：发现 {len(high_risk_columns)} 个高缺失风险列 ({', '.join(high_risk_columns)})。"
                f"建议考虑删除这些列或使用插补方法处理缺失值。"
            )
        
        if duplicate_count > 0:
            recommendations.append(
                f"发现 {duplicate_count} 行重复数据。建议检查数据收集流程并删除重复记录。"
            )
        
        if total_outliers > 0:
            recommendations.append(
                f"检测到 {total_outliers} 个异常值。建议进一步调查这些异常值是否为数据错误或真实的极端观测。"
            )
        
        if not recommendations:
            recommendations.append("数据质量良好，未发现明显问题。")
        
        return recommendations
    
    @staticmethod
    def _generate_correlation_suggestions(high_correlations: List[Dict]) -> List[str]:
        """生成相关性分析建议"""
        suggestions = []
        
        for corr in high_correlations:
            var_x, var_y = corr['variables']
            correlation = corr['correlation']
            corr_type = corr['type']
            
            suggestions.append(
                f"发现变量 '{var_x}' 与 '{var_y}' 存在强{corr_type}相关性 (r={correlation:.3f})。"
                f"建议在回归模型中注意多重共线性问题，考虑使用VIF检验或移除其中一个变量。"
            )
        
        if not suggestions:
            suggestions.append("未发现高度相关的变量对。数据特征之间相对独立。")
        
        return suggestions
    
    @staticmethod
    def _generate_statistical_suggestions(non_normal_columns: List[str], 
                                         normality_tests: Dict) -> List[str]:
        """生成统计分析建议"""
        suggestions = []
        
        if non_normal_columns:
            suggestions.append(
                f"发现 {len(non_normal_columns)} 个非正态分布的数值列：{', '.join(non_normal_columns)}。"
            )
            
            # 检查偏度，提供转换建议
            for col in non_normal_columns:
                if col in normality_tests and 'skewness' in normality_tests[col]:
                    skew = normality_tests[col]['skewness']
                    if abs(skew) > 1:
                        suggestions.append(
                            f"列 '{col}' 偏度较高 (skewness={skew:.2f})。"
                            f"建议考虑对数转换或Box-Cox转换来改善正态性。"
                        )
            
            suggestions.append(
                "对于非正态分布的数据，建议："
                "(1) 使用非参数检验方法（如Spearman相关、Mann-Whitney U检验）；"
                "(2) 考虑数据转换；"
                "(3) 使用稳健统计方法。"
            )
        else:
            suggestions.append(
                "所有数值列均符合正态分布假设。可以安全使用参数统计方法（如Pearson相关、t检验）。"
            )
        
        return suggestions
