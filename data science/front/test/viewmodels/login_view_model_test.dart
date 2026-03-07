import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/auth_failure.dart';
import 'package:front/services/auth_gateway.dart';
import 'package:front/viewmodels/login_view_model.dart';

class _FakeUserCredential extends Fake implements UserCredential {}

class _FakeAuthGateway implements AuthGateway {
  _FakeAuthGateway({
    this.signInWithEmailHandler,
    this.registerWithEmailHandler,
    this.signInWithGoogleHandler,
  });

  final Future<UserCredential> Function(String email, String password)?
  signInWithEmailHandler;
  final Future<UserCredential> Function(String email, String password)?
  registerWithEmailHandler;
  final Future<UserCredential> Function()? signInWithGoogleHandler;

  @override
  User? get currentUser => null;

  @override
  Stream<User?> get authStateChanges => const Stream<User?>.empty();

  @override
  Future<UserCredential> signInWithGoogle() {
    return signInWithGoogleHandler?.call() ??
        Future<UserCredential>.value(_FakeUserCredential());
  }

  @override
  Future<UserCredential> signInWithEmail({
    required String email,
    required String password,
  }) {
    return signInWithEmailHandler?.call(email, password) ??
        Future<UserCredential>.value(_FakeUserCredential());
  }

  @override
  Future<UserCredential> registerWithEmail({
    required String email,
    required String password,
  }) {
    return registerWithEmailHandler?.call(email, password) ??
        Future<UserCredential>.value(_FakeUserCredential());
  }

  @override
  Future<void> signOut() async {}
}

void main() {
  test('authenticateWithEmail returns signedIn on successful login', () async {
    final viewModel = LoginViewModel(authGateway: _FakeAuthGateway());

    final result = await viewModel.authenticateWithEmail(
      email: 'user@example.com',
      password: 'secret123',
    );

    expect(result, LoginSubmissionResult.signedIn);
    expect(viewModel.errorMessage, isNull);
    expect(viewModel.isLoading, isFalse);
  });

  test('authenticateWithEmail auto-registers when user is missing', () async {
    var registerCalled = false;
    final viewModel = LoginViewModel(
      authGateway: _FakeAuthGateway(
        signInWithEmailHandler: (_, _) {
          throw const AuthFailureException(
            AuthFailure(code: 'user-not-found', message: '用户不存在'),
          );
        },
        registerWithEmailHandler: (_, _) {
          registerCalled = true;
          return Future<UserCredential>.value(_FakeUserCredential());
        },
      ),
    );

    final result = await viewModel.authenticateWithEmail(
      email: 'new@example.com',
      password: 'secret123',
    );

    expect(result, LoginSubmissionResult.registered);
    expect(registerCalled, isTrue);
    expect(viewModel.errorMessage, isNull);
  });

  test(
    'authenticateWithEmail keeps login error for non-registerable failure',
    () async {
      final viewModel = LoginViewModel(
        authGateway: _FakeAuthGateway(
          signInWithEmailHandler: (_, _) {
            throw const AuthFailureException(
              AuthFailure(code: 'wrong-password', message: '密码错误'),
            );
          },
        ),
      );

      final result = await viewModel.authenticateWithEmail(
        email: 'user@example.com',
        password: 'bad-password',
      );

      expect(result, LoginSubmissionResult.failed);
      expect(viewModel.errorMessage, '登录失败: 密码错误');
    },
  );

  test(
    'authenticateWithEmail surfaces original login failure when register hits existing email',
    () async {
      final viewModel = LoginViewModel(
        authGateway: _FakeAuthGateway(
          signInWithEmailHandler: (_, _) {
            throw const AuthFailureException(
              AuthFailure(code: 'invalid-credential', message: '用户不存在或密码错误'),
            );
          },
          registerWithEmailHandler: (_, _) {
            throw const AuthFailureException(
              AuthFailure(code: 'email-already-in-use', message: '邮箱已被注册'),
            );
          },
        ),
      );

      final result = await viewModel.authenticateWithEmail(
        email: 'user@example.com',
        password: 'bad-password',
      );

      expect(result, LoginSubmissionResult.failed);
      expect(viewModel.errorMessage, '登录失败: 用户不存在或密码错误');
    },
  );

  test('signInWithGoogle ignores cancelled sign-in as a non-error', () async {
    final viewModel = LoginViewModel(
      authGateway: _FakeAuthGateway(
        signInWithGoogleHandler: () {
          throw const AuthFailureException(
            AuthFailure(code: 'cancelled', message: '登录已取消'),
          );
        },
      ),
    );

    final success = await viewModel.signInWithGoogle();

    expect(success, isFalse);
    expect(viewModel.errorMessage, isNull);
  });

  test(
    'authenticateWithEmail exposes loading while request is in-flight',
    () async {
      final completer = Completer<UserCredential>();
      final viewModel = LoginViewModel(
        authGateway: _FakeAuthGateway(
          signInWithEmailHandler: (_, _) => completer.future,
        ),
      );

      final future = viewModel.authenticateWithEmail(
        email: 'user@example.com',
        password: 'secret123',
      );

      expect(viewModel.isLoading, isTrue);

      completer.complete(_FakeUserCredential());
      await future;

      expect(viewModel.isLoading, isFalse);
    },
  );

  test('togglePasswordVisibility flips obscurePassword state', () {
    final viewModel = LoginViewModel(authGateway: _FakeAuthGateway());

    expect(viewModel.obscurePassword, isTrue);

    viewModel.togglePasswordVisibility();
    expect(viewModel.obscurePassword, isFalse);

    viewModel.togglePasswordVisibility();
    expect(viewModel.obscurePassword, isTrue);
  });
}
