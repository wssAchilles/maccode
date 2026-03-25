FROM debian:bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ca-certificates pkg-config \
    libgrpc++-dev libprotobuf-dev protobuf-compiler protobuf-compiler-grpc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY . .
ARG ENABLE_GRPC_SERVICE=ON
RUN rm -rf build && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DENABLE_GRPC_SERVICE=${ENABLE_GRPC_SERVICE} -DBUILD_TESTING=OFF \
    && cmake --build build -j

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libgrpc++1.51 libprotobuf32 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /src/build/matching_service /usr/local/bin/matching_service
CMD ["matching_service"]
