# API 集成示例

## 在 Flask API 中使用增强分析功能

### 1. 添加新的 API 端点

在 `back/main.py` 或相应的路由文件中添加以下端点：

```python
from flask import Flask, request, jsonify
from services.analysis_service import AnalysisService
import pandas as pd
import io

app = Flask(__name__)

@app.route('/api/data/quality-check', methods=['POST'])
def quality_check():
    """
    数据质量检查端点
    
    接收上传的文件或 DataFrame，返回质量报告
    """
    try:
        # 从请求中获取文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '未找到上传文件'
            }), 400
        
        file = request.files['file']
        
        # 读取数据
        df = pd.read_csv(file.stream)
        
        # 执行质量检查
        result = AnalysisService.perform_quality_check(df)
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'QUALITY_CHECK_ERROR',
            'message': str(e)
        }), 500


@app.route('/api/data/correlations', methods=['POST'])
def calculate_correlations():
    """
    相关性分析端点
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '未找到上传文件'
            }), 400
        
        file = request.files['file']
        df = pd.read_csv(file.stream)
        
        # 执行相关性分析
        result = AnalysisService.calculate_correlations(df)
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'CORRELATION_ERROR',
            'message': str(e)
        }), 500


@app.route('/api/data/statistical-tests', methods=['POST'])
def statistical_tests():
    """
    统计检验端点
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '未找到上传文件'
            }), 400
        
        file = request.files['file']
        df = pd.read_csv(file.stream)
        
        # 执行统计检验
        result = AnalysisService.perform_statistical_tests(df)
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'STATISTICAL_TEST_ERROR',
            'message': str(e)
        }), 500


@app.route('/api/data/comprehensive-analysis', methods=['POST'])
def comprehensive_analysis():
    """
    综合分析端点 - 一次性执行所有分析
    
    这是推荐的方式，可以减少文件上传次数
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '未找到上传文件'
            }), 400
        
        file = request.files['file']
        df = pd.read_csv(file.stream)
        
        # 执行所有分析
        quality_result = AnalysisService.perform_quality_check(df)
        correlation_result = AnalysisService.calculate_correlations(df)
        statistical_result = AnalysisService.perform_statistical_tests(df)
        
        # 基本信息（复用现有逻辑）
        basic_analysis = AnalysisService._perform_analysis(df, 
                                                          request.form.get('user_id', 'anonymous'),
                                                          file.filename)
        
        # 组合所有结果
        comprehensive_result = {
            'success': True,
            'basic_analysis': basic_analysis,
            'quality_check': quality_result,
            'correlations': correlation_result,
            'statistical_tests': statistical_result,
            'overall_summary': {
                'data_shape': f"{df.shape[0]} 行 x {df.shape[1]} 列",
                'quality_score': quality_result.get('quality_score', None),
                'high_correlations_count': len(correlation_result.get('high_correlations', [])),
                'non_normal_columns_count': len(statistical_result.get('non_normal_columns', []))
            }
        }
        
        return jsonify(comprehensive_result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'COMPREHENSIVE_ANALYSIS_ERROR',
            'message': str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

---

## 2. 前端调用示例

### JavaScript/React 示例

```javascript
// 质量检查
async function checkDataQuality(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await fetch('/api/data/quality-check', {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    
    if (result.success) {
      console.log(`质量分数: ${result.quality_score}/100`);
      console.log('建议:', result.recommendations);
      
      // 显示结果到UI
      displayQualityReport(result);
    } else {
      console.error('质量检查失败:', result.message);
    }
  } catch (error) {
    console.error('请求失败:', error);
  }
}

// 综合分析（推荐）
async function comprehensiveAnalysis(file, userId) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_id', userId);
  
  try {
    const response = await fetch('/api/data/comprehensive-analysis', {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    
    if (result.success) {
      // 显示基本信息
      displayBasicInfo(result.basic_analysis);
      
      // 显示质量报告
      displayQualityReport(result.quality_check);
      
      // 显示相关性矩阵
      displayCorrelationMatrix(result.correlations);
      
      // 显示统计检验结果
      displayStatisticalTests(result.statistical_tests);
      
      // 显示总体摘要
      displaySummary(result.overall_summary);
    }
  } catch (error) {
    console.error('分析失败:', error);
  }
}

// UI 显示函数示例
function displayQualityReport(qualityData) {
  // 质量分数
  document.getElementById('quality-score').textContent = 
    `${qualityData.quality_score}/100`;
  
  // 高风险列
  const riskList = document.getElementById('high-risk-columns');
  qualityData.high_risk_columns.forEach(col => {
    const li = document.createElement('li');
    li.textContent = col;
    li.className = 'text-red-600';
    riskList.appendChild(li);
  });
  
  // 建议
  const recommendationsList = document.getElementById('recommendations');
  qualityData.recommendations.forEach(rec => {
    const li = document.createElement('li');
    li.textContent = rec;
    recommendationsList.appendChild(li);
  });
}
```

---

## 3. 使用 Axios 的示例

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  headers: {
    'Content-Type': 'multipart/form-data',
  }
});

// 质量检查
export const checkDataQuality = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/data/quality-check', formData);
  return response.data;
};

// 相关性分析
export const calculateCorrelations = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/data/correlations', formData);
  return response.data;
};

// 统计检验
export const performStatisticalTests = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/data/statistical-tests', formData);
  return response.data;
};

// 综合分析
export const comprehensiveAnalysis = async (file, userId) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_id', userId);
  
  const response = await api.post('/data/comprehensive-analysis', formData);
  return response.data;
};

// React 组件中使用
import React, { useState } from 'react';
import { comprehensiveAnalysis } from './api';

function DataAnalysisComponent() {
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    setLoading(true);
    try {
      const result = await comprehensiveAnalysis(file, 'user123');
      setAnalysisResult(result);
    } catch (error) {
      console.error('分析失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="p-4">
      <input 
        type="file" 
        accept=".csv"
        onChange={handleFileUpload}
        disabled={loading}
      />
      
      {loading && <div>分析中...</div>}
      
      {analysisResult && (
        <div className="mt-4">
          <h2 className="text-2xl font-bold mb-4">分析结果</h2>
          
          {/* 质量分数 */}
          <div className="mb-4">
            <h3 className="text-xl font-semibold">数据质量</h3>
            <p className="text-3xl text-blue-600">
              {analysisResult.quality_check.quality_score}/100
            </p>
          </div>
          
          {/* 高风险列 */}
          {analysisResult.quality_check.high_risk_columns.length > 0 && (
            <div className="mb-4 p-4 bg-red-50 rounded">
              <h4 className="font-semibold text-red-700">高风险列</h4>
              <ul className="list-disc list-inside">
                {analysisResult.quality_check.high_risk_columns.map(col => (
                  <li key={col} className="text-red-600">{col}</li>
                ))}
              </ul>
            </div>
          )}
          
          {/* 建议 */}
          <div className="mb-4">
            <h4 className="font-semibold">建议</h4>
            <ul className="list-disc list-inside">
              {analysisResult.quality_check.recommendations.map((rec, idx) => (
                <li key={idx}>{rec}</li>
              ))}
            </ul>
          </div>
          
          {/* 相关性 */}
          {analysisResult.correlations.high_correlations.length > 0 && (
            <div className="mb-4 p-4 bg-yellow-50 rounded">
              <h4 className="font-semibold text-yellow-700">高相关性变量</h4>
              {analysisResult.correlations.high_correlations.map((corr, idx) => (
                <div key={idx}>
                  {corr.variables[0]} ↔️ {corr.variables[1]}: r={corr.correlation}
                </div>
              ))}
            </div>
          )}
          
          {/* 非正态分布列 */}
          {analysisResult.statistical_tests.non_normal_columns.length > 0 && (
            <div className="mb-4 p-4 bg-blue-50 rounded">
              <h4 className="font-semibold text-blue-700">非正态分布列</h4>
              <p>{analysisResult.statistical_tests.non_normal_columns.join(', ')}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default DataAnalysisComponent;
```

---

## 4. cURL 测试命令

```bash
# 质量检查
curl -X POST http://localhost:5000/api/data/quality-check \
  -F "file=@your_data.csv"

# 相关性分析
curl -X POST http://localhost:5000/api/data/correlations \
  -F "file=@your_data.csv"

# 统计检验
curl -X POST http://localhost:5000/api/data/statistical-tests \
  -F "file=@your_data.csv"

# 综合分析
curl -X POST http://localhost:5000/api/data/comprehensive-analysis \
  -F "file=@your_data.csv" \
  -F "user_id=user123"
```

---

## 5. 错误处理最佳实践

```javascript
async function safeAnalysis(file) {
  try {
    const result = await comprehensiveAnalysis(file, 'user123');
    
    // 检查成功状态
    if (!result.success) {
      throw new Error(result.message || '分析失败');
    }
    
    // 检查质量分数
    if (result.quality_check.quality_score < 50) {
      console.warn('数据质量较差，建议先清洗数据');
      showWarning(result.quality_check.recommendations);
    }
    
    // 检查相关性问题
    if (result.correlations.high_correlations.length > 0) {
      console.warn('发现多重共线性问题');
      showWarning(result.correlations.suggestions);
    }
    
    return result;
    
  } catch (error) {
    console.error('分析出错:', error);
    
    // 用户友好的错误消息
    if (error.response?.status === 400) {
      showError('请上传有效的 CSV 文件');
    } else if (error.response?.status === 500) {
      showError('服务器错误，请稍后重试');
    } else {
      showError('网络错误，请检查连接');
    }
    
    throw error;
  }
}
```

---

## 6. 性能优化建议

1. **缓存结果**：对于同一文件，可以缓存分析结果
2. **异步处理**：对于大文件，使用后台任务处理
3. **分页返回**：对于异常值索引等大量数据，考虑分页
4. **WebSocket**：使用 WebSocket 推送实时分析进度

```python
# 使用 Celery 进行异步处理示例
from celery import Celery

celery = Celery('tasks', broker='redis://localhost:6379/0')

@celery.task
def async_comprehensive_analysis(file_path, user_id):
    df = pd.read_csv(file_path)
    
    quality_result = AnalysisService.perform_quality_check(df)
    correlation_result = AnalysisService.calculate_correlations(df)
    statistical_result = AnalysisService.perform_statistical_tests(df)
    
    # 保存结果到数据库或缓存
    save_analysis_result(user_id, {
        'quality_check': quality_result,
        'correlations': correlation_result,
        'statistical_tests': statistical_result
    })
    
    return {'status': 'completed'}
```

---

## 7. 部署到 GAE 注意事项

确保 `back/requirements.txt` 包含 scipy：

```txt
scipy==1.11.4
```

在 `app.yaml` 中确保有足够的内存：

```yaml
runtime: python311
instance_class: F2  # 增加实例大小以支持 scipy

automatic_scaling:
  min_instances: 0
  max_instances: 5
```

---

## 总结

这些新增的分析功能可以轻松集成到现有的 Flask 后端中，为用户提供：

1. **实时数据质量评估**
2. **自动化的统计检验**
3. **智能的相关性分析**
4. **可操作的建议和警告**

建议使用 `/api/data/comprehensive-analysis` 端点进行一次性完整分析，以减少网络请求和文件上传次数。
