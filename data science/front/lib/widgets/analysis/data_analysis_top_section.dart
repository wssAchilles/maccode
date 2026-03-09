/// 数据分析页顶部编排组件
library;

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../auth/data_analysis_auth_form.dart';
import '../auth/user_info_widget.dart';
import 'file_picker_widget.dart';

class DataAnalysisTopSection extends StatelessWidget {
  const DataAnalysisTopSection({
    super.key,
    required this.currentUser,
    required this.pickedFile,
    required this.saveToStorage,
    required this.formKey,
    required this.emailController,
    required this.passwordController,
    required this.authMode,
    required this.onSignInWithEmail,
    required this.onRegisterWithEmail,
    required this.onToggleAuthMode,
    required this.onGoogleSignIn,
    required this.onPickFile,
    required this.onClearFile,
    required this.onStorageChanged,
  });

  final User? currentUser;
  final PlatformFile? pickedFile;
  final bool saveToStorage;
  final GlobalKey<FormState> formKey;
  final TextEditingController emailController;
  final TextEditingController passwordController;
  final String authMode;
  final VoidCallback onSignInWithEmail;
  final VoidCallback onRegisterWithEmail;
  final VoidCallback onToggleAuthMode;
  final VoidCallback onGoogleSignIn;
  final VoidCallback onPickFile;
  final VoidCallback onClearFile;
  final ValueChanged<bool> onStorageChanged;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth > 960) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: _buildUserSection()),
              const SizedBox(width: 24),
              Expanded(child: _buildFileSection()),
            ],
          );
        }

        return Column(
          children: [
            _buildUserSection(),
            const SizedBox(height: 24),
            _buildFileSection(),
          ],
        );
      },
    );
  }

  Widget _buildUserSection() {
    if (currentUser == null) {
      return DataAnalysisAuthForm(
        formKey: formKey,
        emailController: emailController,
        passwordController: passwordController,
        authMode: authMode,
        onSignInWithEmail: onSignInWithEmail,
        onRegisterWithEmail: onRegisterWithEmail,
        onToggleAuthMode: onToggleAuthMode,
        onGoogleSignIn: onGoogleSignIn,
      );
    }

    return UserInfoWidget(user: currentUser!);
  }

  Widget _buildFileSection() {
    return FilePickerWidget(
      selectedFile: pickedFile,
      isLoggedIn: currentUser != null,
      saveToStorage: saveToStorage,
      onPickFile: onPickFile,
      onClearFile: onClearFile,
      onStorageChanged: onStorageChanged,
    );
  }
}
