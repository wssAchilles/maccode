package org.xzq.aether.application.security;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Service;
import org.xzq.aether.domain.board.Board;
import org.xzq.aether.domain.board.BoardRepository;
import org.xzq.aether.domain.board.Card;
import org.xzq.aether.domain.board.CardRepository;
import org.xzq.aether.domain.project.ProjectMember;
import org.xzq.aether.domain.project.ProjectMemberRepository;
import org.xzq.aether.domain.project.ProjectRole;
import org.xzq.aether.domain.user.User;

/**
 * 权限服务 - 用于 @PreAuthorize 注解
 * 封装复杂的权限检查逻辑，确保业务安全
 * 
 * Bean 名称必须是 "permissionService" 以便在 SpEL 中调用
 */
@Service("permissionService")
@RequiredArgsConstructor
@Slf4j
public class PermissionService {

    private final ProjectMemberRepository projectMemberRepository;
    private final BoardRepository boardRepository;
    private final CardRepository cardRepository;

    /**
     * 检查用户是否是项目成员
     * @param auth Spring Security 认证对象
     * @param projectId 项目 ID
     * @return true 如果用户是项目成员
     */
    public boolean isProjectMember(Authentication auth, Long projectId) {
        if (auth == null || !auth.isAuthenticated() || projectId == null) {
            return false;
        }
        
        try {
            User user = (User) auth.getPrincipal();
            boolean isMember = projectMemberRepository
                .existsByProjectIdAndUserUid(projectId, user.getUid());
            
            log.debug("权限检查 - 用户 {} {} 项目 {} 的成员", 
                user.getUid(), 
                isMember ? "是" : "不是", 
                projectId);
            
            return isMember;
        } catch (ClassCastException e) {
            log.error("无效的 Principal 类型: {}", auth.getPrincipal().getClass());
            return false;
        }
    }

    /**
     * 检查用户是否是项目拥有者
     * @param auth Spring Security 认证对象
     * @param projectId 项目 ID
     * @return true 如果用户是项目拥有者
     */
    public boolean isProjectOwner(Authentication auth, Long projectId) {
        if (auth == null || !auth.isAuthenticated() || projectId == null) {
            return false;
        }
        
        try {
            User user = (User) auth.getPrincipal();
            ProjectMember member = projectMemberRepository
                .findByProjectIdAndUserUid(projectId, user.getUid())
                .orElse(null);
            
            boolean isOwner = member != null && member.getRole() == ProjectRole.OWNER;
            
            log.debug("权限检查 - 用户 {} {} 项目 {} 的拥有者", 
                user.getUid(), 
                isOwner ? "是" : "不是", 
                projectId);
            
            return isOwner;
        } catch (ClassCastException e) {
            log.error("无效的 Principal 类型: {}", auth.getPrincipal().getClass());
            return false;
        }
    }

    /**
     * 检查用户是否是项目管理员或拥有者
     * @param auth Spring Security 认证对象
     * @param projectId 项目 ID
     * @return true 如果用户是项目管理员或拥有者
     */
    public boolean isProjectAdminOrOwner(Authentication auth, Long projectId) {
        if (auth == null || !auth.isAuthenticated() || projectId == null) {
            return false;
        }
        
        try {
            User user = (User) auth.getPrincipal();
            ProjectMember member = projectMemberRepository
                .findByProjectIdAndUserUid(projectId, user.getUid())
                .orElse(null);
            
            boolean isAdmin = member != null && 
                (member.getRole() == ProjectRole.OWNER || 
                 member.getRole() == ProjectRole.ADMIN);
            
            log.debug("权限检查 - 用户 {} {} 项目 {} 的管理员", 
                user.getUid(), 
                isAdmin ? "是" : "不是", 
                projectId);
            
            return isAdmin;
        } catch (ClassCastException e) {
            log.error("无效的 Principal 类型: {}", auth.getPrincipal().getClass());
            return false;
        }
    }

    /**
     * 检查用户是否有权限访问看板
     * @param auth Spring Security 认证对象
     * @param boardId 看板 ID
     * @return true 如果用户是看板所属项目的成员
     */
    public boolean isBoardMember(Authentication auth, Long boardId) {
        if (auth == null || !auth.isAuthenticated() || boardId == null) {
            log.debug("权限检查失败 - 认证对象为空或看板ID为空");
            return false;
        }
        
        try {
            User user = (User) auth.getPrincipal();
            
            // 使用更高效的查询：直接通过 JOIN 查询检查用户是否是看板所属项目的成员
            // 避免懒加载问题
            boolean isMember = projectMemberRepository.existsByBoardIdAndUserUid(boardId, user.getUid());
            
            log.debug("权限检查 - 用户 {} {} 看板 {} 的访问权限", 
                user.getUid(), 
                isMember ? "拥有" : "没有", 
                boardId);
            
            return isMember;
        } catch (ClassCastException e) {
            log.error("无效的 Principal 类型: {}", auth.getPrincipal().getClass());
            return false;
        } catch (Exception e) {
            log.error("权限检查异常 - 看板 {}, 用户 {}: {}", 
                boardId, 
                auth.getPrincipal(), 
                e.getMessage());
            return false;
        }
    }

    /**
     * 检查用户是否可以编辑卡片
     * @param auth Spring Security 认证对象
     * @param cardId 卡片 ID
     * @return true 如果用户是卡片所属项目的成员
     */
    public boolean canEditCard(Authentication auth, Long cardId) {
        if (auth == null || !auth.isAuthenticated() || cardId == null) {
            return false;
        }
        
        try {
            User user = (User) auth.getPrincipal();
            
            // 通过 Card -> CardList -> Board -> Project 检查用户权限
            Card card = cardRepository.findById(cardId).orElse(null);
            if (card == null) {
                log.warn("卡片 {} 不存在", cardId);
                return false;
            }
            
            Board board = card.getList().getBoard();
            Long projectId = board.getProject().getId();
            
            boolean canEdit = projectMemberRepository
                .existsByProjectIdAndUserUid(projectId, user.getUid());
            
            log.debug("权限检查 - 用户 {} {} 卡片 {} 的编辑权限", 
                user.getUid(), 
                canEdit ? "拥有" : "没有", 
                cardId);
            
            return canEdit;
        } catch (ClassCastException e) {
            log.error("无效的 Principal 类型: {}", auth.getPrincipal().getClass());
            return false;
        }
    }

    /**
     * 检查用户是否可以编辑列表
     * @param auth Spring Security 认证对象
     * @param listId 列表 ID
     * @return true 如果用户是列表所属项目的成员
     */
    public boolean canEditList(Authentication auth, Long listId) {
        if (auth == null || !auth.isAuthenticated() || listId == null) {
            return false;
        }
        
        try {
            User user = (User) auth.getPrincipal();
            
            // 通过 CardList -> Board 找到所属项目
            return cardRepository.findById(listId)
                .map(card -> {
                    Long projectId = card.getList().getBoard().getProject().getId();
                    return projectMemberRepository
                        .existsByProjectIdAndUserUid(projectId, user.getUid());
                })
                .orElse(false);
        } catch (ClassCastException e) {
            log.error("无效的 Principal 类型: {}", auth.getPrincipal().getClass());
            return false;
        }
    }
}
