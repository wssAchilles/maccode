import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/auth_action_result.dart';
import 'package:front/repositories/auth_repository.dart';
import 'package:front/widgets/auth/auth_gate.dart';

class _FakeUser extends Fake implements User {}

class _FakeAuthRepository implements AuthRepository {
  _FakeAuthRepository(this._controller, {this.currentUserValue});

  final StreamController<User?> _controller;
  final User? currentUserValue;

  @override
  User? get currentUser => currentUserValue;

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
  Future<void> signOut() async {}
}

void main() {
  testWidgets('shows loading before auth stream emits', (
    WidgetTester tester,
  ) async {
    final controller = StreamController<User?>();

    await tester.pumpWidget(
      MaterialApp(
        home: AuthGate(
          authRepository: _FakeAuthRepository(controller),
          authenticatedBuilder: (_, user) => const Text('已登录'),
          unauthenticatedBuilder: (_) => const Text('未登录'),
        ),
      ),
    );

    expect(find.text('加载中...'), findsOneWidget);

    await controller.close();
  });

  testWidgets('shows unauthenticated builder when stream emits null', (
    WidgetTester tester,
  ) async {
    final controller = StreamController<User?>();

    await tester.pumpWidget(
      MaterialApp(
        home: AuthGate(
          authRepository: _FakeAuthRepository(controller),
          authenticatedBuilder: (_, user) => const Text('已登录'),
          unauthenticatedBuilder: (_) => const Text('未登录'),
        ),
      ),
    );

    controller.add(null);
    await tester.pump();

    expect(find.text('未登录'), findsOneWidget);

    await controller.close();
  });

  testWidgets('shows authenticated builder when stream emits user', (
    WidgetTester tester,
  ) async {
    final controller = StreamController<User?>();

    await tester.pumpWidget(
      MaterialApp(
        home: AuthGate(
          authRepository: _FakeAuthRepository(controller),
          authenticatedBuilder: (_, user) => const Text('已登录'),
          unauthenticatedBuilder: (_) => const Text('未登录'),
        ),
      ),
    );

    controller.add(_FakeUser());
    await tester.pump();

    expect(find.text('已登录'), findsOneWidget);

    await controller.close();
  });

  testWidgets('uses currentUser as initial authenticated state', (
    WidgetTester tester,
  ) async {
    final controller = StreamController<User?>();

    await tester.pumpWidget(
      MaterialApp(
        home: AuthGate(
          authRepository: _FakeAuthRepository(
            controller,
            currentUserValue: _FakeUser(),
          ),
          authenticatedBuilder: (_, user) => const Text('已登录'),
          unauthenticatedBuilder: (_) => const Text('未登录'),
        ),
      ),
    );

    expect(find.text('已登录'), findsOneWidget);
    expect(find.text('加载中...'), findsNothing);

    await controller.close();
  });

  testWidgets('shows error view when auth stream fails', (
    WidgetTester tester,
  ) async {
    final controller = StreamController<User?>();

    await tester.pumpWidget(
      MaterialApp(
        home: AuthGate(
          authRepository: _FakeAuthRepository(controller),
          authenticatedBuilder: (_, user) => const Text('已登录'),
          unauthenticatedBuilder: (_) => const Text('未登录'),
        ),
      ),
    );

    controller.addError(Exception('boom'));
    await tester.pump();

    expect(find.textContaining('认证服务出错'), findsOneWidget);

    await controller.close();
  });
}
