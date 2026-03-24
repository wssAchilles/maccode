FROM debian:bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY . .
ARG ENABLE_GRPC_SERVICE=OFF
RUN rm -rf build && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DENABLE_GRPC_SERVICE=${ENABLE_GRPC_SERVICE} \
    && cmake --build build -j

FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /src/build/matching_service /usr/local/bin/matching_service
CMD ["matching_service"]
