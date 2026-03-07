import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/widgets/auth/data_analysis_auth_form.dart';

void main() {
  testWidgets('login mode renders login copy and triggers login callback', (
    WidgetTester tester,
  ) async {
    final emailController = TextEditingController();
    final passwordController = TextEditingController();
    final formKey = GlobalKey<FormState>();

    var loginTapped = false;
    var registerTapped = false;
    var toggleTapped = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DataAnalysisAuthForm(
            formKey: formKey,
            emailController: emailController,
            passwordController: passwordController,
            authMode: 'login',
            onSignInWithEmail: () => loginTapped = true,
            onRegisterWithEmail: () => registerTapped = true,
            onToggleAuthMode: () => toggleTapped = true,
            onGoogleSignIn: () {},
          ),
        ),
      ),
    );

    expect(find.text('登录以使用数据分析服务'), findsOneWidget);
    expect(find.text('登录'), findsOneWidget);
    expect(find.text('立即注册'), findsOneWidget);

    await tester.tap(find.text('登录'));
    await tester.pump();

    expect(loginTapped, isTrue);
    expect(registerTapped, isFalse);

    await tester.tap(find.text('立即注册'));
    await tester.pump();

    expect(toggleTapped, isTrue);

    emailController.dispose();
    passwordController.dispose();
  });

  testWidgets(
    'register mode renders register copy and triggers register callback',
    (WidgetTester tester) async {
      final emailController = TextEditingController();
      final passwordController = TextEditingController();
      final formKey = GlobalKey<FormState>();

      var loginTapped = false;
      var registerTapped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DataAnalysisAuthForm(
              formKey: formKey,
              emailController: emailController,
              passwordController: passwordController,
              authMode: 'register',
              onSignInWithEmail: () => loginTapped = true,
              onRegisterWithEmail: () => registerTapped = true,
              onToggleAuthMode: () {},
              onGoogleSignIn: () {},
            ),
          ),
        ),
      );

      expect(find.text('注册新账户'), findsOneWidget);
      expect(find.text('注册'), findsOneWidget);
      expect(find.text('返回登录'), findsOneWidget);

      await tester.tap(find.text('注册'));
      await tester.pump();

      expect(registerTapped, isTrue);
      expect(loginTapped, isFalse);

      emailController.dispose();
      passwordController.dispose();
    },
  );
}
