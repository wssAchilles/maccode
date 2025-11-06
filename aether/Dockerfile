# ========================================
# Stage 1: Build Stage
# 使用 Maven 构建 Spring Boot 应用
# ========================================
FROM eclipse-temurin:17-jdk-jammy AS builder

# 设置工作目录
WORKDIR /app

# 复制 Maven Wrapper 文件（用于构建）
COPY .mvn/ .mvn/
COPY mvnw mvnw.cmd ./

# 赋予 mvnw 执行权限
RUN chmod +x mvnw

# 复制 pom.xml（先复制依赖文件，利用 Docker 缓存）
COPY pom.xml ./

# 下载所有依赖（缓存此层）
RUN ./mvnw dependency:go-offline -B

# 复制源代码
COPY src ./src

# 构建应用（跳过测试以加速构建）
RUN ./mvnw package -DskipTests -B

# ========================================
# Stage 2: Runtime Stage
# 使用更小的 JRE 镜像运行应用
# ========================================
FROM eclipse-temurin:17-jre-jammy

# 设置工作目录
WORKDIR /app

# 从构建阶段复制 JAR 文件
COPY --from=builder /app/target/*.jar app.jar

# 暴露端口
EXPOSE 8080

# 设置 JVM 参数（可选，优化生产环境）
ENV JAVA_OPTS="-Xmx512m -Xms256m"

# 健康检查（可选）
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/actuator/health || exit 1

# 启动应用
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
