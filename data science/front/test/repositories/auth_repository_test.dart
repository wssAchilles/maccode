import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/auth_failure.dart';
import 'package:front/repositories/auth_repository.dart';
import 'package:front/services/auth_gateway.dart';

class _FakeUser extends Fake implements User {
  _FakeUser(this.email);

  @override
  final String? email;

  @override
  String get uid => 'user-12345678';
}

class _FakeUserCredential extends Fake implements UserCredential {
  _FakeUserCredential(this._user);

  final User? _user;

  @override
  User? get user => _user;
}

class _FakeAuthGateway implements AuthGateway {
  _FakeAuthGateway({
    this.currentUserValue,
    this.authStateChangesValue,
    this.signInWithGoogleHandler,
    this.signInWithEmailHandler,
    this.registerWithEmailHandler,
  });

  final User? currentUserValue;
  final Stream<User?>? authStateChangesValue;
  final Future<UserCredential> Function()? signInWithGoogleHandler;
  final Future<UserCredential> Function({
    required String email,
    required String password,
  })?
  signInWithEmailHandler;
  final Future<UserCredential> Function({
    required String email,
    required String password,
  })?
  registerWithEmailHandler;

  @override
  User? get currentUser => currentUserValue;

  @override
  Stream<User?> get authStateChanges =>
      authStateChangesValue ?? const Stream<User?>.empty();

  @override
  Future<UserCredential> signInWithGoogle() async {
    final handler = signInWithGoogleHandler;
    if (handler == null) {
      throw UnimplementedError();
    }
    return handler();
  }

  @override
  Future<UserCredential> signInWithEmail({
    required String email,
    required String password,
  }) async {
    final handler = signInWithEmailHandler;
    if (handler == null) {
      throw UnimplementedError();
    }
    return handler(email: email, password: password);
  }

  @override
  Future<UserCredential> registerWithEmail({
    required String email,
    required String password,
  }) async {
    final handler = registerWithEmailHandler;
    if (handler == null) {
      throw UnimplementedError();
    }
    return handler(email: email, password: password);
  }

  @override
  Future<void> signOut() async {}
}

void main() {
  test('signInWithEmail returns success result with user', () async {
    final repository = GatewayAuthRepository(
      authGateway: _FakeAuthGateway(
        signInWithEmailHandler: ({required email, required password}) async {
          return _FakeUserCredential(_FakeUser(email));
        },
      ),
    );

    final result = await repository.signInWithEmail(
      email: 'user@example.com',
      password: 'secret123',
    );

    expect(result.isSuccess, isTrue);
    expect(result.user?.email, 'user@example.com');
    expect(result.failure, isNull);
  });

  test(
    'signInWithGoogle preserves typed failure and cancelled state',
    () async {
      final repository = GatewayAuthRepository(
        authGateway: _FakeAuthGateway(
          signInWithGoogleHandler: () async {
            throw const AuthFailureException(
              AuthFailure(code: 'cancelled', message: '登录已取消'),
            );
          },
        ),
      );

      final result = await repository.signInWithGoogle();

      expect(result.isFailure, isTrue);
      expect(result.isCancelled, isTrue);
      expect(result.failure?.message, '登录已取消');
    },
  );

  test('registerWithEmail maps missing credential user to failure', () async {
    final repository = GatewayAuthRepository(
      authGateway: _FakeAuthGateway(
        registerWithEmailHandler: ({required email, required password}) async {
          return _FakeUserCredential(null);
        },
      ),
    );

    final result = await repository.registerWithEmail(
      email: 'user@example.com',
      password: 'secret123',
    );

    expect(result.isFailure, isTrue);
    expect(result.failure?.code, 'missing-user');
    expect(result.failure?.message, '认证成功但未返回用户信息');
  });

  test(
    'exposes current user and auth stream through repository seam',
    () async {
      final controller = StreamController<User?>.broadcast();
      final currentUser = _FakeUser('user@example.com');
      final repository = GatewayAuthRepository(
        authGateway: _FakeAuthGateway(
          currentUserValue: currentUser,
          authStateChangesValue: controller.stream,
          signInWithGoogleHandler: () async {
            return _FakeUserCredential(currentUser);
          },
        ),
      );
      addTearDown(controller.close);

      expect(repository.currentUser?.email, 'user@example.com');
      expectLater(repository.authStateChanges, emitsInOrder([isNull]));

      controller.add(null);
    },
  );
}
