/// 文件选择器组件 - 从 DataAnalysisScreen 提取
/// 【性能优化】独立组件减少不必要的重建
library;

import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../../config/app_theme.dart';
import '../common/glass_card.dart';

/// 文件选择器回调类型
typedef OnFileSelected = void Function(PlatformFile file);
typedef OnFileClear = void Function();
typedef OnStorageOptionChanged = void Function(bool value);

/// 文件选择器组件
class FilePickerWidget extends StatelessWidget {
  final PlatformFile? selectedFile;
  final bool isLoggedIn;
  final bool saveToStorage;
  final VoidCallback onPickFile;
  final OnFileClear onClearFile;
  final OnStorageOptionChanged onStorageChanged;

  const FilePickerWidget({
    super.key,
    this.selectedFile,
    required this.isLoggedIn,
    required this.saveToStorage,
    required this.onPickFile,
    required this.onClearFile,
    required this.onStorageChanged,
  });

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题行
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: const Icon(
                  Icons.upload_file_rounded,
                  color: AppColors.primary,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Text('选择 CSV 文件', style: AppTextStyles.h4),
            ],
          ),
          const SizedBox(height: 16),

          // 拖放区域或已选文件
          if (selectedFile == null) _buildDropZone() else _buildSelectedFile(),
        ],
      ),
    );
  }

  Widget _buildDropZone() {
    return DropZoneContainer(
      onTap: isLoggedIn ? onPickFile : null,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.cloud_upload_outlined,
              size: 48,
              color: isLoggedIn ? AppColors.primary : AppColors.textMuted,
            ),
            const SizedBox(height: 12),
            Text(
              isLoggedIn ? '点击选择文件' : '先完成登录后上传',
              style: AppTextStyles.bodyMedium.copyWith(
                color: isLoggedIn ? AppColors.primary : AppColors.textMuted,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              isLoggedIn ? '仅支持 CSV 格式' : '登录后将自动启用 CSV 文件选择',
              style: AppTextStyles.bodySmall,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSelectedFile() {
    return Column(
      children: [
        // 文件信息
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.successLight,
            borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            border: Border.all(color: AppColors.success.withValues(alpha: 0.3)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.success.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusSm),
                ),
                child: const Icon(
                  Icons.description_rounded,
                  color: AppColors.success,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      selectedFile!.name,
                      style: AppTextStyles.labelLarge,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      '${(selectedFile!.size / 1024).toStringAsFixed(2)} KB',
                      style: AppTextStyles.bodySmall,
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close_rounded, size: 20),
                onPressed: onClearFile,
                style: IconButton.styleFrom(
                  backgroundColor: AppColors.error.withValues(alpha: 0.1),
                  foregroundColor: AppColors.error,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        // 存储选项
        _buildStorageOption(),
      ],
    );
  }

  Widget _buildStorageOption() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Row(
        children: [
          Checkbox(
            value: saveToStorage,
            onChanged: (value) => onStorageChanged(value ?? true),
            activeColor: AppColors.primary,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('保存到 Cloud Storage', style: AppTextStyles.labelMedium),
                Text('将文件归档以便日后查看', style: AppTextStyles.bodySmall),
              ],
            ),
          ),
          const Icon(
            Icons.cloud_outlined,
            color: AppColors.textMuted,
            size: 20,
          ),
        ],
      ),
    );
  }
}
