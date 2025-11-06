package org.xzq.aether.infrastructure.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * OpenAPI (Swagger) 配置
 * 职责: 为 RESTful API 提供交互式文档
 * 
 * 访问地址:
 * - Swagger UI: http://localhost:8080/swagger-ui.html
 * - API Docs: http://localhost:8080/v3/api-docs
 */
@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI aetherOpenAPI() {
        return new OpenAPI()
            .info(new Info()
                .title("aether API")
                .version("v1.0")
                .description("""
                    一个基于 Spring Boot 和 Firebase 的实时、敏捷项目协作平台。
                    
                    **认证方式:**
                    - 使用 Firebase ID Token 作为 Bearer Token
                    - 在 Authorization 请求头中添加: `Bearer <your-firebase-id-token>`
                    
                    **核心功能:**
                    - 项目管理 (Projects)
                    - 看板管理 (Boards)
                    - 卡片管理 (Cards)
                    - 实时协作 (WebSocket)
                    """)
                .contact(new Contact()
                    .name("aether Team")
                    .email("support@aether.com"))
                .license(new License()
                    .name("Apache 2.0")
                    .url("https://www.apache.org/licenses/LICENSE-2.0.html")))
            // 添加全局安全要求
            .addSecurityItem(new SecurityRequirement()
                .addList("bearerAuth"))
            // 定义安全方案
            .components(new Components()
                .addSecuritySchemes("bearerAuth", new SecurityScheme()
                    .name("bearerAuth")
                    .type(SecurityScheme.Type.HTTP)
                    .scheme("bearer")
                    .bearerFormat("JWT")
                    .description("Firebase ID Token (从 Firebase Authentication 获取)")));
    }
}
