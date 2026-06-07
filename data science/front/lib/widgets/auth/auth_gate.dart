/// 应用认证入口组件
/// 统一处理认证等待、错误、已登录和未登录四种入口态
library;

import 'package:firebase_auth/firebase_auth.dart' show User;
import 'package:flutter/material.dart';

import '../../repositories/auth_repository.dart';
import '../../screens/login_screen.dart';
import '../../services/auth_gateway.dart';
import '../main_navigation.dart';

typedef AuthenticatedBuilder = Widget Function(BuildContext context, User user);
typedef AuthErrorBuilder = Widget Function(BuildContext context, Object error);

class AuthGate extends StatefulWidget {
  AuthGate({
    super.key,
    AuthRepository? authRepository,
    AuthGateway? authGateway,
    this.authenticatedBuilder,
    this.unauthenticatedBuilder,
    this.loadingBuilder,
    this.errorBuilder,
  }) : assert(
         authRepository == null || authGateway == null,
         'Provide either authRepository or authGateway, not both.',
       ),
       _authRepository =
           authRepository ?? GatewayAuthRepository(authGateway: authGateway);

  final AuthRepository _authRepository;
  final AuthenticatedBuilder? authenticatedBuilder;
  final WidgetBuilder? unauthenticatedBuilder;
  final WidgetBuilder? loadingBuilder;
  final AuthErrorBuilder? errorBuilder;

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  int _retryKey = 0;
  bool _showLoginFallback = false;

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      key: ValueKey(_retryKey),
      stream: widget._authRepository.authStateChanges,
      initialData: _showLoginFallback
          ? null
          : widget._authRepository.currentUser,
      builder: (context, snapshot) {
        if (_showLoginFallback) {
          final builder = widget.unauthenticatedBuilder;
          return builder?.call(context) ?? const LoginScreen();
        }
        if (snapshot.connectionState == ConnectionState.waiting &&
            snapshot.data == null &&
            !snapshot.hasError) {
          final builder = widget.loadingBuilder;
          return builder?.call(context) ?? const _AuthGateLoadingView();
        }

        if (snapshot.hasError) {
          final error = snapshot.error!;
          final builder = widget.errorBuilder;
          return builder?.call(context, error) ??
              _AuthGateErrorView(
                error: error,
                onRetry: () {
                  setState(() {
                    _showLoginFallback = false;
                    _retryKey++;
                  });
                },
                onReturnToLogin: () {
                  setState(() {
                    _showLoginFallback = true;
                  });
                },
              );
        }

        final user = snapshot.data;
        if (user != null) {
          final builder = widget.authenticatedBuilder;
          return builder?.call(context, user) ??
              MainNavigation(authRepository: widget._authRepository);
        }

        final builder = widget.unauthenticatedBuilder;
        return builder?.call(context) ?? const LoginScreen();
      },
    );
  }
}

class _AuthGateLoadingView extends StatelessWidget {
  const _AuthGateLoadingView();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('加载中...', style: TextStyle(fontSize: 16, color: Colors.grey)),
          ],
        ),
      ),
    );
  }
}

class _AuthGateErrorView extends StatelessWidget {
  const _AuthGateErrorView({
    required this.error,
    required this.onRetry,
    required this.onReturnToLogin,
  });

  final Object error;
  final VoidCallback onRetry;
  final VoidCallback onReturnToLogin;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error_outline, size: 64, color: Colors.red),
                const SizedBox(height: 16),
                const Text(
                  '认证服务暂时不可用',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                const Text(
                  '请重试认证状态，或返回登录页后稍后再试。',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey),
                ),
                const SizedBox(height: 16),
                ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  title: const Text('技术详情'),
                  children: [
                    SelectableText(
                      error.toString(),
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.red),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                Wrap(
                  alignment: WrapAlignment.center,
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    FilledButton.icon(
                      onPressed: onRetry,
                      icon: const Icon(Icons.refresh_rounded),
                      label: const Text('重试认证状态'),
                    ),
                    OutlinedButton.icon(
                      onPressed: onReturnToLogin,
                      icon: const Icon(Icons.login_rounded),
                      label: const Text('返回登录页'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
