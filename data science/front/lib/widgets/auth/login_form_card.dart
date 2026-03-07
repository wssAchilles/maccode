/// 登录页表单卡片组件
library;

import 'dart:ui';

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import 'login_header.dart';

class LoginFormCard extends StatelessWidget {
  const LoginFormCard({
    super.key,
    required this.formKey,
    required this.emailController,
    required this.passwordController,
    required this.obscurePassword,
    required this.isLoading,
    required this.onSubmit,
    required this.onGoogleSignIn,
    required this.onTogglePasswordVisibility,
  });

  final GlobalKey<FormState> formKey;
  final TextEditingController emailController;
  final TextEditingController passwordController;
  final bool obscurePassword;
  final bool isLoading;
  final VoidCallback onSubmit;
  final VoidCallback onGoogleSignIn;
  final VoidCallback onTogglePasswordVisibility;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppDecorations.radiusXl),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.85),
            borderRadius: BorderRadius.circular(AppDecorations.radiusXl),
            border: Border.all(
              color: Colors.white.withValues(alpha: 0.3),
              width: 1,
            ),
            boxShadow: AppDecorations.shadowLg,
          ),
          child: Form(
            key: formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const LoginHeader(),
                const SizedBox(height: 40),
                _buildEmailField(),
                const SizedBox(height: 16),
                _buildPasswordField(),
                const SizedBox(height: 32),
                _buildLoginButton(),
                const SizedBox(height: 24),
                _buildDivider(),
                const SizedBox(height: 24),
                _buildGoogleButton(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildEmailField() {
    return TextFormField(
      key: const ValueKey('login-email-field'),
      controller: emailController,
      keyboardType: TextInputType.emailAddress,
      decoration: InputDecoration(
        labelText: '邮箱',
        prefixIcon: const Icon(Icons.email_outlined),
        hintText: 'your@email.com',
        filled: true,
        fillColor: AppColors.surfaceVariant.withValues(alpha: 0.5),
      ),
      validator: (value) {
        if (value == null || value.isEmpty) {
          return '请输入邮箱';
        }
        if (!value.contains('@')) {
          return '请输入有效的邮箱';
        }
        return null;
      },
    );
  }

  Widget _buildPasswordField() {
    return TextFormField(
      key: const ValueKey('login-password-field'),
      controller: passwordController,
      obscureText: obscurePassword,
      decoration: InputDecoration(
        labelText: '密码',
        prefixIcon: const Icon(Icons.lock_outlined),
        hintText: '至少 6 位字符',
        filled: true,
        fillColor: AppColors.surfaceVariant.withValues(alpha: 0.5),
        suffixIcon: IconButton(
          key: const ValueKey('login-password-visibility-button'),
          icon: Icon(
            obscurePassword
                ? Icons.visibility_off_outlined
                : Icons.visibility_outlined,
            color: AppColors.textMuted,
          ),
          onPressed: onTogglePasswordVisibility,
        ),
      ),
      validator: (value) {
        if (value == null || value.isEmpty) {
          return '请输入密码';
        }
        if (value.length < 6) {
          return '密码至少6位';
        }
        return null;
      },
    );
  }

  Widget _buildLoginButton() {
    return SizedBox(
      height: 52,
      child: ElevatedButton(
        key: const ValueKey('login-submit-button'),
        onPressed: isLoading ? null : onSubmit,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.cta,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
          ),
        ),
        child: isLoading
            ? const SizedBox(
                height: 24,
                width: 24,
                child: CircularProgressIndicator(
                  color: Colors.white,
                  strokeWidth: 2.5,
                ),
              )
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.login_rounded, size: 20),
                  const SizedBox(width: 8),
                  Text('登录 / 注册', style: AppTextStyles.button),
                ],
              ),
      ),
    );
  }

  Widget _buildDivider() {
    return Row(
      children: [
        Expanded(child: Divider(color: AppColors.border)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(
            '或',
            style: AppTextStyles.bodySmall.copyWith(color: AppColors.textMuted),
          ),
        ),
        Expanded(child: Divider(color: AppColors.border)),
      ],
    );
  }

  Widget _buildGoogleButton() {
    return SizedBox(
      height: 52,
      child: OutlinedButton(
        key: const ValueKey('login-google-button'),
        onPressed: isLoading ? null : onGoogleSignIn,
        style: OutlinedButton.styleFrom(
          side: BorderSide(color: AppColors.border),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const _GoogleBadge(),
            const SizedBox(width: 12),
            Text(
              '使用 Google 账号登录',
              style: AppTextStyles.button.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GoogleBadge extends StatelessWidget {
  const _GoogleBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 22,
      height: 22,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(11),
        border: Border.all(color: AppColors.border),
      ),
      child: Text(
        'G',
        style: AppTextStyles.labelLarge.copyWith(
          fontWeight: FontWeight.w700,
          color: const Color(0xFF4285F4),
        ),
      ),
    );
  }
}
