package org.xzq.aether.application.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.xzq.aether.application.dto.project.*;
import org.xzq.aether.application.events.ProjectMemberAddedEvent;
import org.xzq.aether.application.service.mapper.DtoMapper;
import org.xzq.aether.domain.project.*;
import org.xzq.aether.domain.user.User;
import org.xzq.aether.domain.user.UserRepository;

import java.util.List;
import java.util.stream.Collectors;

/**
 * 项目应用服务
 * 编排项目相关的业务逻辑
 * 
 * [Milestone 4] 集成事件驱动架构
 */
@Service
@RequiredArgsConstructor
@Transactional
@Slf4j
public class ProjectAppService {

    private final ProjectRepository projectRepository;
    private final ProjectMemberRepository projectMemberRepository;
    private final UserRepository userRepository;
    private final DtoMapper dtoMapper;
    private final ApplicationEventPublisher eventPublisher;

    /**
     * 创建新项目
     * 创建者自动成为项目拥有者
     */
    public ProjectResponse createProject(CreateProjectRequest request, User currentUser) {
        log.info("用户 {} 创建新项目: {}", currentUser.getUid(), request.getName());
        
        // 创建项目实体
        Project project = Project.create(
            request.getName(),
            request.getDescription(),
            currentUser
        );
        
        // 保存项目
        project = projectRepository.save(project);
        
        // 创建项目成员记录（拥有者）
        project.addMember(currentUser, ProjectRole.OWNER);
        
        log.info("项目 {} 创建成功，ID: {}", project.getName(), project.getId());
        
        return dtoMapper.toProjectResponse(project);
    }

    /**
     * 获取项目详情
     * 需要是项目成员才能访问
     */
    @PreAuthorize("@permissionService.isProjectMember(authentication, #projectId)")
    public ProjectDetailResponse getProjectById(Long projectId) {
        log.debug("获取项目详情: {}", projectId);
        
        Project project = projectRepository.findByIdWithMembers(projectId)
            .orElseThrow(() -> new IllegalArgumentException("项目不存在: " + projectId));
        
        return dtoMapper.toProjectDetailResponse(project);
    }

    /**
     * 更新项目信息
     * 需要是项目管理员或拥有者
     */
    @PreAuthorize("@permissionService.isProjectAdminOrOwner(authentication, #projectId)")
    public ProjectResponse updateProject(Long projectId, UpdateProjectRequest request) {
        log.info("更新项目 {}: {}", projectId, request);
        
        Project project = projectRepository.findById(projectId)
            .orElseThrow(() -> new IllegalArgumentException("项目不存在: " + projectId));
        
        // 调用领域模型的业务方法
        project.update(request.getName(), request.getDescription());
        
        return dtoMapper.toProjectResponse(project);
    }

    /**
     * 删除项目
     * 只有项目拥有者才能删除
     */
    @PreAuthorize("@permissionService.isProjectOwner(authentication, #projectId)")
    public void deleteProject(Long projectId) {
        log.warn("删除项目: {}", projectId);
        
        Project project = projectRepository.findById(projectId)
            .orElseThrow(() -> new IllegalArgumentException("项目不存在: " + projectId));
        
        projectRepository.delete(project);
        
        log.info("项目 {} 已删除", projectId);
    }

    /**
     * 获取用户参与的所有项目
     */
    public List<ProjectResponse> getMyProjects(User currentUser) {
        log.debug("获取用户 {} 的所有项目", currentUser.getUid());
        
        List<Project> projects = projectRepository.findAllByMemberUid(currentUser.getUid());
        
        return projects.stream()
            .map(dtoMapper::toProjectResponse)
            .collect(Collectors.toList());
    }

    /**
     * 添加项目成员
     * 需要是项目管理员或拥有者
     * [Milestone 4] 发布 ProjectMemberAddedEvent 事件
     */
    @PreAuthorize("@permissionService.isProjectAdminOrOwner(authentication, #projectId)")
    public ProjectMemberResponse addMember(Long projectId, AddMemberRequest request, User currentUser) {
        log.info("向项目 {} 添加成员: {}", projectId, request.getUserUid());
        
        Project project = projectRepository.findById(projectId)
            .orElseThrow(() -> new IllegalArgumentException("项目不存在: " + projectId));
        
        User user = userRepository.findById(request.getUserUid())
            .orElseThrow(() -> new IllegalArgumentException("用户不存在: " + request.getUserUid()));
        
        // 检查用户是否已是成员
        if (project.hasMember(user.getUid())) {
            throw new IllegalStateException("用户已是项目成员");
        }
        
        // 调用领域模型的业务方法
        project.addMember(user, request.getRole());
        
        ProjectMember member = projectMemberRepository
            .findByProjectIdAndUserUid(projectId, user.getUid())
            .orElseThrow();
        
        log.info("成员 {} 已添加到项目 {}", user.getUid(), projectId);
        
        // [Milestone 4] 发布事件 - 通知所有项目成员
        eventPublisher.publishEvent(new ProjectMemberAddedEvent(member, currentUser));
        
        return dtoMapper.toProjectMemberResponse(member);
    }

    /**
     * 移除项目成员
     * 需要是项目管理员或拥有者
     * 不能移除拥有者
     */
    @PreAuthorize("@permissionService.isProjectAdminOrOwner(authentication, #projectId)")
    public void removeMember(Long projectId, String userUid) {
        log.info("从项目 {} 移除成员: {}", projectId, userUid);
        
        Project project = projectRepository.findById(projectId)
            .orElseThrow(() -> new IllegalArgumentException("项目不存在: " + projectId));
        
        // 检查是否尝试移除拥有者
        if (project.isOwner(userUid)) {
            throw new IllegalStateException("不能移除项目拥有者");
        }
        
        User user = userRepository.findById(userUid)
            .orElseThrow(() -> new IllegalArgumentException("用户不存在: " + userUid));
        
        // 调用领域模型的业务方法
        project.removeMember(user);
        
        log.info("成员 {} 已从项目 {} 移除", userUid, projectId);
    }

    /**
     * 更新成员角色
     * 需要是项目拥有者
     * 不能修改拥有者角色
     */
    @PreAuthorize("@permissionService.isProjectOwner(authentication, #projectId)")
    public ProjectMemberResponse updateMemberRole(
        Long projectId, 
        String userUid, 
        UpdateMemberRoleRequest request
    ) {
        log.info("更新项目 {} 成员 {} 的角色为: {}", projectId, userUid, request.getRole());
        
        Project project = projectRepository.findById(projectId)
            .orElseThrow(() -> new IllegalArgumentException("项目不存在: " + projectId));
        
        // 检查是否尝试修改拥有者角色
        if (project.isOwner(userUid)) {
            throw new IllegalStateException("不能修改项目拥有者的角色");
        }
        
        ProjectMember member = projectMemberRepository
            .findByProjectIdAndUserUid(projectId, userUid)
            .orElseThrow(() -> new IllegalArgumentException("成员不存在"));
        
        // 调用领域模型的业务方法
        member.updateRole(request.getRole());
        
        log.info("成员 {} 的角色已更新为: {}", userUid, request.getRole());
        
        return dtoMapper.toProjectMemberResponse(member);
    }

    /**
     * 获取项目的所有成员
     * 需要是项目成员才能访问
     */
    @PreAuthorize("@permissionService.isProjectMember(authentication, #projectId)")
    public List<ProjectMemberResponse> getProjectMembers(Long projectId) {
        log.debug("获取项目 {} 的成员列表", projectId);
        
        List<ProjectMember> members = projectMemberRepository.findAllByProjectId(projectId);
        
        return members.stream()
            .map(dtoMapper::toProjectMemberResponse)
            .collect(Collectors.toList());
    }
}
