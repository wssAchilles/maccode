#include "runtime_env.hpp"

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <string>

int ReadBoundedIntEnv(const char* key, int default_value, int min_value, int max_value) {
  const char* raw = std::getenv(key);
  if (raw == nullptr || *raw == '\0') {
    return default_value;
  }
  try {
    const int parsed = std::stoi(std::string(raw));
    if (parsed < min_value || parsed > max_value) {
      std::cerr << "env " << key << "=" << raw << " out of range [" << min_value << ", "
                << max_value << "], clamped to " << std::clamp(parsed, min_value, max_value)
                << std::endl;
    }
    return std::clamp(parsed, min_value, max_value);
  } catch (...) {
    std::cerr << "env " << key << "=" << raw << " invalid, fallback to " << default_value
              << std::endl;
    return default_value;
  }
}

std::size_t ReadBoundedSizeEnv(const char* key, std::size_t default_value, std::size_t min_value,
                               std::size_t max_value) {
  const char* raw = std::getenv(key);
  if (raw == nullptr || *raw == '\0') {
    return default_value;
  }
  try {
    const auto parsed = static_cast<std::size_t>(std::stoull(std::string(raw)));
    if (parsed < min_value || parsed > max_value) {
      std::cerr << "env " << key << "=" << raw << " out of range [" << min_value << ", "
                << max_value << "], clamped to " << std::clamp(parsed, min_value, max_value)
                << std::endl;
    }
    return std::clamp(parsed, min_value, max_value);
  } catch (...) {
    std::cerr << "env " << key << "=" << raw << " invalid, fallback to " << default_value
              << std::endl;
    return default_value;
  }
}

std::uint64_t ReadBoundedU64Env(const char* key, std::uint64_t default_value,
                                std::uint64_t min_value, std::uint64_t max_value) {
  const char* raw = std::getenv(key);
  if (raw == nullptr || *raw == '\0') {
    return default_value;
  }
  try {
    const auto parsed = static_cast<std::uint64_t>(std::stoull(std::string(raw)));
    if (parsed < min_value || parsed > max_value) {
      std::cerr << "env " << key << "=" << raw << " out of range [" << min_value << ", "
                << max_value << "], clamped to " << std::clamp(parsed, min_value, max_value)
                << std::endl;
    }
    return std::clamp(parsed, min_value, max_value);
  } catch (...) {
    std::cerr << "env " << key << "=" << raw << " invalid, fallback to " << default_value
              << std::endl;
    return default_value;
  }
}
