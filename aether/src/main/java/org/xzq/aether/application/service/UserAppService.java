package org.xzq.aether.application.service;

import com.google.firebase.auth.FirebaseToken;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.xzq.aether.domain.user.User;
import org.xzq.aether.domain.user.UserRepository;

/**
 * 用户应用服务 (User Application Service)
 * 职责: 协调用户领域的业务流程，特别是 Firebase 用户同步
 * 
 * DDD 原则: 这是应用服务层，保持"薄"，主要用于协调领域对象
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class UserAppService {

    private final UserRepository userRepository;

    /**
     * 同步 Firebase 用户到本地数据库
     * 
     * 流程:
     * 1. 检查用户是否已存在 (通过 Firebase UID)
     * 2. 如果不存在，创建新用户
     * 3. 如果已存在，检查并更新用户信息 (如果有变更)
     * 
     * @param decodedToken Firebase 解码后的 Token
     * @return 同步后的用户实体
     */
    @Transactional
    public User syncUser(FirebaseToken decodedToken) {
        String uid = decodedToken.getUid();
        String email = decodedToken.getEmail();
        String username = decodedToken.getName();
        String avatarUrl = decodedToken.getPicture();

        log.debug("开始同步 Firebase 用户: uid={}, email={}", uid, email);

        // 检查用户是否已存在
        return userRepository.findById(uid)
                .map(existingUser -> {
                    // 用户已存在，检查是否需要更新
                    boolean hasChanges = existingUser.updateFromFirebase(email, username, avatarUrl);
                    
                    if (hasChanges) {
                        log.info("更新现有用户信息: uid={}, email={}", uid, email);
                        return userRepository.save(existingUser);
                    } else {
                        log.debug("用户信息无变更: uid={}", uid);
                        return existingUser;
                    }
                })
                .orElseGet(() -> {
                    // 用户不存在，创建新用户
                    log.info("创建新用户: uid={}, email={}", uid, email);
                    
                    User newUser = User.builder()
                            .uid(uid)
                            .email(email != null ? email : uid + "@unknown.com") // 防止 email 为 null
                            .username(username != null ? username : "User_" + uid.substring(0, 8)) // 默认用户名
                            .avatarUrl(avatarUrl)
                            .build();
                    
                    return userRepository.save(newUser);
                });
    }

    /**
     * 通过 UID 获取用户
     * 
     * @param uid Firebase UID
     * @return 用户实体 (如果存在)
     */
    @Transactional(readOnly = true)
    public User getUserByUid(String uid) {
        return userRepository.findById(uid)
                .orElseThrow(() -> new IllegalArgumentException("用户不存在: uid=" + uid));
    }

    /**
     * 检查用户是否存在
     * 
     * @param uid Firebase UID
     * @return 是否存在
     */
    @Transactional(readOnly = true)
    public boolean existsByUid(String uid) {
        return userRepository.existsByUid(uid);
    }
}
