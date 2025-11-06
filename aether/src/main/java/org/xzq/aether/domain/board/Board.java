package org.xzq.aether.domain.board;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;
import org.xzq.aether.domain.project.Project;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

/**
 * 看板实体 - DDD 核心领域模型
 * 代表一个看板，是卡片列表的容器
 */
@Entity
@Table(name = "boards")
@EntityListeners(AuditingEntityListener.class)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Board {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    /**
     * 所属项目
     */
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "project_id", nullable = false)
    private Project project;

    /**
     * 看板下的所有列表 (一对多，按 position 排序)
     */
    @OneToMany(mappedBy = "board", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("position ASC")
    private List<CardList> lists = new ArrayList<>();

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    // ============ DDD 业务方法 ============

    /**
     * 创建新看板 (工厂方法)
     * @param name 看板名称
     * @param project 所属项目
     * @return 新看板实例
     */
    public static Board create(String name, Project project) {
        Board board = new Board();
        board.name = name;
        board.project = project;
        return board;
    }

    /**
     * 更新看板名称
     * @param name 新名称
     */
    public void updateName(String name) {
        if (name != null && !name.isBlank()) {
            this.name = name;
        }
    }

    /**
     * 添加列表
     * @param cardList 卡片列表
     */
    public void addList(CardList cardList) {
        this.lists.add(cardList);
    }

    /**
     * 检查是否属于指定项目
     * @param projectId 项目 ID
     * @return true 如果属于该项目
     */
    public boolean belongsToProject(Long projectId) {
        return this.project.getId().equals(projectId);
    }
}
