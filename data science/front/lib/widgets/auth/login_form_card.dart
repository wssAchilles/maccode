/// 登录页表单卡片组件
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';

class LoginFormCard extends StatefulWidget {
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
  State<LoginFormCard> createState() => _LoginFormCardState();
}

class _LoginFormCardState extends State<LoginFormCard> {
  bool _staySignedIn = false;

  @override
  Widget build(BuildContext context) {
    final isCompact = MediaQuery.sizeOf(context).width < 940;
    return Container(
      padding: EdgeInsets.fromLTRB(
        isCompact ? 28 : 48,
        isCompact ? 28 : 54,
        isCompact ? 28 : 42,
        isCompact ? 30 : 42,
      ),
      alignment: Alignment.center,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 360),
        child: Form(
          key: widget.formKey,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                '欢迎回来',
                style: AppTextStyles.headingFont.copyWith(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: const Color(0xFF1B2730),
                ),
              ),
              const SizedBox(height: 10),
              Text(
                '输入你的账号信息以访问智能能源控制台。',
                style: AppTextStyles.bodyFont.copyWith(
                  fontSize: 15,
                  height: 1.55,
                  color: const Color(0xFF5B6774),
                ),
              ),
              const SizedBox(height: 28),
              _buildFieldLabel('工作邮箱'),
              const SizedBox(height: 10),
              _buildEmailField(),
              const SizedBox(height: 18),
              Row(
                children: [
                  Expanded(child: _buildFieldLabel('安全密码')),
                  Text(
                    '忘记密码？',
                    style: AppTextStyles.bodyFont.copyWith(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: const Color(0xFF5285F6),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              _buildPasswordField(),
              const SizedBox(height: 14),
              _buildRememberRow(),
              const SizedBox(height: 24),
              _buildLoginButton(),
              const SizedBox(height: 26),
              _buildDivider(),
              const SizedBox(height: 24),
              _buildGoogleButton(),
              const SizedBox(height: 26),
              Center(
                child: Text.rich(
                  TextSpan(
                    style: AppTextStyles.bodyFont.copyWith(
                      fontSize: 14,
                      color: const Color(0xFF6B7785),
                    ),
                    children: [
                      const TextSpan(text: '新运营者？'),
                      TextSpan(
                        text: '申请平台访问',
                        style: AppTextStyles.bodyFont.copyWith(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: const Color(0xFFB75A09),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFieldLabel(String label) {
    return Text(
      label,
      style: AppTextStyles.bodyFont.copyWith(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.8,
        color: const Color(0xFF5A6673),
      ),
    );
  }

  Widget _buildEmailField() {
    return TextFormField(
      key: const ValueKey('login-email-field'),
      controller: widget.emailController,
      keyboardType: TextInputType.emailAddress,
      decoration: InputDecoration(
        hintText: '请输入企业邮箱',
        prefixIcon: const Icon(Icons.mail_outline_rounded),
        filled: true,
        fillColor: const Color(0xFFEAF3FF),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 18,
          vertical: 18,
        ),
        border: _inputBorder,
        enabledBorder: _inputBorder,
        focusedBorder: _focusedInputBorder,
        errorBorder: _inputBorder.copyWith(
          borderSide: const BorderSide(color: Color(0xFFE36D6D)),
        ),
        focusedErrorBorder: _focusedInputBorder.copyWith(
          borderSide: const BorderSide(color: Color(0xFFE36D6D)),
        ),
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
      controller: widget.passwordController,
      obscureText: widget.obscurePassword,
      decoration: InputDecoration(
        hintText: '输入至少 6 位密码',
        prefixIcon: const Icon(Icons.lock_outline_rounded),
        filled: true,
        fillColor: const Color(0xFFEAF3FF),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 18,
          vertical: 18,
        ),
        border: _inputBorder,
        enabledBorder: _inputBorder,
        focusedBorder: _focusedInputBorder,
        suffixIcon: IconButton(
          key: const ValueKey('login-password-visibility-button'),
          icon: Icon(
            widget.obscurePassword
                ? Icons.visibility_off_outlined
                : Icons.visibility_outlined,
            color: const Color(0xFF657180),
          ),
          onPressed: widget.onTogglePasswordVisibility,
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

  Widget _buildRememberRow() {
    return Row(
      children: [
        Transform.scale(
          scale: 0.92,
          child: Checkbox(
            value: _staySignedIn,
            onChanged: (value) {
              setState(() {
                _staySignedIn = value ?? false;
              });
            },
            side: const BorderSide(color: Color(0xFFD5DFEC)),
            fillColor: WidgetStateProperty.resolveWith((states) {
              if (states.contains(WidgetState.selected)) {
                return const Color(0xFF4A92FD);
              }
              return Colors.transparent;
            }),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(5),
            ),
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            '30 天内保持登录状态',
            style: AppTextStyles.bodyFont.copyWith(
              fontSize: 14,
              color: const Color(0xFF51606D),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildLoginButton() {
    return SizedBox(
      height: 56,
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
            colors: [Color(0xFFB75A09), Color(0xFFFF7A1A)],
          ),
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFFCF7B2F).withValues(alpha: 0.25),
              blurRadius: 18,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: ElevatedButton(
          key: const ValueKey('login-submit-button'),
          onPressed: widget.isLoading ? null : widget.onSubmit,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.transparent,
            disabledBackgroundColor: Colors.transparent,
            shadowColor: Colors.transparent,
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
          child: widget.isLoading
              ? const SizedBox(
                  height: 24,
                  width: 24,
                  child: CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2.5,
                  ),
                )
              : Text(
                  '登录',
                  style: AppTextStyles.bodyFont.copyWith(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                  ),
                ),
        ),
      ),
    );
  }

  Widget _buildDivider() {
    return Row(
      children: [
        const Expanded(child: Divider(color: Color(0xFFE6ECF4))),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          child: Text(
            '授权登录',
            style: AppTextStyles.bodyFont.copyWith(
              fontSize: 11,
              letterSpacing: 1.1,
              color: const Color(0xFF97A0AB),
            ),
          ),
        ),
        const Expanded(child: Divider(color: Color(0xFFE6ECF4))),
      ],
    );
  }

  Widget _buildGoogleButton() {
    return SizedBox(
      height: 56,
      child: OutlinedButton(
        key: const ValueKey('login-google-button'),
        onPressed: widget.isLoading ? null : widget.onGoogleSignIn,
        style: OutlinedButton.styleFrom(
          backgroundColor: Colors.white,
          side: const BorderSide(color: Color(0xFFD8E1EC)),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const _GoogleBadge(),
            const SizedBox(width: 12),
            Text(
              '使用 Google 企业账号继续',
              style: AppTextStyles.bodyFont.copyWith(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: const Color(0xFF1F2A33),
              ),
            ),
          ],
        ),
      ),
    );
  }

  OutlineInputBorder get _inputBorder => OutlineInputBorder(
    borderRadius: BorderRadius.circular(14),
    borderSide: BorderSide.none,
  );

  OutlineInputBorder get _focusedInputBorder => OutlineInputBorder(
    borderRadius: BorderRadius.circular(14),
    borderSide: const BorderSide(color: Color(0xFF9FC4FF), width: 1.2),
  );
}

class _GoogleBadge extends StatelessWidget {
  const _GoogleBadge();

  @override
  Widget build(BuildContext context) {
    return ShaderMask(
      shaderCallback: (bounds) => const SweepGradient(
        colors: [
          Color(0xFF4285F4),
          Color(0xFF34A853),
          Color(0xFFFBBC05),
          Color(0xFFEA4335),
          Color(0xFF4285F4),
        ],
      ).createShader(bounds),
      child: Text(
        'G',
        style: AppTextStyles.bodyFont.copyWith(
          fontSize: 22,
          fontWeight: FontWeight.w700,
          color: Colors.white,
        ),
      ),
    );
  }
}
