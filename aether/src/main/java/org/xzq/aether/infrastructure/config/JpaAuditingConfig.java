package org.xzq.aether.infrastructure.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * JPA 审计配置 + 异步支持
 * 职责: 启用 JPA 自动审计功能和异步事件处理
 * 
 * 功能:
 * - 自动填充 @CreatedDate 字段 (创建时间)
 * - 自动填充 @LastModifiedDate 字段 (最后更新时间)
 * - 启用 @Async 注解支持，用于异步事件监听器
 */
@Configuration
@EnableJpaAuditing
@EnableAsync
public class JpaAuditingConfig {
    // 配置类，无需额外代码
    // @EnableJpaAuditing 注解会自动激活审计功能
    // @EnableAsync 注解会启用异步方法执行能力
}
