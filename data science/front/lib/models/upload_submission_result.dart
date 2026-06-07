library;

class UploadSubmissionResult {
  const UploadSubmissionResult({
    required this.uploadUrl,
    required this.storagePath,
  });

  factory UploadSubmissionResult.fromJson(Map<String, dynamic> json) {
    final uploadUrl = json['uploadUrl'];
    final storagePath = json['storagePath'];
    if (uploadUrl is! String ||
        uploadUrl.isEmpty ||
        storagePath is! String ||
        storagePath.isEmpty) {
      throw const FormatException(
        'Upload response is missing required fields.',
      );
    }
    return UploadSubmissionResult(
      uploadUrl: uploadUrl,
      storagePath: storagePath,
    );
  }

  final String uploadUrl;
  final String storagePath;
}
