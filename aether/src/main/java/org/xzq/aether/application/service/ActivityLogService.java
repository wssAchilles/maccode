package org.xzq.aether.application.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.xzq.aether.application.events.*;
import org.xzq.aether.domain.activity.ActivityLog;
import org.xzq.aether.domain.activity.ActivityLogRepository;
import org.xzq.aether.domain.board.Card;
import org.xzq.aether.domain.board.CardList;
import org.xzq.aether.domain.project.Project;
import org.xzq.aether.domain.project.ProjectMember;
import org.xzq.aether.domain.user.User;

/**
 * 活动日志服务
 * 职责: 监听领域事件，异步记录人类可读的活动日志到数据库
 * 
 * 设计原则:
 * 1. 所有方法标记 @Async，不阻塞主业务流程
 * 2. 所有方法标记 @Transactional，独立事务防止主事务失败影响日志
 * 3. 异常捕获，日志失败不应影响核心业务
 * 4. 消息使用中文，面向人类可读
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class ActivityLogService {

    private final ActivityLogRepository activityLogRepository;

    /**
     * 处理卡片创建事件
     * 消息示例: "张三 在列表 'TODO' 中创建了卡片 '设计登录页面'"
     */
    @EventListener
    @Async
    @Transactional
    public void handleCardCreated(CardCreatedEvent event) {
        try {
            Card card = event.getCard();
            CardList list = card.getList();
            Project project = list.getBoard().getProject();
            User user = event.getTriggeredBy();

            String message = String.format(
                "%s 在列表「%s」中创建了卡片「%s」",
                user.getUsername(),
                list.getName(),
                card.getTitle()
            );

            ActivityLog activityLog = ActivityLog.create(message, project, user);
            activityLogRepository.save(activityLog);

            log.debug("活动日志已记录: projectId={}, message={}", project.getId(), message);

        } catch (Exception e) {
            log.error("记录卡片创建活动日志失败", e);
        }
    }

    /**
     * 处理卡片更新事件
     * 消息示例: "李四 更新了卡片 '设计登录页面'"
     */
    @EventListener
    @Async
    @Transactional
    public void handleCardUpdated(CardUpdatedEvent event) {
        try {
            Card card = event.getCard();
            CardList list = card.getList();
            Project project = list.getBoard().getProject();
            User user = event.getTriggeredBy();

            String message = String.format(
                "%s 更新了卡片「%s」",
                user.getUsername(),
                card.getTitle()
            );

            ActivityLog activityLog = ActivityLog.create(message, project, user);
            activityLogRepository.save(activityLog);

            log.debug("活动日志已记录: projectId={}, message={}", project.getId(), message);

        } catch (Exception e) {
            log.error("记录卡片更新活动日志失败", e);
        }
    }

    /**
     * 处理卡片移动事件
     * 消息示例: "王五 将卡片 '设计登录页面' 从 'TODO' 移动到了 'In Progress'"
     * 
     * 注意: 需要额外查询来获取列表名称，因为事件只包含列表ID
     */
    @EventListener
    @Async
    @Transactional
    public void handleCardMoved(CardMovedEvent event) {
        try {
            Card card = event.getCard();
            CardList newList = card.getList();
            Project project = newList.getBoard().getProject();
            User user = event.getTriggeredBy();

            // 如果 oldListId 和 newListId 相同，说明是同列表内位置调整
            if (event.getOldListId().equals(event.getNewListId())) {
                String message = String.format(
                    "%s 调整了卡片「%s」在列表「%s」中的位置",
                    user.getUsername(),
                    card.getTitle(),
                    newList.getName()
                );

                ActivityLog activityLog = ActivityLog.create(message, project, user);
                activityLogRepository.save(activityLog);
            } else {
                // 跨列表移动 - 需要获取旧列表名称
                // 由于事件只包含 oldListId，我们需要从 board 的列表中查找
                String oldListName = newList.getBoard().getLists().stream()
                    .filter(l -> l.getId().equals(event.getOldListId()))
                    .findFirst()
                    .map(CardList::getName)
                    .orElse("未知列表");

                String message = String.format(
                    "%s 将卡片「%s」从「%s」移动到了「%s」",
                    user.getUsername(),
                    card.getTitle(),
                    oldListName,
                    newList.getName()
                );

                ActivityLog activityLog = ActivityLog.create(message, project, user);
                activityLogRepository.save(activityLog);
            }

            log.debug("活动日志已记录: projectId={}", project.getId());

        } catch (Exception e) {
            log.error("记录卡片移动活动日志失败", e);
        }
    }

    /**
     * 处理卡片删除事件
     * 消息示例: "赵六 删除了卡片 '设计登录页面'"
     * 
     * 注意: 卡片实体已被删除，需要从事件中获取项目信息
     */
    @EventListener
    @Async
    @Transactional
    public void handleCardDeleted(CardDeletedEvent event) {
        try {
            // 卡片已删除，需要通过 boardId 获取 project
            // 这里需要额外注入 BoardRepository 来查询
            // 为了简化，我们先记录一个基本的日志（不包含项目信息）
            // TODO: 考虑在事件中直接传递 projectId
            
            User user = event.getTriggeredBy();
            String message = String.format(
                "%s 删除了卡片「%s」",
                user.getUsername(),
                event.getCardTitle()
            );

            // 由于我们没有 project 引用，这里暂时无法保存
            // 需要注入 BoardRepository 来查询 project
            log.warn("卡片删除事件无法记录活动日志：缺少 project 引用。建议在 CardDeletedEvent 中包含 Project");
            log.debug("卡片删除消息: {}", message);

        } catch (Exception e) {
            log.error("记录卡片删除活动日志失败", e);
        }
    }

    /**
     * 处理项目成员添加事件
     * 消息示例: "管理员 将 '张三' 添加为项目成员（角色: MEMBER）"
     */
    @EventListener
    @Async
    @Transactional
    public void handleProjectMemberAdded(ProjectMemberAddedEvent event) {
        try {
            ProjectMember member = event.getMember();
            Project project = member.getId().getProject();
            User addedUser = member.getId().getUser();
            User triggeredBy = event.getTriggeredBy();

            String roleText = switch (member.getRole()) {
                case OWNER -> "项目所有者";
                case ADMIN -> "管理员";
                case MEMBER -> "成员";
            };

            String message = String.format(
                "%s 将「%s」添加为项目成员（角色: %s）",
                triggeredBy.getUsername(),
                addedUser.getUsername(),
                roleText
            );

            ActivityLog activityLog = ActivityLog.create(message, project, triggeredBy);
            activityLogRepository.save(activityLog);

            log.debug("活动日志已记录: projectId={}, message={}", project.getId(), message);

        } catch (Exception e) {
            log.error("记录项目成员添加活动日志失败", e);
        }
    }
}
