part of '../optimization_result.dart';

Map<String, dynamic>? _toStringDynamicMap(Object? value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map) {
    return value.map((key, entryValue) => MapEntry(key.toString(), entryValue));
  }
  return null;
}

List<String>? _toStringList(Object? value) {
  if (value is! List) {
    return null;
  }
  return value.map((entry) => entry.toString()).toList();
}

List<double>? _toDoubleList(Object? value) {
  if (value is! List) {
    return null;
  }
  return value
      .map((entry) => _toNullableDouble(entry))
      .whereType<double>()
      .toList();
}

List<int>? _toIntList(Object? value) {
  if (value is! List) {
    return null;
  }
  return value.map((entry) => _toNullableInt(entry)).whereType<int>().toList();
}

String? _toNullableString(Object? value) {
  if (value == null) {
    return null;
  }
  return value.toString();
}

int? _toNullableInt(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value.trim());
  }
  return null;
}

double? _toNullableDouble(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value.trim());
  }
  return null;
}

bool? _toNullableBool(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  if (value is String) {
    switch (value.trim().toLowerCase()) {
      case '1':
      case 'true':
      case 'yes':
      case 'y':
        return true;
      case '0':
      case 'false':
      case 'no':
      case 'n':
        return false;
    }
  }
  return null;
}

Object? _firstPresent(Map<String, dynamic> json, List<String> keys) {
  for (final key in keys) {
    if (json.containsKey(key)) {
      return json[key];
    }
  }
  return null;
}
