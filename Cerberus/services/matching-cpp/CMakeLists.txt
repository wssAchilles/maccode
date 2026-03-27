cmake_minimum_required(VERSION 3.20)
project(cerberus_matching LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BUILD_TESTING "Build tests" ON)
option(ENABLE_GRPC_SERVICE "Build gRPC server for matching service when dependencies are available" ON)
option(REQUIRE_GRPC_SERVICE "Fail configure when gRPC service cannot be built" OFF)

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
set(CERBERUS_PROTO_INCLUDE_DIR "")
set(CERBERUS_GRPC_SERVICE_BUILT OFF)

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
    set(CERBERUS_PROTO_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/proto)
    set(CERBERUS_PROTO_GEN_DIR ${CMAKE_CURRENT_BINARY_DIR}/generated)
    set(CERBERUS_ORDER_PROTO ${CERBERUS_PROTO_ROOT}/cerberus/order/v1/order.proto)
    set(CERBERUS_PROTO_INCLUDE_DIR ${CERBERUS_PROTO_GEN_DIR})
    file(MAKE_DIRECTORY ${CERBERUS_PROTO_GEN_DIR})

    set(CERBERUS_PROTOC_EXECUTABLE "")
    if(TARGET protobuf::protoc)
      set(CERBERUS_PROTOC_EXECUTABLE $<TARGET_FILE:protobuf::protoc>)
    elseif(TARGET Protobuf::protoc)
      set(CERBERUS_PROTOC_EXECUTABLE $<TARGET_FILE:Protobuf::protoc>)
    elseif(DEFINED Protobuf_PROTOC_EXECUTABLE AND NOT Protobuf_PROTOC_EXECUTABLE STREQUAL "")
      set(CERBERUS_PROTOC_EXECUTABLE ${Protobuf_PROTOC_EXECUTABLE})
    else()
      find_program(CERBERUS_PROTOC_EXECUTABLE protoc REQUIRED)
    endif()

    get_target_property(GRPC_CPP_PLUGIN_EXECUTABLE gRPC::grpc_cpp_plugin IMPORTED_LOCATION)
    if(NOT GRPC_CPP_PLUGIN_EXECUTABLE)
      find_program(GRPC_CPP_PLUGIN_EXECUTABLE grpc_cpp_plugin REQUIRED)
    endif()

    add_custom_command(
      OUTPUT
        ${CERBERUS_PROTO_GEN_DIR}/cerberus/order/v1/order.pb.cc
        ${CERBERUS_PROTO_GEN_DIR}/cerberus/order/v1/order.pb.h
        ${CERBERUS_PROTO_GEN_DIR}/cerberus/order/v1/order.grpc.pb.cc
        ${CERBERUS_PROTO_GEN_DIR}/cerberus/order/v1/order.grpc.pb.h
      COMMAND ${CERBERUS_PROTOC_EXECUTABLE}
      ARGS
        --proto_path=${CERBERUS_PROTO_ROOT}
        --cpp_out=${CERBERUS_PROTO_GEN_DIR}
        --grpc_out=${CERBERUS_PROTO_GEN_DIR}
        --plugin=protoc-gen-grpc=${GRPC_CPP_PLUGIN_EXECUTABLE}
        ${CERBERUS_ORDER_PROTO}
      DEPENDS ${CERBERUS_ORDER_PROTO}
      COMMENT "Generating C++ protobuf/grpc sources for order.proto"
      VERBATIM
    )

    add_library(cerberus_proto STATIC
      ${CERBERUS_PROTO_GEN_DIR}/cerberus/order/v1/order.pb.cc
      ${CERBERUS_PROTO_GEN_DIR}/cerberus/order/v1/order.grpc.pb.cc
    )
    target_include_directories(cerberus_proto PUBLIC ${CERBERUS_PROTO_INCLUDE_DIR})
    target_link_libraries(cerberus_proto PUBLIC ${PROTOBUF_LIB_TARGET} gRPC::grpc++ gRPC::grpc)

    add_library(grpc_order_service
      src/grpc_order_service_mapping.cpp
      src/grpc_order_service_common.cpp
      src/grpc_order_service_context.cpp
      src/grpc_order_service_backpressure.cpp
      src/grpc_order_service_telemetry.cpp
      src/grpc_order_service_submit.cpp
      src/grpc_order_service_order_lifecycle.cpp
      src/grpc_order_service_orderbook.cpp
      src/grpc_order_service_executions.cpp
      src/grpc_order_service_health_stats.cpp
    )
    target_include_directories(grpc_order_service PUBLIC
      ${CMAKE_CURRENT_SOURCE_DIR}/src
      ${CERBERUS_PROTO_INCLUDE_DIR}
    )
    target_link_libraries(grpc_order_service PUBLIC matching_engine cerberus_proto)

    set(MATCHING_SERVICE_SOURCES
      src/main_grpc.cpp
      src/runtime_config.cpp
      src/runtime_env.cpp
    )
    set(MATCHING_SERVICE_LIBRARIES grpc_order_service)
    set(CERBERUS_GRPC_SERVICE_BUILT ON)

    message(STATUS "gRPC dependencies detected, building matching_service with gRPC.")
  else()
    message(WARNING "gRPC/Protobuf not found, building fallback matching_service without network RPC.")
  endif()
endif()

if(REQUIRE_GRPC_SERVICE AND NOT CERBERUS_GRPC_SERVICE_BUILT)
  message(FATAL_ERROR "REQUIRE_GRPC_SERVICE=ON but gRPC service could not be built. Install gRPC/protobuf deps or disable REQUIRE_GRPC_SERVICE.")
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

  if(CERBERUS_GRPC_SERVICE_BUILT)
    add_executable(
      grpc_order_service_mapping_test
      tests/test_grpc_mapping.cpp
      src/grpc_order_service_mapping.cpp
    )
    target_include_directories(grpc_order_service_mapping_test PRIVATE
      ${CMAKE_CURRENT_SOURCE_DIR}/src
      ${CERBERUS_PROTO_INCLUDE_DIR}
    )
    target_link_libraries(grpc_order_service_mapping_test PRIVATE
      matching_engine
      cerberus_proto
    )
    add_test(NAME grpc_order_service_mapping_test COMMAND grpc_order_service_mapping_test)
  endif()
endif()
