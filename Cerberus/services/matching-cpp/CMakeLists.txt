cmake_minimum_required(VERSION 3.20)
project(cerberus_matching LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BUILD_TESTING "Build tests" ON)
option(ENABLE_GRPC_SERVICE "Build gRPC server for matching service when dependencies are available" ON)

add_library(matching_engine
  src/matching_engine_submit.cpp
  src/matching_engine_manage.cpp
  src/matching_engine_view.cpp
  src/order_service_submit.cpp
  src/order_service_query.cpp
  src/order_service_state.cpp
)
target_include_directories(matching_engine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)

set(MATCHING_SERVICE_SOURCES src/main.cpp)
set(MATCHING_SERVICE_LIBRARIES matching_engine)

if(ENABLE_GRPC_SERVICE)
  find_package(gRPC QUIET)
  set(PROTOBUF_LIB_TARGET "")
  if(TARGET protobuf::libprotobuf)
    set(PROTOBUF_LIB_TARGET protobuf::libprotobuf)
  elseif(TARGET Protobuf::libprotobuf)
    set(PROTOBUF_LIB_TARGET Protobuf::libprotobuf)
  else()
    find_package(Protobuf QUIET)
    if(TARGET protobuf::libprotobuf)
      set(PROTOBUF_LIB_TARGET protobuf::libprotobuf)
    elseif(TARGET Protobuf::libprotobuf)
      set(PROTOBUF_LIB_TARGET Protobuf::libprotobuf)
    endif()
  endif()

  if(gRPC_FOUND AND NOT PROTOBUF_LIB_TARGET STREQUAL "")
    add_library(cerberus_proto STATIC
      gen/cerberus/order/v1/order.pb.cc
      gen/cerberus/order/v1/order.grpc.pb.cc
      gen/cerberus/market/v1/market.pb.cc
      gen/cerberus/market/v1/market.grpc.pb.cc
      gen/cerberus/strategy/v1/strategy.pb.cc
      gen/cerberus/strategy/v1/strategy.grpc.pb.cc
    )
    target_include_directories(cerberus_proto PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/gen)
    target_link_libraries(cerberus_proto PUBLIC ${PROTOBUF_LIB_TARGET} gRPC::grpc++ gRPC::grpc)

    add_library(grpc_order_service
      src/grpc_order_service_common.cpp
      src/grpc_order_service_submit.cpp
      src/grpc_order_service_order_lifecycle.cpp
      src/grpc_order_service_orderbook.cpp
      src/grpc_order_service_executions.cpp
      src/grpc_order_service_health_stats.cpp
    )
    target_include_directories(grpc_order_service PUBLIC
      ${CMAKE_CURRENT_SOURCE_DIR}/src
      ${CMAKE_CURRENT_SOURCE_DIR}/gen
    )
    target_link_libraries(grpc_order_service PUBLIC matching_engine cerberus_proto)

    set(MATCHING_SERVICE_SOURCES src/main_grpc.cpp)
    set(MATCHING_SERVICE_LIBRARIES grpc_order_service)

    message(STATUS "gRPC dependencies detected, building matching_service with gRPC.")
  else()
    message(WARNING "gRPC/Protobuf not found, building fallback matching_service without network RPC.")
  endif()
endif()

add_executable(matching_service ${MATCHING_SERVICE_SOURCES})
target_link_libraries(matching_service PRIVATE ${MATCHING_SERVICE_LIBRARIES})

if(BUILD_TESTING)
  include(CTest)
  include(FetchContent)

  FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/tags/v1.15.2.zip
  )

  set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
  FetchContent_MakeAvailable(googletest)

  add_executable(matching_engine_test tests/test_matching.cpp)
  target_link_libraries(matching_engine_test PRIVATE matching_engine GTest::gtest_main)

  include(GoogleTest)
  gtest_discover_tests(matching_engine_test)
endif()
