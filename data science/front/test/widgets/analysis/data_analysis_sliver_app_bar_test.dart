import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/widgets/analysis/data_analysis_sliver_app_bar.dart';

void main() {
  testWidgets('hides history and signout actions when logged out', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CustomScrollView(
            slivers: [
              DataAnalysisSliverAppBar(
                isLoggedIn: false,
                onOpenHistory: () {},
                onSignOut: () {},
              ),
              const SliverToBoxAdapter(child: SizedBox(height: 200)),
            ],
          ),
        ),
      ),
    );

    expect(find.byIcon(Icons.history_rounded), findsNothing);
    expect(find.byIcon(Icons.logout_rounded), findsNothing);
  });

  testWidgets('shows actions and triggers callbacks when logged in', (
    WidgetTester tester,
  ) async {
    var historyTapped = false;
    var signOutTapped = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CustomScrollView(
            slivers: [
              DataAnalysisSliverAppBar(
                isLoggedIn: true,
                onOpenHistory: () => historyTapped = true,
                onSignOut: () => signOutTapped = true,
              ),
              const SliverToBoxAdapter(child: SizedBox(height: 200)),
            ],
          ),
        ),
      ),
    );

    expect(find.byIcon(Icons.history_rounded), findsOneWidget);
    expect(find.byIcon(Icons.logout_rounded), findsOneWidget);

    await tester.tap(find.byIcon(Icons.history_rounded));
    await tester.pump();
    expect(historyTapped, isTrue);

    await tester.tap(find.byIcon(Icons.logout_rounded));
    await tester.pump();
    expect(signOutTapped, isTrue);
  });
}
