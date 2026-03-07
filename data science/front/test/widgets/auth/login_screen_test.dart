import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/auth_failure.dart';
import 'package:front/screens/login_screen.dart';
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

  int signInCallCount = 0;

  @override
  User? get currentUser => null;

  @override
  Stream<User?> get authStateChanges => const Stream<User?>.empty();

  @override
  Future<UserCredential> signInWithEmail({
    required String email,
    required String password,
  }) {
    signInCallCount += 1;
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
  Future<UserCredential> signInWithGoogle() {
    return signInWithGoogleHandler?.call() ??
        Future<UserCredential>.value(_FakeUserCredential());
  }

  @override
  Future<void> signOut() async {}
}

Future<void> _pumpLoginScreen(
  WidgetTester tester, {
  required LoginViewModel viewModel,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      home: LoginScreen(viewModel: viewModel),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('LoginScreen validates required fields before submitting', (
    WidgetTester tester,
  ) async {
    final gateway = _FakeAuthGateway();
    final viewModel = LoginViewModel(authGateway: gateway);
    addTearDown(viewModel.dispose);

    await _pumpLoginScreen(tester, viewModel: viewModel);

    await tester.tap(find.byKey(const ValueKey('login-submit-button')));
    await tester.pumpAndSettle();

    expect(find.text('请输入邮箱'), findsOneWidget);
    expect(find.text('请输入密码'), findsOneWidget);
    expect(gateway.signInCallCount, 0);
  });

  testWidgets('LoginScreen shows registration dialog after auto register', (
    WidgetTester tester,
  ) async {
    final viewModel = LoginViewModel(
      authGateway: _FakeAuthGateway(
        signInWithEmailHandler: (_, _) {
          throw const AuthFailureException(
            AuthFailure(code: 'user-not-found', message: '用户不存在'),
          );
        },
        registerWithEmailHandler: (_, _) {
          return Future<UserCredential>.value(_FakeUserCredential());
        },
      ),
    );
    addTearDown(viewModel.dispose);

    await _pumpLoginScreen(tester, viewModel: viewModel);

    await tester.enterText(
      find.byKey(const ValueKey('login-email-field')),
      'new@example.com',
    );
    await tester.enterText(
      find.byKey(const ValueKey('login-password-field')),
      'secret123',
    );

    await tester.tap(find.byKey(const ValueKey('login-submit-button')));
    await tester.pumpAndSettle();

    expect(find.text('注册成功'), findsOneWidget);
    expect(find.text('您已成功注册！即将进入仪表盘。'), findsOneWidget);
  });

  testWidgets('LoginScreen shows snackbar on email auth failure', (
    WidgetTester tester,
  ) async {
    final viewModel = LoginViewModel(
      authGateway: _FakeAuthGateway(
        signInWithEmailHandler: (_, _) {
          throw const AuthFailureException(
            AuthFailure(code: 'wrong-password', message: '密码错误'),
          );
        },
      ),
    );
    addTearDown(viewModel.dispose);

    await _pumpLoginScreen(tester, viewModel: viewModel);

    await tester.enterText(
      find.byKey(const ValueKey('login-email-field')),
      'user@example.com',
    );
    await tester.enterText(
      find.byKey(const ValueKey('login-password-field')),
      'secret123',
    );

    await tester.tap(find.byKey(const ValueKey('login-submit-button')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('登录失败: 密码错误'), findsOneWidget);
  });

  testWidgets('LoginScreen toggles password visibility', (
    WidgetTester tester,
  ) async {
    final viewModel = LoginViewModel(authGateway: _FakeAuthGateway());
    addTearDown(viewModel.dispose);

    await _pumpLoginScreen(tester, viewModel: viewModel);

    expect(find.byIcon(Icons.visibility_off_outlined), findsOneWidget);

    await tester.tap(
      find.byKey(const ValueKey('login-password-visibility-button')),
    );
    await tester.pump();

    expect(find.byIcon(Icons.visibility_outlined), findsOneWidget);
  });

  testWidgets('LoginScreen shows snackbar on google sign-in failure', (
    WidgetTester tester,
  ) async {
    final viewModel = LoginViewModel(
      authGateway: _FakeAuthGateway(
        signInWithGoogleHandler: () {
          throw const AuthFailureException(
            AuthFailure(code: 'popup-closed', message: '弹窗被关闭'),
          );
        },
      ),
    );
    addTearDown(viewModel.dispose);

    await _pumpLoginScreen(tester, viewModel: viewModel);

    await tester.tap(find.byKey(const ValueKey('login-google-button')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('谷歌登录失败: 弹窗被关闭'), findsOneWidget);
  });
}
