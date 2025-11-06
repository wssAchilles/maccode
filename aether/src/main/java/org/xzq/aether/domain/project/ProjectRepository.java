package org.xzq.aether.domain.project;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Project 仓储接口
 * 提供项目的数据访问能力
 */
@Repository
public interface ProjectRepository extends JpaRepository<Project, Long> {

    /**
     * 查询用户参与的所有项目
     * @param userUid 用户 UID
     * @return 项目列表
     */
    @Query("SELECT DISTINCT p FROM Project p " +
           "JOIN p.members m " +
           "WHERE m.id.user.uid = :userUid")
    List<Project> findAllByMemberUid(@Param("userUid") String userUid);

    /**
     * 查询用户拥有的所有项目
     * @param ownerUid 拥有者 UID
     * @return 项目列表
     */
    List<Project> findAllByOwnerUid(String ownerUid);

    /**
     * 根据名称查找项目（模糊搜索）
     * @param name 项目名称关键字
     * @return 项目列表
     */
    List<Project> findByNameContainingIgnoreCase(String name);

    /**
     * 获取项目详情（包含成员信息）
     * @param projectId 项目 ID
     * @return 项目（带成员）
     */
    @Query("SELECT p FROM Project p " +
           "LEFT JOIN FETCH p.members " +
           "WHERE p.id = :projectId")
    Optional<Project> findByIdWithMembers(@Param("projectId") Long projectId);
}
