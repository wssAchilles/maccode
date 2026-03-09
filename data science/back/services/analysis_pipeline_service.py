"""Shared CSV analysis pipeline for sync and job-based execution."""

from __future__ import annotations

import io
import logging
import time
from typing import Any, Callable, Dict, Optional

import pandas as pd

from services.analysis_service import AnalysisService
from services.history_service import HistoryService
from services.storage_service import StorageService
from utils.exceptions import ValidationError
from utils.validators import validate_file_size

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, str, str], None]


class AnalysisPipelineService:
    @classmethod
    def run_csv_analysis(
        cls,
        *,
        uid: str,
        storage_path: str,
        filename: Optional[str] = None,
        save_to_storage: bool = True,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        if not storage_path:
            raise ValidationError('缺少参数：storage_path')

        filename = filename or storage_path.split('/')[-1]
        storage = StorageService()

        cls._emit(progress_callback, 15, 'Loading CSV from Cloud Storage', 'dataset')
        if not storage.file_exists(storage_path):
            raise ValidationError('文件不存在')

        start_time = time.time()
        file_bytes = storage.download_file(storage_path)
        file_size = len(file_bytes)
        if not validate_file_size(file_size, max_size_mb=50):
            raise ValidationError('文件大小不能超过 50MB')

        file_stream = io.BytesIO(file_bytes)
        df = pd.read_csv(file_stream)
        load_time = time.time() - start_time
        logger.info('[%s] Data loaded in %.2fs, shape=%s', uid, load_time, df.shape)

        cls._emit(progress_callback, 35, 'Running schema and preview analysis', 'basic_analysis')
        basic_start = time.time()
        basic_result = AnalysisService.analyze_dataframe(df, filename, uid)
        basic_time = time.time() - basic_start
        if not basic_result.get('success'):
            raise RuntimeError(basic_result.get('message') or '基础分析失败')

        quality_analysis = cls._run_optional_stage(
            uid=uid,
            phase='quality',
            progress=55,
            message='Evaluating data quality risks',
            callback=lambda: AnalysisService.perform_quality_check(df),
            error_code='QUALITY_CHECK_ERROR',
            error_message='质量检查失败',
            progress_callback=progress_callback,
        )

        correlations = cls._run_optional_stage(
            uid=uid,
            phase='correlation',
            progress=70,
            message='Computing feature correlations',
            callback=lambda: AnalysisService.calculate_correlations(df),
            error_code='CORRELATION_ERROR',
            error_message='相关性分析失败',
            progress_callback=progress_callback,
        )

        statistical_tests = cls._run_optional_stage(
            uid=uid,
            phase='statistical',
            progress=84,
            message='Running statistical tests',
            callback=lambda: AnalysisService.perform_statistical_tests(df),
            error_code='STATISTICAL_TEST_ERROR',
            error_message='统计检验失败',
            progress_callback=progress_callback,
        )

        analysis_result = {
            'basic_info': basic_result.get('basic_info', {}),
            'preview': basic_result.get('preview', []),
            'descriptive_statistics': basic_result.get('descriptive_statistics', {}),
            'missing_data': basic_result.get('missing_data', {}),
            'type_distribution': basic_result.get('type_distribution', {}),
            'correlation_matrix': basic_result.get('correlation_matrix'),
            'quality_analysis': quality_analysis,
            'correlations': correlations,
            'statistical_tests': statistical_tests,
        }

        cls._emit(progress_callback, 92, 'Persisting history and asset retention state', 'history_archive')
        record_id = None
        if save_to_storage:
            try:
                storage_url = f'gs://{storage.bucket_name}/{storage_path}'
                record_id = HistoryService.save_analysis_record(
                    uid=uid,
                    filename=filename,
                    storage_url=storage_url,
                    analysis_result=analysis_result,
                )
            except Exception as exc:
                logger.error('[%s] Failed to save analysis history: %s', uid, exc, exc_info=True)
        else:
            try:
                storage.delete_file(storage_path)
                logger.info('[%s] Deleted temporary analysis file: %s', uid, storage_path)
            except Exception as exc:
                logger.warning('[%s] Failed to delete temporary analysis file: %s', uid, exc)

        total_time = time.time() - start_time
        cls._emit(progress_callback, 97, 'Packaging analysis payload', 'packaging')

        return {
            'success': True,
            'analysis_result': analysis_result,
            'message': '分析完成',
            'storage_path': storage_path,
            'storage_retained': save_to_storage,
            'history_record_id': record_id,
            'performance': {
                'load_time': round(load_time, 2),
                'basic_analysis_time': round(basic_time, 2),
                'total_time': round(total_time, 2),
            },
        }

    @classmethod
    def _run_optional_stage(
        cls,
        *,
        uid: str,
        phase: str,
        progress: int,
        message: str,
        callback: Callable[[], Dict[str, Any]],
        error_code: str,
        error_message: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        try:
            cls._emit(progress_callback, progress, message, phase)
            started = time.time()
            result = callback()
            elapsed = time.time() - started
            logger.info('[%s] %s completed in %.2fs', uid, phase, elapsed)
            if result.get('success'):
                return result
            return {
                'success': False,
                'error': result.get('error', 'UNKNOWN'),
                'message': result.get('message', error_message),
            }
        except Exception as exc:
            logger.warning('[%s] %s failed: %s', uid, phase, exc)
            return {
                'success': False,
                'error': error_code,
                'message': f'{error_message}: {exc}',
            }

    @staticmethod
    def _emit(
        callback: Optional[ProgressCallback],
        progress: int,
        message: str,
        phase: str,
    ) -> None:
        if callback is not None:
            callback(progress, message, phase)
