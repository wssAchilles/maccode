package org.xzq.aether.infrastructure.config;

import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.xzq.aether.application.security.FirebaseTokenFilter;

import java.util.Arrays;

/**
 * Spring Security 核心配置
 * 职责: 配置认证和授权策略
 * 
 * 架构原则:
 * 1. 无状态 (Stateless) - 不使用 Session
 * 2. JWT 认证 - 使用 Firebase Token
 * 3. CORS 支持 - 允许前端跨域访问
 * 4. 方法级安全 - 启用 @PreAuthorize 注解
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity(prePostEnabled = true)
@RequiredArgsConstructor
public class SecurityConfig {

    private final FirebaseTokenFilter firebaseTokenFilter;

    /**
     * 配置安全过滤链
     */
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                // 禁用 CSRF (因为使用 JWT，无状态)
                .csrf(AbstractHttpConfigurer::disable)
                
                // 配置 CORS
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                
                // 禁用 Session (使用无状态策略)
                .sessionManagement(session -> 
                        session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                
                // 配置请求授权
                .authorizeHttpRequests(authz -> authz
                        // 公开端点 (无需认证)
                        .requestMatchers(
                                "/api/v1/auth/public/**",
                                "/swagger-ui/**",
                                "/swagger-ui.html",
                                "/v3/api-docs/**",
                                "/swagger-resources/**",
                                "/webjars/**",
                                "/actuator/health",
                                "/actuator/info",
                                "/ws/**" // WebSocket 端点
                        ).permitAll()
                        
                        // 所有其他请求都需要认证
                        .anyRequest().authenticated()
                )
                
                // 添加 Firebase Token 认证过滤器
                // 必须在 UsernamePasswordAuthenticationFilter 之前
                .addFilterBefore(firebaseTokenFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    /**
     * 配置 CORS (跨域资源共享)
     * 允许前端 (Next.js) 访问后端 API
     */
    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        
        // 允许的前端域名
        configuration.setAllowedOrigins(Arrays.asList(
                "http://localhost:3000",      // Next.js 开发环境
                "http://localhost:3001",      // 备用端口
                "https://aether.example.com"  // 生产环境 (根据实际修改)
        ));
        
        // 允许的 HTTP 方法
        configuration.setAllowedMethods(Arrays.asList(
                "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"
        ));
        
        // 允许的请求头
        configuration.setAllowedHeaders(Arrays.asList("*"));
        
        // 允许携带凭证 (Cookies)
        configuration.setAllowCredentials(true);
        
        // 暴露的响应头
        configuration.setExposedHeaders(Arrays.asList(
                "Authorization",
                "Content-Type",
                "X-Total-Count"
        ));
        
        // 预检请求的缓存时间 (秒)
        configuration.setMaxAge(3600L);
        
        // 应用配置到所有路径
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        
        return source;
    }
}
