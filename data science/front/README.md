# Sentinel Ops Frontend

Flutter multi-platform client for the data-science-as-a-service workspace.

## Product Shape

The app is an authenticated operations console with five workspaces:

- 概览: operations hub, asset chains, approvals, control tasks, runtime console
- 能源优化: battery and power optimization workflows
- 数据分析: CSV upload, analysis, quality review, background analysis jobs
- AI Lab: deep learning training and RAG ingestion/chat workflows
- 历史与审计: job history, audit trail, analysis details, asset ledger

The UI follows the existing MVVM-style flow:

```text
Widget/Screen -> ChangeNotifier ViewModel -> Repository/Gateway -> ApiService/Firebase
```

## Runtime Configuration

API endpoints can be overridden at build time:

```bash
flutter run --dart-define=API_BASE_URL=http://localhost:8080
flutter run --dart-define=HEAVY_API_BASE_URL=http://localhost:8000
```

Default development endpoints are selected per platform in `lib/config/constants.dart`.

## Common Commands

```bash
flutter pub get
rtk flutter analyze
rtk flutter test
```

Run a focused test file:

```bash
rtk flutter test test/viewmodels/data_analysis_view_model_test.dart
```

## Architecture Notes

- `MainShellRuntimeViewModel` is a facade over smaller shell runtime pieces: navigation state, workspace runtime registry, projection building, and operation runtime control.
- Screens should remain layout and event-forwarding surfaces. Cross-viewmodel workflows belong in coordinators.
- New motion behavior should use `lib/motion/` tokens and sequence helpers instead of hardcoded durations and curves.
- New API boundaries should prefer typed DTO/model objects over raw `Map<String, dynamic>` in ViewModels.
