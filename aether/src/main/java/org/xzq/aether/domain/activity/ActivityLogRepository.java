package org.xzq.aether.domain.activity;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;

/**
 * ActivityLog 仓储接口
 * 提供活动日志的数据访问能力
 */
@Repository
public interface ActivityLogRepository extends JpaRepository<ActivityLog, Long> {

    /**
     * 查询项目的所有活动日志（分页，按时间倒序）
     * @param projectId 项目 ID
     * @param pageable 分页参数
     * @return 活动日志分页结果
     */
    Page<ActivityLog> findAllByProjectIdOrderByCreatedAtDesc(Long projectId, Pageable pageable);

    /**
     * 查询项目在指定时间后的活动日志
     * @param projectId 项目 ID
     * @param since 起始时间
     * @return 活动日志列表
     */
    List<ActivityLog> findAllByProjectIdAndCreatedAtAfterOrderByCreatedAtDesc(
        Long projectId, 
        Instant since
    );

    /**
     * 查询用户的所有操作记录（分页）
     * @param userUid 用户 UID
     * @param pageable 分页参数
     * @return 活动日志分页结果
     */
    Page<ActivityLog> findAllByUserUidOrderByCreatedAtDesc(String userUid, Pageable pageable);

    /**
     * 统计项目的活动数量
     * @param projectId 项目 ID
     * @return 活动数量
     */
    @Query("SELECT COUNT(a) FROM ActivityLog a WHERE a.project.id = :projectId")
    long countByProjectId(@Param("projectId") Long projectId);
}
