/// 登录页面
library;

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../viewmodels/login_view_model.dart';
import '../widgets/auth/login_background.dart';
import '../widgets/auth/login_form_card.dart';
import '../widgets/responsive_wrapper.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, this.viewModel});

  final LoginViewModel? viewModel;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  late final LoginViewModel _viewModel;
  late final bool _ownsViewModel;
  late final AnimationController _animationController;
  late final Animation<double> _fadeAnimation;
  late final Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _ownsViewModel = widget.viewModel == null;
    _viewModel = widget.viewModel ?? LoginViewModel();
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _fadeAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeOut),
    );
    _slideAnimation =
        Tween<Offset>(begin: const Offset(0, 0.1), end: Offset.zero).animate(
          CurvedAnimation(parent: _animationController, curve: Curves.easeOut),
        );
    _animationController.forward();
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _animationController.dispose();
    if (_ownsViewModel) {
      _viewModel.dispose();
    }
    super.dispose();
  }

  Future<void> _handleLoginOrRegister() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    final result = await _viewModel.authenticateWithEmail(
      email: _emailController.text.trim(),
      password: _passwordController.text,
    );

    if (!mounted) {
      return;
    }

    if (result == LoginSubmissionResult.registered) {
      await _showRegistrationSuccessDialog();
      return;
    }

    final errorMessage = _viewModel.errorMessage;
    if (result == LoginSubmissionResult.failed && errorMessage != null) {
      _showErrorSnackBar(errorMessage);
    }
  }

  Future<void> _handleGoogleSignIn() async {
    final success = await _viewModel.signInWithGoogle();
    if (!mounted || success) {
      return;
    }

    final errorMessage = _viewModel.errorMessage;
    if (errorMessage != null) {
      _showErrorSnackBar(errorMessage);
    }
  }

  Future<void> _showRegistrationSuccessDialog() {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        ),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppColors.successLight,
                borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              ),
              child: const Icon(Icons.check_circle, color: AppColors.success),
            ),
            const SizedBox(width: 12),
            const Text('注册成功'),
          ],
        ),
        content: const Text('您已成功注册！即将进入仪表盘。'),
        actions: [
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: AppColors.error,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final screenHeight = MediaQuery.sizeOf(context).height;
    return Scaffold(
      body: LoginBackground(
        child: SafeArea(
          child: Center(
            child: ResponsiveWrapper(
              maxWidth: 1120,
              mobileBreakpoint: 940,
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 32,
                ),
                child: FadeTransition(
                  opacity: _fadeAnimation,
                  child: SlideTransition(
                    position: _slideAnimation,
                    child: LayoutBuilder(
                      builder: (context, constraints) {
                        final isCompact = constraints.maxWidth < 940;
                        final shellHeight =
                            (screenHeight.clamp(720.0, 860.0) - 88).toDouble();

                        return ClipRRect(
                          borderRadius: BorderRadius.circular(32),
                          child: Container(
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.78),
                              borderRadius: BorderRadius.circular(32),
                              border: Border.all(
                                color: Colors.white.withValues(alpha: 0.82),
                                width: 1,
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: const Color(
                                    0xFF7AA4E0,
                                  ).withValues(alpha: 0.12),
                                  blurRadius: 42,
                                  offset: const Offset(0, 18),
                                ),
                              ],
                            ),
                            child: SizedBox(
                              height: isCompact ? null : shellHeight,
                              child: isCompact
                                  ? Column(
                                      children: [
                                        const _LoginHeroPanel(isCompact: true),
                                        _buildFormPanel(),
                                      ],
                                    )
                                  : Row(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.stretch,
                                      children: [
                                        const Expanded(
                                          flex: 58,
                                          child: _LoginHeroPanel(),
                                        ),
                                        Expanded(
                                          flex: 42,
                                          child: Container(
                                            color: Colors.white,
                                            child: _buildFormPanel(),
                                          ),
                                        ),
                                      ],
                                    ),
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFormPanel() {
    return ListenableBuilder(
      listenable: _viewModel,
      builder: (context, _) {
        return LoginFormCard(
          formKey: _formKey,
          emailController: _emailController,
          passwordController: _passwordController,
          obscurePassword: _viewModel.obscurePassword,
          isLoading: _viewModel.isLoading,
          onSubmit: _handleLoginOrRegister,
          onGoogleSignIn: _handleGoogleSignIn,
          onTogglePasswordVisibility: _viewModel.togglePasswordVisibility,
        );
      },
    );
  }
}

class _LoginHeroPanel extends StatelessWidget {
  const _LoginHeroPanel({this.isCompact = false});

  final bool isCompact;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: isCompact ? 380 : double.infinity,
      child: Container(
        padding: EdgeInsets.fromLTRB(
          isCompact ? 28 : 40,
          isCompact ? 28 : 38,
          isCompact ? 28 : 40,
          isCompact ? 28 : 34,
        ),
        decoration: BoxDecoration(
          color: const Color(0xFFEAF5FF),
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(32),
            bottomLeft: isCompact ? Radius.zero : const Radius.circular(32),
            topRight: isCompact ? const Radius.circular(32) : Radius.zero,
          ),
        ),
        child: Stack(
          children: [
            Positioned(top: 120, left: 28, child: _buildSparkle(18, 0.18)),
            Positioned(top: 320, right: 64, child: _buildSparkle(14, 0.2)),
            Positioned(bottom: 124, left: 42, child: _buildSparkle(12, 0.15)),
            Positioned.fill(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _HeroBrandBadge(isCompact: isCompact),
                  SizedBox(height: isCompact ? 34 : 56),
                  ConstrainedBox(
                    constraints: BoxConstraints(
                      maxWidth: isCompact ? 520 : 430,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text.rich(
                          TextSpan(
                            children: [
                              TextSpan(
                                text: '精准管理你的\n',
                                style: AppTextStyles.headingFont.copyWith(
                                  fontSize: isCompact ? 42 : 58,
                                  height: 1.06,
                                  fontWeight: FontWeight.w700,
                                  color: const Color(0xFF15212B),
                                ),
                              ),
                              TextSpan(
                                text: '能源生态系统\n',
                                style: AppTextStyles.headingFont.copyWith(
                                  fontSize: isCompact ? 42 : 58,
                                  height: 1.06,
                                  fontWeight: FontWeight.w700,
                                  color: const Color(0xFFB75A09),
                                ),
                              ),
                              TextSpan(
                                text: '与调度效率。',
                                style: AppTextStyles.headingFont.copyWith(
                                  fontSize: isCompact ? 42 : 58,
                                  height: 1.06,
                                  fontWeight: FontWeight.w700,
                                  color: const Color(0xFF15212B),
                                ),
                              ),
                            ],
                          ),
                        ),
                        SizedBox(height: isCompact ? 22 : 28),
                        Text(
                          '进入智能策展控制台，监控、排程并持续优化你的能源消耗与分析效率。',
                          style: AppTextStyles.bodyFont.copyWith(
                            fontSize: 16,
                            height: 1.55,
                            color: const Color(0xFF495766),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Spacer(),
                  Wrap(
                    spacing: 36,
                    runSpacing: 20,
                    children: const [
                      _HeroMetric(value: '98.2%', label: '调度效率'),
                      _HeroMetric(value: '2.4k', label: '活跃节点'),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSparkle(double size, double opacity) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: Colors.white.withValues(alpha: opacity),
          boxShadow: [
            BoxShadow(
              color: Colors.white.withValues(alpha: opacity * 1.4),
              blurRadius: 18,
              spreadRadius: 3,
            ),
          ],
        ),
      ),
    );
  }
}

class _HeroBrandBadge extends StatelessWidget {
  const _HeroBrandBadge({required this.isCompact});

  final bool isCompact;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: isCompact ? 34 : 32,
          height: isCompact ? 34 : 32,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
              colors: [Color(0xFFB75A09), Color(0xFFFF7A1A)],
            ),
            borderRadius: BorderRadius.circular(10),
          ),
          alignment: Alignment.center,
          child: const Icon(Icons.bolt_rounded, size: 18, color: Colors.white),
        ),
        const SizedBox(width: 12),
        Text(
          '智能能源平台',
          style: AppTextStyles.headingFont.copyWith(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: const Color(0xFF1B2730),
          ),
        ),
      ],
    );
  }
}

class _HeroMetric extends StatelessWidget {
  const _HeroMetric({required this.value, required this.label});

  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          value,
          style: AppTextStyles.headingFont.copyWith(
            fontSize: 28,
            fontWeight: FontWeight.w700,
            color: const Color(0xFF1B2730),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: AppTextStyles.bodyFont.copyWith(
            fontSize: 13,
            letterSpacing: 1.1,
            color: const Color(0xFF64717E),
          ),
        ),
      ],
    );
  }
}
