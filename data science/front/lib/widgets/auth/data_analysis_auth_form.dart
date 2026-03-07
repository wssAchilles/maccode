/// 数据分析页面登录/注册表单组件
/// 从 DataAnalysisScreen 抽离，降低页面复杂度并提高可测试性
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../common/glass_card.dart';

class DataAnalysisAuthForm extends StatelessWidget {
  const DataAnalysisAuthForm({
    super.key,
    required this.formKey,
    required this.emailController,
    required this.passwordController,
    required this.authMode,
    required this.onSignInWithEmail,
    required this.onRegisterWithEmail,
    required this.onToggleAuthMode,
    required this.onGoogleSignIn,
  });

  final GlobalKey<FormState> formKey;
  final TextEditingController emailController;
  final TextEditingController passwordController;
  final String authMode;
  final VoidCallback onSignInWithEmail;
  final VoidCallback onRegisterWithEmail;
  final VoidCallback onToggleAuthMode;
  final VoidCallback onGoogleSignIn;

  @override
  Widget build(BuildContext context) {
    final isLogin = authMode == 'login';

    return GlassCard(
      child: Form(
        key: formKey,
        child: Column(
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                gradient: AppColors.primaryGradient,
                borderRadius: BorderRadius.circular(AppDecorations.radiusXl),
              ),
              child: const Icon(
                Icons.person_rounded,
                size: 40,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              isLogin ? '登录以使用数据分析服务' : '注册新账户',
              style: AppTextStyles.h3,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            TextFormField(
              controller: emailController,
              keyboardType: TextInputType.emailAddress,
              decoration: InputDecoration(
                labelText: '邮箱',
                hintText: 'your@email.com',
                prefixIcon: const Icon(Icons.email_outlined),
                filled: true,
                fillColor: AppColors.surfaceVariant,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                  borderSide: BorderSide.none,
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                  borderSide: const BorderSide(
                    color: AppColors.primary,
                    width: 2,
                  ),
                ),
              ),
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return '请输入邮箱';
                }
                if (!value.contains('@')) {
                  return '邮箱格式不正确';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: passwordController,
              obscureText: true,
              decoration: InputDecoration(
                labelText: '密码',
                hintText: '至少6位字符',
                prefixIcon: const Icon(Icons.lock_outline_rounded),
                filled: true,
                fillColor: AppColors.surfaceVariant,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                  borderSide: BorderSide.none,
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                  borderSide: const BorderSide(
                    color: AppColors.primary,
                    width: 2,
                  ),
                ),
              ),
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return '请输入密码';
                }
                if (value.length < 6) {
                  return '密码至少需要6位字符';
                }
                return null;
              },
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed: isLogin ? onSignInWithEmail : onRegisterWithEmail,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.cta,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(
                      AppDecorations.radiusMd,
                    ),
                  ),
                  elevation: 0,
                ),
                child: Text(isLogin ? '登录' : '注册', style: AppTextStyles.button),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  isLogin ? '还没有账户？' : '已有账户？',
                  style: AppTextStyles.bodySmall,
                ),
                TextButton(
                  onPressed: onToggleAuthMode,
                  child: Text(
                    isLogin ? '立即注册' : '返回登录',
                    style: AppTextStyles.labelLarge.copyWith(
                      color: AppColors.primary,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(child: Divider(color: AppColors.border)),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Text('或', style: AppTextStyles.bodySmall),
                ),
                Expanded(child: Divider(color: AppColors.border)),
              ],
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: OutlinedButton.icon(
                onPressed: onGoogleSignIn,
                icon: const Icon(Icons.g_mobiledata_rounded, size: 24),
                label: const Text('使用 Google 登录'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.textPrimary,
                  side: const BorderSide(color: AppColors.border),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(
                      AppDecorations.radiusMd,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
