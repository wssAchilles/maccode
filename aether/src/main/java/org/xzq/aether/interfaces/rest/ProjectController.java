package org.xzq.aether.interfaces.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.xzq.aether.application.dto.board.BoardResponse;
import org.xzq.aether.application.dto.project.*;
import org.xzq.aether.application.service.BoardAppService;
import org.xzq.aether.application.service.ProjectAppService;
import org.xzq.aether.domain.user.User;

import java.util.List;

/**
 * 项目 REST Controller
 * 处理项目相关的 HTTP 请求
 */
@Tag(name = "Projects", description = "项目管理 API - 创建、查询、更新和管理项目及其成员")
@RestController
@RequestMapping("/api/v1/projects")
@RequiredArgsConstructor
@SecurityRequirement(name = "bearerAuth")
public class ProjectController {

    private final ProjectAppService projectAppService;
    private final BoardAppService boardAppService;

    /**
     * 创建新项目
     * POST /api/v1/projects
     */
    @Operation(summary = "创建新项目", description = "创建一个新的项目，当前用户将自动成为项目所有者")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "201", description = "项目创建成功"),
        @ApiResponse(responseCode = "400", description = "请求参数无效"),
        @ApiResponse(responseCode = "401", description = "未认证")
    })
    @PostMapping
    public ResponseEntity<ProjectResponse> createProject(
        @Valid @RequestBody CreateProjectRequest request,
        @Parameter(hidden = true) Authentication authentication
    ) {
        User currentUser = (User) authentication.getPrincipal();
        ProjectResponse response = projectAppService.createProject(request, currentUser);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    /**
     * 获取我的所有项目
     * GET /api/v1/projects
     */
    @Operation(summary = "获取我的所有项目", description = "获取当前用户参与的所有项目列表")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "成功获取项目列表"),
        @ApiResponse(responseCode = "401", description = "未认证")
    })
    @GetMapping
    public ResponseEntity<List<ProjectResponse>> getMyProjects(
        @Parameter(hidden = true) Authentication authentication
    ) {
        User currentUser = (User) authentication.getPrincipal();
        List<ProjectResponse> projects = projectAppService.getMyProjects(currentUser);
        return ResponseEntity.ok(projects);
    }

    /**
     * 获取项目详情
     * GET /api/v1/projects/{projectId}
     */
    @Operation(summary = "获取项目详情", description = "根据项目 ID 获取项目的详细信息，包括成员和看板列表")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "成功获取项目详情"),
        @ApiResponse(responseCode = "404", description = "项目不存在"),
        @ApiResponse(responseCode = "403", description = "无权访问该项目")
    })
    @GetMapping("/{projectId}")
    public ResponseEntity<ProjectDetailResponse> getProjectById(
        @Parameter(description = "项目 ID") @PathVariable Long projectId
    ) {
        ProjectDetailResponse response = projectAppService.getProjectById(projectId);
        return ResponseEntity.ok(response);
    }

    /**
     * 更新项目信息
     * PUT /api/v1/projects/{projectId}
     */
    @PutMapping("/{projectId}")
    public ResponseEntity<ProjectResponse> updateProject(
        @PathVariable Long projectId,
        @Valid @RequestBody UpdateProjectRequest request
    ) {
        ProjectResponse response = projectAppService.updateProject(projectId, request);
        return ResponseEntity.ok(response);
    }

    /**
     * 删除项目
     * DELETE /api/v1/projects/{projectId}
     */
    @DeleteMapping("/{projectId}")
    public ResponseEntity<Void> deleteProject(@PathVariable Long projectId) {
        projectAppService.deleteProject(projectId);
        return ResponseEntity.noContent().build();
    }

    /**
     * 获取项目下的所有看板
     * GET /api/v1/projects/{projectId}/boards
     */
    @Operation(summary = "获取项目看板列表", description = "获取指定项目下的所有看板")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "成功获取看板列表"),
        @ApiResponse(responseCode = "403", description = "无权访问该项目"),
        @ApiResponse(responseCode = "404", description = "项目不存在")
    })
    @GetMapping("/{projectId}/boards")
    public ResponseEntity<List<BoardResponse>> getProjectBoards(
        @Parameter(description = "项目 ID") @PathVariable Long projectId
    ) {
        List<BoardResponse> boards = boardAppService.getProjectBoards(projectId);
        return ResponseEntity.ok(boards);
    }

    /**
     * 获取项目成员列表
     * GET /api/v1/projects/{projectId}/members
     */
    @GetMapping("/{projectId}/members")
    public ResponseEntity<List<ProjectMemberResponse>> getProjectMembers(@PathVariable Long projectId) {
        List<ProjectMemberResponse> members = projectAppService.getProjectMembers(projectId);
        return ResponseEntity.ok(members);
    }

    /**
     * 添加项目成员
     * POST /api/v1/projects/{projectId}/members
     */
    @PostMapping("/{projectId}/members")
    public ResponseEntity<ProjectMemberResponse> addMember(
        @PathVariable Long projectId,
        @Valid @RequestBody AddMemberRequest request,
        Authentication authentication
    ) {
        User currentUser = (User) authentication.getPrincipal();
        ProjectMemberResponse response = projectAppService.addMember(projectId, request, currentUser);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    /**
     * 移除项目成员
     * DELETE /api/v1/projects/{projectId}/members/{userUid}
     */
    @DeleteMapping("/{projectId}/members/{userUid}")
    public ResponseEntity<Void> removeMember(
        @PathVariable Long projectId,
        @PathVariable String userUid
    ) {
        projectAppService.removeMember(projectId, userUid);
        return ResponseEntity.noContent().build();
    }

    /**
     * 更新成员角色
     * PATCH /api/v1/projects/{projectId}/members/{userUid}
     */
    @PatchMapping("/{projectId}/members/{userUid}")
    public ResponseEntity<ProjectMemberResponse> updateMemberRole(
        @PathVariable Long projectId,
        @PathVariable String userUid,
        @Valid @RequestBody UpdateMemberRoleRequest request
    ) {
        ProjectMemberResponse response = projectAppService.updateMemberRole(projectId, userUid, request);
        return ResponseEntity.ok(response);
    }
}
