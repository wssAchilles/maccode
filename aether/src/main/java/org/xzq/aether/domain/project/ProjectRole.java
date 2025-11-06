package org.xzq.aether.domain.project;

/**
 * 项目成员角色枚举
 * 定义项目中用户的权限级别
 */
public enum ProjectRole {
    /**
     * 项目拥有者 - 拥有所有权限
     */
    OWNER,
    
    /**
     * 项目管理员 - 可以管理成员和内容
     */
    ADMIN,
    
    /**
     * 项目普通成员 - 只能编辑内容
     */
    MEMBER
}
