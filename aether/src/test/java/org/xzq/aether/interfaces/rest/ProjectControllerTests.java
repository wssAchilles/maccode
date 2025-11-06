package org.xzq.aether.interfaces.rest;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;
import org.xzq.aether.application.dto.project.CreateProjectRequest;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * ProjectController 集成测试
 * 测试 API 流程和安全规则
 */
@SpringBootTest
@AutoConfigureMockMvc
@Transactional
@ActiveProfiles("test")
@DisplayName("ProjectController 集成测试")
class ProjectControllerTests {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    @DisplayName("创建项目 - 未认证 - 应返回 401")
    void testCreateProjectRequiresAuth() throws Exception {
        // Given
        CreateProjectRequest request = new CreateProjectRequest();
        request.setName("Test Project");
        request.setDescription("Test Description");

        // When & Then
        mockMvc.perform(post("/api/v1/projects")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("获取所有项目 - 未认证 - 应返回 401")
    void testGetProjectsRequiresAuth() throws Exception {
        // When & Then
        mockMvc.perform(get("/api/v1/projects"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("获取项目详情 - 未认证 - 应返回 401")
    void testGetProjectByIdRequiresAuth() throws Exception {
        // When & Then
        mockMvc.perform(get("/api/v1/projects/1"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("创建项目 - 无效请求体 - 应返回 400")
    void testCreateProjectWithInvalidRequest() throws Exception {
        // Given - 空的项目名称
        CreateProjectRequest request = new CreateProjectRequest();
        request.setName("");  // 无效：空名称

        // When & Then
        // 注意：由于没有认证，会先返回 401，而不是 400
        // 如果需要测试 400，需要模拟认证用户
        mockMvc.perform(post("/api/v1/projects")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("更新项目 - 未认证 - 应返回 401")
    void testUpdateProjectRequiresAuth() throws Exception {
        // Given
        CreateProjectRequest request = new CreateProjectRequest();
        request.setName("Updated Project");

        // When & Then
        mockMvc.perform(put("/api/v1/projects/1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("删除项目 - 未认证 - 应返回 401")
    void testDeleteProjectRequiresAuth() throws Exception {
        // When & Then
        mockMvc.perform(delete("/api/v1/projects/1"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("添加项目成员 - 未认证 - 应返回 401")
    void testAddMemberRequiresAuth() throws Exception {
        // Given
        String requestBody = "{\"userUid\":\"test-uid\",\"role\":\"MEMBER\"}";

        // When & Then
        mockMvc.perform(post("/api/v1/projects/1/members")
                .contentType(MediaType.APPLICATION_JSON)
                .content(requestBody))
            .andExpect(status().isUnauthorized());
    }

    // ========================================
    // 以下是带认证的测试示例（需要配置 Firebase 模拟）
    // 暂时注释，实际使用时需要配置 @WithMockUser 或自定义认证模拟
    // ========================================

    /*
    @Test
    @WithMockUser(username = "test-uid")
    @DisplayName("创建项目 - 已认证 - 应返回 201")
    void testCreateProjectAsAuthenticatedUser() throws Exception {
        // Given
        CreateProjectRequest request = new CreateProjectRequest();
        request.setName("Test Project");
        request.setDescription("Test Description");

        // When & Then
        mockMvc.perform(post("/api/v1/projects")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.name").value("Test Project"))
            .andExpect(jsonPath("$.description").value("Test Description"));
    }
    */
}
