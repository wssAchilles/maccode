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
    return Scaffold(
      body: LoginBackground(
        child: Center(
          child: ResponsiveWrapper(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: FadeTransition(
                opacity: _fadeAnimation,
                child: SlideTransition(
                  position: _slideAnimation,
                  child: ListenableBuilder(
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
                        onTogglePasswordVisibility:
                            _viewModel.togglePasswordVisibility,
                      );
                    },
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
