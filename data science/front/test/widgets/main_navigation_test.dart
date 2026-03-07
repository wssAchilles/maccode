import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/services/auth_gateway.dart';
import 'package:front/widgets/main_navigation.dart';

class _FakeAuthGateway implements AuthGateway {
  @override
  User? get currentUser => null;

  @override
  Stream<User?> get authStateChanges => const Stream<User?>.empty();

  @override
  Future<UserCredential> signInWithGoogle() => throw UnimplementedError();

  @override
  Future<UserCredential> signInWithEmail({
    required String email,
    required String password,
  }) => throw UnimplementedError();

  @override
  Future<UserCredential> registerWithEmail({
    required String email,
    required String password,
  }) => throw UnimplementedError();

  @override
  Future<void> signOut() async {}
}

class _PlainPage extends StatelessWidget {
  const _PlainPage(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Center(child: Text(label));
  }
}

class _ScaffoldPage extends StatelessWidget {
  const _ScaffoldPage(this.title);

  final String title;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(child: Text('$title 内容')),
    );
  }
}

void main() {
  MainNavigation buildShell() {
    return MainNavigation(
      authGateway: _FakeAuthGateway(),
      pages: const [
        _PlainPage('模型页内容'),
        _PlainPage('分析页内容'),
        _PlainPage('历史页内容'),
      ],
    );
  }

  testWidgets('keeps shell minimal without top-level Scaffold/AppBar', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(MaterialApp(home: buildShell()));

    expect(find.byType(Scaffold), findsNothing);
    expect(find.byType(AppBar), findsNothing);
    expect(find.text('模型页内容'), findsOneWidget);
  });

  testWidgets('switches tabs through bottom navigation items', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(MaterialApp(home: buildShell()));

    expect(find.text('模型页内容'), findsOneWidget);
    expect(find.text('分析页内容'), findsNothing);
    expect(find.text('历史页内容'), findsNothing);

    await tester.tap(find.byKey(const ValueKey('main-nav-item-1')));
    await tester.pumpAndSettle();
    expect(find.text('分析页内容'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('main-nav-item-2')));
    await tester.pumpAndSettle();
    expect(find.text('历史页内容'), findsOneWidget);
  });

  testWidgets(
    'keeps only child page app bar when tabs use their own scaffold',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: MainNavigation(
            authGateway: _FakeAuthGateway(),
            pages: const [
              _ScaffoldPage('模型页'),
              _ScaffoldPage('分析页'),
              _ScaffoldPage('历史页'),
            ],
          ),
        ),
      );

      expect(find.byType(AppBar), findsOneWidget);
      expect(find.text('模型页'), findsOneWidget);

      await tester.tap(find.byKey(const ValueKey('main-nav-item-1')));
      await tester.pumpAndSettle();

      expect(find.byType(AppBar), findsOneWidget);
      expect(find.text('分析页'), findsOneWidget);
      expect(find.text('模型页'), findsNothing);
    },
  );
}
