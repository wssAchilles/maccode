package org.xzq.aether.domain.board;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Board 仓储接口
 * 提供看板的数据访问能力
 */
@Repository
public interface BoardRepository extends JpaRepository<Board, Long> {

    /**
     * 查询项目下的所有看板
     * @param projectId 项目 ID
     * @return 看板列表
     */
    List<Board> findAllByProjectId(Long projectId);

    /**
     * 获取看板详情（包含列表）
     * 注意：不能同时 fetch 多个集合,所以只 fetch lists,cards 将懒加载
     * @param boardId 看板 ID
     * @return 看板（带列表）
     */
    @Query("SELECT DISTINCT b FROM Board b " +
           "LEFT JOIN FETCH b.lists " +
           "WHERE b.id = :boardId")
    Optional<Board> findByIdWithListsAndCards(@Param("boardId") Long boardId);

    /**
     * 检查看板是否属于指定项目
     * @param boardId 看板 ID
     * @param projectId 项目 ID
     * @return true 如果属于该项目
     */
    @Query("SELECT COUNT(b) > 0 FROM Board b " +
           "WHERE b.id = :boardId AND b.project.id = :projectId")
    boolean existsByIdAndProjectId(
        @Param("boardId") Long boardId, 
        @Param("projectId") Long projectId
    );
}
