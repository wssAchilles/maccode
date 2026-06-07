import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/widgets/analysis/data_analysis_state_views.dart';
import 'package:front/widgets/analysis/data_analysis_top_section.dart';

class _FakeUser extends Fake implements User {
  _FakeUser({required this.email, this.displayName});

  @override
  final String? email;

  @override
  final String? displayName;

  @override
  String? get photoURL => null;
}

void main() {
  testWidgets('DataAnalysisLoadingView renders auth-specific copy', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: DataAnalysisLoadingView(isAuthenticated: false)),
      ),
    );

    expect(find.text('认证处理中'), findsOneWidget);

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: DataAnalysisLoadingView(isAuthenticated: true)),
      ),
    );

    expect(find.text('分析任务执行中'), findsOneWidget);
  });

  testWidgets('DataAnalysisStartButton respects enabled state', (
    WidgetTester tester,
  ) async {
    var started = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DataAnalysisStartButton(
            canAnalyze: false,
            onStart: () => started = true,
          ),
        ),
      ),
    );

    await tester.tap(find.byKey(const ValueKey('analysis-start-button')));
    await tester.pump();
    expect(started, isFalse);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DataAnalysisStartButton(
            canAnalyze: true,
            onStart: () => started = true,
          ),
        ),
      ),
    );

    await tester.tap(find.byKey(const ValueKey('analysis-start-button')));
    await tester.pump();
    expect(started, isTrue);
  });

  testWidgets('DataAnalysisErrorBanner renders message and dismisses', (
    WidgetTester tester,
  ) async {
    var dismissed = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DataAnalysisErrorBanner(
            message: '分析失败',
            onDismiss: () => dismissed = true,
          ),
        ),
      ),
    );

    expect(find.text('分析失败'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('analysis-error-dismiss')));
    await tester.pump();

    expect(dismissed, isTrue);
  });

  testWidgets('DataAnalysisTopSection shows auth form when logged out', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: DataAnalysisTopSection(
              currentUser: null,
              pickedFile: null,
              saveToStorage: true,
              formKey: GlobalKey<FormState>(),
              emailController: TextEditingController(),
              passwordController: TextEditingController(),
              authMode: 'login',
              onSignInWithEmail: () {},
              onRegisterWithEmail: () {},
              onToggleAuthMode: () {},
              onGoogleSignIn: () {},
              onPickFile: () {},
              onClearFile: () {},
              onStorageChanged: (_) {},
            ),
          ),
        ),
      ),
    );

    expect(find.text('登录以使用数据分析服务'), findsOneWidget);
    expect(find.text('选择 CSV 文件'), findsOneWidget);
  });

  testWidgets('DataAnalysisTopSection shows user info when logged in', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: DataAnalysisTopSection(
              currentUser: _FakeUser(
                email: 'user@example.com',
                displayName: '测试用户',
              ),
              pickedFile: PlatformFile(name: 'data.csv', size: 1024),
              saveToStorage: true,
              formKey: GlobalKey<FormState>(),
              emailController: TextEditingController(),
              passwordController: TextEditingController(),
              authMode: 'login',
              onSignInWithEmail: () {},
              onRegisterWithEmail: () {},
              onToggleAuthMode: () {},
              onGoogleSignIn: () {},
              onPickFile: () {},
              onClearFile: () {},
              onStorageChanged: (_) {},
            ),
          ),
        ),
      ),
    );

    expect(find.text('测试用户'), findsOneWidget);
    expect(find.text('data.csv'), findsOneWidget);
  });
}
