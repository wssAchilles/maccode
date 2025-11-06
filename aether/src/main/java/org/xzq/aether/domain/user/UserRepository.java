package org.xzq.aether.domain.user;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * 用户仓储接口 (User Repository)
 * 职责: 定义用户领域的数据访问契约
 * 
 * DDD 原则: 这是仓储接口，具体实现由 Spring Data JPA 自动生成
 */
@Repository
public interface UserRepository extends JpaRepository<User, String> {

    /**
     * 通过邮箱查找用户
     * 
     * @param email 用户邮箱
     * @return 用户实体 (如果存在)
     */
    Optional<User> findByEmail(String email);

    /**
     * 检查邮箱是否已存在
     * 
     * @param email 用户邮箱
     * @return 是否存在
     */
    boolean existsByEmail(String email);

    /**
     * 通过 UID 检查用户是否存在
     * 
     * @param uid Firebase UID
     * @return 是否存在
     */
    boolean existsByUid(String uid);
}
