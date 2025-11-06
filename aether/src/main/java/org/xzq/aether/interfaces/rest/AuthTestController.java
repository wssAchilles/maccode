package org.xzq.aether.interfaces.rest;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.xzq.aether.domain.user.User;

import java.util.HashMap;
import java.util.Map;

/**
 * 认证测试控制器
 * 职责: 提供端点用于测试 Firebase 认证流程
 * 
 * 这是 Milestone 1 的验证端点
 */
@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class AuthTestController {

    /**
     * 获取当前认证用户信息
     * 用于测试认证是否成功
     * 
     * @return 用户信息
     */
    @GetMapping("/me")
    public ResponseEntity<Map<String, Object>> getCurrentUser() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        
        if (authentication == null || !authentication.isAuthenticated()) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "Unauthorized",
                    "message", "未认证"
            ));
        }

        // 从认证上下文中获取 User 实体
        User user = (User) authentication.getPrincipal();

        Map<String, Object> response = new HashMap<>();
        response.put("uid", user.getUid());
        response.put("email", user.getEmail());
        response.put("username", user.getUsername());
        response.put("avatarUrl", user.getAvatarUrl());
        response.put("createdAt", user.getCreatedAt());
        response.put("updatedAt", user.getUpdatedAt());

        return ResponseEntity.ok(response);
    }

    /**
     * 公开端点 (无需认证)
     * 用于测试服务器是否正常运行
     * 
     * @return 健康检查信息
     */
    @GetMapping("/public/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of(
                "status", "UP",
                "message", "aether API 正常运行",
                "timestamp", java.time.Instant.now().toString()
        ));
    }
}
