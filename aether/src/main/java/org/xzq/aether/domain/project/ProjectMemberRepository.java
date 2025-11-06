package org.xzq.aether.domain.project;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * ProjectMember 仓储接口
 * 提供项目成员的数据访问能力
 */
@Repository
public interface ProjectMemberRepository extends JpaRepository<ProjectMember, ProjectMemberId> {

    /**
     * 查询项目的所有成员
     * @param projectId 项目 ID
     * @return 成员列表
     */
    @Query("SELECT pm FROM ProjectMember pm " +
           "WHERE pm.id.project.id = :projectId")
    List<ProjectMember> findAllByProjectId(@Param("projectId") Long projectId);

    /**
     * 查询用户在指定项目中的成员记录
     * @param projectId 项目 ID
     * @param userUid 用户 UID
     * @return 成员记录
     */
    @Query("SELECT pm FROM ProjectMember pm " +
           "WHERE pm.id.project.id = :projectId " +
           "AND pm.id.user.uid = :userUid")
    Optional<ProjectMember> findByProjectIdAndUserUid(
        @Param("projectId") Long projectId, 
        @Param("userUid") String userUid
    );

    /**
     * 检查用户是否是项目成员
     * @param projectId 项目 ID
     * @param userUid 用户 UID
     * @return true 如果是成员
     */
    @Query("SELECT COUNT(pm) > 0 FROM ProjectMember pm " +
           "WHERE pm.id.project.id = :projectId " +
           "AND pm.id.user.uid = :userUid")
    boolean existsByProjectIdAndUserUid(
        @Param("projectId") Long projectId, 
        @Param("userUid") String userUid
    );

    /**
     * 检查用户是否是看板所属项目的成员
     * @param boardId 看板 ID
     * @param userUid 用户 UID
     * @return true 如果用户是该看板所属项目的成员
     */
    @Query("SELECT COUNT(pm) > 0 FROM ProjectMember pm, Board b " +
           "WHERE pm.id.project.id = b.project.id " +
           "AND b.id = :boardId " +
           "AND pm.id.user.uid = :userUid")
    boolean existsByBoardIdAndUserUid(
        @Param("boardId") Long boardId,
        @Param("userUid") String userUid
    );
}
