import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/widgets/auth/login_form_card.dart';

void main() {
  testWidgets('LoginFormCard disables controls and shows loading feedback', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(900, 1100);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final formKey = GlobalKey<FormState>();
    final emailController = TextEditingController(text: 'user@example.com');
    final passwordController = TextEditingController(text: 'secret123');
    addTearDown(emailController.dispose);
    addTearDown(passwordController.dispose);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: LoginFormCard(
            formKey: formKey,
            emailController: emailController,
            passwordController: passwordController,
            obscurePassword: true,
            isLoading: true,
            onSubmit: () {},
            onGoogleSignIn: () {},
            onTogglePasswordVisibility: () {},
          ),
        ),
      ),
    );

    expect(find.text('正在验证身份，请稍候...'), findsOneWidget);
    expect(find.text('正在验证'), findsOneWidget);
    expect(
      tester
          .widget<TextFormField>(
            find.byKey(const ValueKey('login-email-field')),
          )
          .enabled,
      isFalse,
    );
    expect(
      tester
          .widget<TextFormField>(
            find.byKey(const ValueKey('login-password-field')),
          )
          .enabled,
      isFalse,
    );
    expect(
      tester
          .widget<ElevatedButton>(
            find.byKey(const ValueKey('login-submit-button')),
          )
          .onPressed,
      isNull,
    );
    expect(
      tester
          .widget<OutlinedButton>(
            find.byKey(const ValueKey('login-google-button')),
          )
          .onPressed,
      isNull,
    );
  });
}
