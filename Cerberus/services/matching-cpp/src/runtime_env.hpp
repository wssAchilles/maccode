#pragma once

#include <cstddef>
#include <cstdint>

int ReadBoundedIntEnv(const char* key, int default_value, int min_value, int max_value);
std::size_t ReadBoundedSizeEnv(const char* key, std::size_t default_value, std::size_t min_value,
                               std::size_t max_value);
std::uint64_t ReadBoundedU64Env(const char* key, std::uint64_t default_value,
                                std::uint64_t min_value, std::uint64_t max_value);
