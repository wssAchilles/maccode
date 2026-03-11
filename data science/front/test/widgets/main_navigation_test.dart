import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/auth_action_result.dart';
import 'package:front/repositories/auth_repository.dart';
import 'package:front/widgets/main_navigation.dart';

class _FakeAuthRepository implements AuthRepository {
  _FakeAuthRepository({User? currentUser, Stream<User?>? authStateChanges})
    : _currentUser = currentUser,
      _authStateChanges = authStateChanges ?? const Stream<User?>.empty();

  User? _currentUser;
  final Stream<User?> _authStateChanges;

  @override
  User? get currentUser => _currentUser;

  @override
  Stream<User?> get authStateChanges => _authStateChanges;

  @override
  Future<AuthActionResult> signInWithGoogle() => throw UnimplementedError();

  @override
  Future<AuthActionResult> signInWithEmail({
    required String email,
    required String password,
  }) => throw UnimplementedError();

  @override
  Future<AuthActionResult> registerWithEmail({
    required String email,
    required String password,
  }) => throw UnimplementedError();

  @override
  Future<void> signOut() async {
    _currentUser = null;
  }
}

class _ReactiveAuthRepository implements AuthRepository {
  _ReactiveAuthRepository();

  final StreamController<User?> _controller =
      StreamController<User?>.broadcast();
  User? _currentUser;

  @override
  User? get currentUser => _currentUser;

  @override
  Stream<User?> get authStateChanges => _controller.stream;

  @override
  Future<AuthActionResult> signInWithGoogle() => throw UnimplementedError();

  @override
  Future<AuthActionResult> signInWithEmail({
    required String email,
    required String password,
  }) => throw UnimplementedError();

  @override
  Future<AuthActionResult> registerWithEmail({
    required String email,
    required String password,
  }) => throw UnimplementedError();

  @override
  Future<void> signOut() async {
    emit(null);
  }

  void emit(User? user) {
    _currentUser = user;
    _controller.add(user);
  }

  Future<void> dispose() async {
    await _controller.close();
  }
}

class _FakeUser implements User {
  _FakeUser({required this.uid, this.email, this.emailVerified = false});

  @override
  final String uid;

  @override
  final String? email;

  @override
  final bool emailVerified;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
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
    return MainNavigation.custom(
      authRepository: _FakeAuthRepository(),
      pages: const [
        _PlainPage('概览内容'),
        _PlainPage('模型页内容'),
        _PlainPage('分析页内容'),
        _PlainPage('AI Lab 内容'),
        _PlainPage('历史页内容'),
      ],
    );
  }

  testWidgets('uses a single shell scaffold without top-level AppBar', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(MaterialApp(home: buildShell()));

    expect(find.byType(Scaffold), findsOneWidget);
    expect(find.byType(AppBar), findsNothing);
    expect(find.text('概览内容'), findsOneWidget);
  });

  testWidgets('switches tabs through bottom navigation items', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(MaterialApp(home: buildShell()));

    expect(find.text('概览内容'), findsOneWidget);
    expect(find.text('模型页内容'), findsNothing);
    expect(find.text('分析页内容'), findsNothing);
    expect(find.text('历史页内容'), findsNothing);

    await tester.tap(find.text('数据分析'));
    await tester.pumpAndSettle();
    expect(find.text('分析页内容'), findsOneWidget);

    await tester.tap(find.text('AI Lab'));
    await tester.pumpAndSettle();
    expect(find.text('AI Lab 内容'), findsOneWidget);

    await tester.tap(find.text('历史与审计'));
    await tester.pumpAndSettle();
    expect(find.text('历史页内容'), findsOneWidget);
  });

  testWidgets(
    'keeps only child page app bar when tabs use their own scaffold',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: MainNavigation.custom(
            authRepository: _FakeAuthRepository(),
            pages: const [
              _ScaffoldPage('概览页'),
              _ScaffoldPage('模型页'),
              _ScaffoldPage('分析页'),
              _ScaffoldPage('AI Lab'),
              _ScaffoldPage('历史页'),
            ],
          ),
        ),
      );

      expect(find.byType(AppBar), findsOneWidget);
      expect(find.text('概览页'), findsOneWidget);

      await tester.tap(find.text('数据分析'));
      await tester.pumpAndSettle();

      expect(find.byType(AppBar), findsOneWidget);
      expect(find.text('分析页'), findsOneWidget);
      expect(find.text('概览页'), findsNothing);
    },
  );

  testWidgets('disables auth actions when no current user is available', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(MaterialApp(home: buildShell()));

    final userInfoButton = tester.widget<OutlinedButton>(
      find.byKey(const ValueKey('main-nav-user-info')),
    );
    final signOutButton = tester.widget<FilledButton>(
      find.byKey(const ValueKey('main-nav-sign-out')),
    );

    expect(userInfoButton.onPressed, isNull);
    expect(signOutButton.onPressed, isNull);
  });

  testWidgets('reacts to auth state changes and enables user actions', (
    WidgetTester tester,
  ) async {
    final authRepository = _ReactiveAuthRepository();
    addTearDown(authRepository.dispose);

    await tester.pumpWidget(
      MaterialApp(
        home: MainNavigation.custom(
          authRepository: authRepository,
          pages: const [
            _PlainPage('概览内容'),
            _PlainPage('模型页内容'),
            _PlainPage('分析页内容'),
            _PlainPage('AI Lab 内容'),
            _PlainPage('历史页内容'),
          ],
        ),
      ),
    );

    expect(
      tester
          .widget<OutlinedButton>(
            find.byKey(const ValueKey('main-nav-user-info')),
          )
          .onPressed,
      isNull,
    );

    authRepository.emit(
      _FakeUser(
        uid: 'user-12345678',
        email: 'user@example.com',
        emailVerified: true,
      ),
    );
    await tester.pump();

    expect(
      tester
          .widget<OutlinedButton>(
            find.byKey(const ValueKey('main-nav-user-info')),
          )
          .onPressed,
      isNotNull,
    );
    expect(
      tester
          .widget<FilledButton>(find.byKey(const ValueKey('main-nav-sign-out')))
          .onPressed,
      isNotNull,
    );

    await tester.tap(find.byKey(const ValueKey('main-nav-user-info')));
    await tester.pumpAndSettle();

    expect(find.text('用户信息'), findsNWidgets(2));
    expect(find.text('user@example.com'), findsOneWidget);
  });
}
