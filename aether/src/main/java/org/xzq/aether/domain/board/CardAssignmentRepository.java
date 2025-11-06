package org.xzq.aether.domain.board;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * CardAssignment 仓储接口
 * 提供卡片指派的数据访问能力
 */
@Repository
public interface CardAssignmentRepository extends JpaRepository<CardAssignment, CardAssignmentId> {

    /**
     * 查询卡片的所有指派记录
     * @param cardId 卡片 ID
     * @return 指派记录列表
     */
    @Query("SELECT ca FROM CardAssignment ca " +
           "WHERE ca.id.card.id = :cardId")
    List<CardAssignment> findAllByCardId(@Param("cardId") Long cardId);

    /**
     * 查询用户的所有指派记录
     * @param userUid 用户 UID
     * @return 指派记录列表
     */
    @Query("SELECT ca FROM CardAssignment ca " +
           "WHERE ca.id.user.uid = :userUid")
    List<CardAssignment> findAllByUserUid(@Param("userUid") String userUid);

    /**
     * 检查用户是否被指派到指定卡片
     * @param cardId 卡片 ID
     * @param userUid 用户 UID
     * @return true 如果已指派
     */
    @Query("SELECT COUNT(ca) > 0 FROM CardAssignment ca " +
           "WHERE ca.id.card.id = :cardId " +
           "AND ca.id.user.uid = :userUid")
    boolean existsByCardIdAndUserUid(
        @Param("cardId") Long cardId, 
        @Param("userUid") String userUid
    );
}
