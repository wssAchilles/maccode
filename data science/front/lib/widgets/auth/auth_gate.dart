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

class AuthGate extends StatelessWidget {
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
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      stream: _authRepository.authStateChanges,
      initialData: _authRepository.currentUser,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting &&
            snapshot.data == null &&
            !snapshot.hasError) {
          final builder = loadingBuilder;
          return builder?.call(context) ?? const _AuthGateLoadingView();
        }

        if (snapshot.hasError) {
          final error = snapshot.error!;
          final builder = errorBuilder;
          return builder?.call(context, error) ??
              _AuthGateErrorView(error: error);
        }

        final user = snapshot.data;
        if (user != null) {
          final builder = authenticatedBuilder;
          return builder?.call(context, user) ??
              MainNavigation(authRepository: _authRepository);
        }

        final builder = unauthenticatedBuilder;
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
  const _AuthGateErrorView({required this.error});

  final Object error;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              '认证服务出错: $error',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.red),
            ),
          ],
        ),
      ),
    );
  }
}
