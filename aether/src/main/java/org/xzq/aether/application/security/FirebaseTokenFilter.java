package org.xzq.aether.application.security;

import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseAuthException;
import com.google.firebase.auth.FirebaseToken;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.lang.NonNull;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.xzq.aether.application.service.UserAppService;
import org.xzq.aether.domain.user.User;

import java.io.IOException;
import java.util.Collections;

/**
 * Firebase Token 认证过滤器
 * 职责: 拦截所有 HTTP 请求，验证 Firebase JWT Token，并同步用户信息
 * 
 * 架构原则:
 * 1. 认证优先 (Authentication-First) - Firebase 负责验证用户身份
 * 2. 用户同步 (User Sync) - 将 Firebase 用户同步到本地数据库
 * 3. 安全上下文 (Security Context) - 将认证信息设置到 Spring Security 上下文
 * 
 * 这是认证闭环的核心组件
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class FirebaseTokenFilter extends OncePerRequestFilter {

    private final UserAppService userAppService;

    @Override
    protected void doFilterInternal(
            @NonNull HttpServletRequest request,
            @NonNull HttpServletResponse response,
            @NonNull FilterChain filterChain
    ) throws ServletException, IOException {

        try {
            // 1. 提取 Token
            String token = extractTokenFromRequest(request);

            if (token != null) {
                // 2. 验证 Firebase Token
                FirebaseToken decodedToken = verifyFirebaseToken(token);

                if (decodedToken != null) {
                    // 3. 同步用户信息到本地数据库
                    User user = userAppService.syncUser(decodedToken);

                    // 4. 设置 Spring Security 认证上下文
                    setAuthentication(user, request);

                    log.debug("认证成功: uid={}, email={}", user.getUid(), user.getEmail());
                }
            }

        } catch (FirebaseAuthException e) {
            log.warn("Firebase Token 验证失败: {}", e.getMessage());
            clearSecurityContext();
            sendUnauthorizedResponse(response, "Invalid Firebase Token");
            return; // 不继续执行过滤链

        } catch (IllegalArgumentException e) {
            log.warn("Token 格式错误: {}", e.getMessage());
            clearSecurityContext();
            sendUnauthorizedResponse(response, "Malformed Token");
            return; // 不继续执行过滤链

        } catch (Exception e) {
            log.error("认证过程中发生未知错误", e);
            clearSecurityContext();
            sendUnauthorizedResponse(response, "Authentication Error");
            return; // 不继续执行过滤链
        }

        // 5. 继续过滤链
        filterChain.doFilter(request, response);
    }

    /**
     * 从 HTTP 请求中提取 Bearer Token
     * 
     * @param request HTTP 请求
     * @return JWT Token (不含 "Bearer " 前缀)，如果不存在则返回 null
     */
    private String extractTokenFromRequest(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");

        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7); // 移除 "Bearer " 前缀
        }

        return null;
    }

    /**
     * 验证 Firebase Token
     * 
     * @param token JWT Token
     * @return 解码后的 Firebase Token
     * @throws FirebaseAuthException 如果验证失败
     */
    private FirebaseToken verifyFirebaseToken(String token) throws FirebaseAuthException {
        try {
            return FirebaseAuth.getInstance().verifyIdToken(token);
        } catch (FirebaseAuthException e) {
            log.error("Firebase Token 验证失败: {}", e.getMessage());
            throw e;
        }
    }

    /**
     * 设置 Spring Security 认证上下文
     * 
     * @param user 用户实体
     * @param request HTTP 请求
     */
    private void setAuthentication(User user, HttpServletRequest request) {
        // 创建认证 Token
        // Principal: User 实体 (方便在 @PreAuthorize 中使用)
        // Credentials: null (无密码)
        // Authorities: 空集合 (暂时不使用角色，后续通过 @PreAuthorize 实现细粒度权限控制)
        UsernamePasswordAuthenticationToken authentication =
                new UsernamePasswordAuthenticationToken(
                        user,
                        null,
                        Collections.emptyList()
                );

        // 设置请求详情
        authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

        // 将认证信息设置到安全上下文
        SecurityContextHolder.getContext().setAuthentication(authentication);
    }

    /**
     * 清除 Spring Security 上下文
     */
    private void clearSecurityContext() {
        SecurityContextHolder.clearContext();
    }

    /**
     * 发送 401 Unauthorized 响应
     * 
     * @param response HTTP 响应
     * @param message 错误消息
     * @throws IOException IO 异常
     */
    private void sendUnauthorizedResponse(
            HttpServletResponse response,
            String message
    ) throws IOException {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType("application/json");
        response.setCharacterEncoding("UTF-8");
        
        String jsonResponse = String.format(
                "{\"error\": \"Unauthorized\", \"message\": \"%s\"}",
                message
        );
        
        response.getWriter().write(jsonResponse);
        response.getWriter().flush();
    }

    /**
     * 判断是否应该跳过此过滤器
     * 对于公开端点 (如 Swagger, Actuator)，可以跳过认证
     */
    @Override
    protected boolean shouldNotFilter(@NonNull HttpServletRequest request) {
        String path = request.getRequestURI();
        
        // 公开端点列表
        return path.startsWith("/swagger-ui") ||
               path.startsWith("/v3/api-docs") ||
               path.startsWith("/actuator/health") ||
               path.startsWith("/actuator/info") ||
               path.startsWith("/api/v1/auth/public");
    }
}
