# Web (Spring MVC + JPA) 示例项目

一个可部署到 Tomcat 的传统 WAR 工程，基于：
- Spring MVC 5.x
- Spring Data JPA + Hibernate 5.x
- HikariCP 连接池
- H2 内存数据库（默认），可切换 MySQL
- JSP + JSTL
- Logback 日志
- JUnit 5 + Spring Test

## 快速开始

1) 运行测试

```bash
mvn test
```

2) 打包 WAR

```bash
mvn package -DskipTests
```

3) 部署

将 `target/web.war` 拷贝到 Tomcat 的 `webapps/` 目录，启动后访问：

- http://localhost:8080/web/
- http://localhost:8080/web/actuator/health

## 切换到 MySQL

在启动容器时设置系统属性或在 Tomcat 的 setenv 脚本中添加：

```bash
-Dapp.jdbc.url=jdbc:mysql://localhost:3306/webdb?useSSL=false&serverTimezone=UTC
-Dapp.jdbc.username=root
-Dapp.jdbc.password=yourpass
-Dapp.jpa.dialect=org.hibernate.dialect.MySQL8Dialect
```

## 结构

- `org.example.config.AppConfig`：数据源、JPA、事务
- `org.example.config.WebConfig`：Spring MVC、视图解析、静态资源
- `org.example.controller.*`：控制器与全局异常处理
- `org.example.domain.User`：实体
- `org.example.repository.UserRepository`：仓库
- `org.example.service.*`：服务
- `src/main/webapp/WEB-INF/views`：JSP 视图

## 常见问题

- JSP 404：确认视图解析器前后缀，JSP 位于 `/WEB-INF/views/` 下。
- 数据库连接失败：检查 `app.jdbc.*` 参数与驱动。
- 中文乱码：已配置 UTF-8 过滤器，确保 Tomcat 使用 UTF-8 URIEncoding。

