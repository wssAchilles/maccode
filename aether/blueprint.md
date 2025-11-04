这是一个非常棒的决定。作为你的项目架构师，我将为你提供这份\*\*“aether”项目\*\*的顶层设计蓝图。

这份蓝图将作为你（以及你的 AI Agent）的“单一事实来源”(Single Source of Truth)，确保项目的每一个部分都协同一致、目标明确。我们不谈论具体代码，我们只定义**方向、契约和架构**。

-----

# 项目蓝图 (Project Blueprint): "aether"

  * **项目名称:** `aether`
  * **项目愿景:** 一个基于 Spring Boot 和 Firebase 的实时、敏捷项目协作平台。它以“领域驱动设计”(DDD)为核心，构建一个高度内聚、低耦合、易于扩展的后端系统，为团队提供“以太”般无所不在的丝滑协作体验。

-----

## 阶段一：地基与架构 (Foundation & Architecture)

此阶段的目标是定义项目的“骨架”和“灵魂”。

### 1.1. 技术栈选型 (Tech Stack)

  * **核心框架:** Spring Boot 3.x
  * **认证服务:** Firebase Authentication
  * **数据持久化:** Spring Data JPA (Hibernate)
  * **数据库:** MySQL 8+
  * **实时通信:** Spring WebSocket (STOMP)
  * **安全框架:** Spring Security 6
  * **构建工具:** Maven
  * **API 文档:** springdoc-openapi (Swagger 3)
  * **部署:** Docker / Docker Compose

### 1.2. 核心架构原则 (Core Principles)

你（和你的 AI Agent）在生成任何代码时，都**必须**遵守以下原则：

1.  **领域驱动设计 (DDD) - 高内聚：**
      * **拒绝贫血模型：** 业务逻辑（如“一个卡片如何移动”、“一个项目如何归档”）**必须**封装在领域实体（Entity）自身的方法中。
      * **拒绝臃肿服务：** `Service` 层应保持“薄”，主要充当协调者，调用领域模型的方法来完成工作。
2.  **事件驱动架构 (EDA) - 低耦合：**
      * 核心业务（如“移动卡片”）和附加业务（如“发送通知”、“记录日志”）**必须**解耦。
      * 使用 Spring Events 机制。主流程只负责发布事件，其他监听器（如通知服务、日志服务）异步处理。
3.  **安全优先 (Security-First)：**
      * **职责分离：** Firebase **只负责**身份认证（Authentication，你是谁？）；Spring Security **只负责**访问授权（Authorization，你能做什么？）。
      * **零信任：** 任何 API 端点都不能假设用户是合法的。所有需要授权的端点都**必须**受 Spring Security 保护。

### 1.3. 项目模块结构 (Package Structure)

你的 AI Agent 必须按**领域**（业务功能）组织包，**而不是**按技术分层（如 `controller`, `service`, `repository`）。这是 DDD 的基本要求。

```
com.aether.platform
├── domain                  # 核心领域层 (POJO 实体, 领域服务, 仓储接口)
│   ├── user              # 用户领域 (User 实体, UserRepository 接口)
│   ├── project           # 项目领域 (Project, ProjectMember, ProjectRepository)
│   ├── board             # 看板领域 (Board, CardList, Card, BoardRepository...)
│   └── shared            # 共享值对象 (如 UserId, ProjectId)
│
├── application             # 应用层 (协调者)
│   ├── service           # 应用服务 (AppService, 编排领域服务)
│   ├── dto               # 数据传输对象 (Request/Response DTOs)
│   └── security          # 安全配置与过滤器
│
├── infrastructure          # 基础设施层 (具体技术实现)
│   ├── persistence       # 持久化实现 (JPA Repository 的实现)
│   ├── firebase          # Firebase Admin SDK 的封装
│   ├── websocket         # WebSocket 消息处理器
│   └── config            # 所有 Spring 配置类 (DB, Security, WebSocket)
│
└── interfaces              # 接口层 (对外暴露)
    └── rest              # REST API 控制器 (Controllers)
```

-----

## 阶段二：数据建模与持久化 (Data Modeling)

此阶段定义系统的数据“蓝图”。你的 AI Agent 需要根据这些定义生成 JPA 实体。

### 2.1. 实体关系模型 (ERM) 描述

  * **User (用户):**
      * 与 `ProjectMember` 呈**一对多**关系（一个用户可以是多个项目的成员）。
      * 与 `Card` 呈**多对多**关系（通过 `CardAssignment` 实体，一个用户可被指派到多个卡片）。
  * **Project (项目):**
      * 与 `ProjectMember` 呈**一对多**关系。
      * 与 `Board` (看板) 呈**一对多**关系。
  * **Board (看板):**
      * 与 `Project` 呈**多对一**关系。
      * 与 `CardList` (列表) 呈**一对多**关系。
  * **CardList (卡片列表):**
      * 与 `Board` 呈**多对一**关系。
      * 与 `Card` (卡片) 呈**一对多**关系。
  * **Card (卡片):**
      * 与 `CardList` 呈**多对一**关系。

### 2.2. 核心实体属性定义

1.  **User (用户) 实体:**

      * **`uid` (String):** **主键**。这**必须**用于存储从 Firebase 获取的 `UID`，而不是自增 ID。
      * `email` (String): 唯一，用于显示。
      * `username` (String): 显示名称。
      * `avatarUrl` (String): 头像链接。

2.  **Project (项目) 实体:**

      * `id` (Long): 主键。
      * `name` (String): 项目名称。
      * `description` (Text): 项目描述。
      * *关系:* `owner` (指向 `User` 的多对一)。
      * *关系:* `members` (指向 `ProjectMember` 的一对多)。
      * *关系:* `boards` (指向 `Board` 的一对多)。

3.  **ProjectMember (项目成员) 实体:**

      * *复合主键:* `projectId` 和 `userId`。
      * `role` (Enum): 角色（如 `OWNER`, `ADMIN`, `MEMBER`）。

4.  **Board (看板) 实体:**

      * `id` (Long): 主键。
      * `name` (String): 看板名称。
      * *关系:* `project` (指向 `Project` 的多对一)。
      * *关系:* `lists` (指向 `CardList` 的一对多，**必须**支持排序)。

5.  **CardList (卡片列表) 实体:**

      * `id` (Long): 主键。
      * `name` (String): 列表名称 (如 "待办", "进行中")。
      * `position` (Double/Integer): **必须**有此字段，用于列表的拖拽排序。
      * *关系:* `board` (指向 `Board` 的多对一)。
      * *关系:* `cards` (指向 `Card` 的一对多，**必须**支持排序)。

6.  **Card (卡片) 实体:**

      * `id` (Long): 主键。
      * `title` (String): 卡片标题。
      * `description` (Text): 卡片描述。
      * `dueDate` (Timestamp): 截止日期。
      * `position` (Double/Integer): **必须**有此字段，用于卡片在列表内的拖拽排序。
      * *关系:* `list` (指向 `CardList` 的多对一)。
      * *关系:* `assignees` (指向 `User` 的多对多)。

-----

## 阶段三：核心 API 与安全 (Core API & Security)

此阶段构建系统的“骨架”——认证和 CRUD。

### 3.1. 模块一：认证与安全 (Firebase + Spring Security)

这是本项目的**第一个里程碑**。

1.  **生成安全配置 (`SecurityConfig`):**
      * **必须**禁用 `CSRF`（因为我们使用 JWT，无状态）。
      * **必须**禁用 `Session`（`STATELESS` 策略）。
      * **必须**配置 `CORS`，允许你的前端域名访问。
      * **必须**启用方法级安全 (`@EnableMethodSecurity`)。
2.  **生成 `FirebaseTokenFilter` (认证过滤器):**
      * 这是你的**核心认证器**。
      * **职责:** 继承 `OncePerRequestFilter`。
      * **逻辑:**
        1.  从 `Authorization` 请求头中提取 `Bearer Token`。
        2.  使用 `FirebaseAuth.getInstance().verifyIdToken(token)` 验证此 Token。
        3.  如果验证成功，从 Firebase 返回的 `DecodedToken` 中获取 `UID` 和 `email`。
        4.  使用这些信息，创建一个 Spring Security 的 `UsernamePasswordAuthenticationToken`（或自定义 Token）。
        5.  将此 Token 放入 `SecurityContextHolder.getContext().setAuthentication(...)`。
      * **必须**将此 Filter 添加到 Spring Security 过滤链的 `UsernamePasswordAuthenticationFilter` 之前。
3.  **生成 `UserSync` 逻辑:**
      * 当 Firebase 认证成功后，Filter **必须**检查本地 `User` 表中是否存在该 `UID`。
      * 如果不存在，**必须**调用一个 `UserService` 的 `syncUser` 方法，将 Firebase 的 `UID`, `email`, `username` 等信息**同步**到你本地的 `aether_db` 数据库的 `User` 表中。

### 3.2. 模块二：核心 CRUD 端点

你的 AI Agent 现在可以根据我们之前定义的 API 列表，为 `Project`, `Board`, `CardList`, `Card` 生成全套的 RESTful `Controller`。

**关键指令：**

  * **使用 DTOs:** `Controller` 的所有输入和输出**必须**使用 `application/dto` 中定义的 DTO 对象，**严禁**直接暴露 JPA 实体。
  * **权限控制:** **必须**在 `Service` 层的方法上（**而不是** Controller）使用 `@PreAuthorize` 注解来做权限控制。
      * **示例:**
          * `getBoardDetails(boardId)`: **必须**校验 `@permissionService.isBoardMember(authentication, #boardId)`。
          * `deleteCard(cardId)`: **必须**校验 `@permissionService.canEditCard(authentication, #cardId)`。
  * **生成 `PermissionService`:**
      * AI Agent 需生成一个 `PermissionService` (或类似名称的 Bean)。
      * 它包含多个公开的 `boolean` 方法（如 `isBoardMember`），这些方法内部封装了复杂的数据库查询逻辑，专门用于被 `@PreAuthorize` 注解调用。

### 3.3. 模块三：核心交互逻辑 (拖拽)

1.  **生成“列表排序”端点:** `PUT /api/v1/boards/{boardId}/lists/order`
      * 它接收一个**有序**的 `listId` 数组。
      * 服务层**必须**在一个事务中，遍历此数组，并更新每个 `CardList` 的 `position` 字段。
2.  **生成“卡片移动”端点:** `PATCH /api/v1/cards/{cardId}/move`
      * 它接收 `targetListId` 和 `newPosition`。
      * 这是**最复杂的业务逻辑**，AI Agent 必须小心处理：
        1.  **场景1：列表内移动。** (只更新受影响卡片的 `position` 字段)。
        2.  **场景2：跨列表移动。** (更新卡片的 `list_id` 关联，并更新新旧两个列表中受影响卡片的 `position` 字段)。
      * **必须**在一个数据库事务中完成。

-----

## 阶段四：高级功能 (Real-time & EDA)

此阶段为项目“注入灵魂”，是拉开差距的亮点。

### 4.1. 模块四：实时协作 (WebSocket)

1.  **生成 `WebSocketConfig`:**
      * **必须**配置一个基于 STOMP 的消息代理。
      * **必须**定义 `/topic` 作为广播前缀，`/app` 作为应用目标前缀。
2.  **定义 WebSocket “契约”:**
      * **订阅 (Subscribe):** 客户端在进入看板时，**必须**订阅一个动态主题：`/topic/board/{boardId}`。
      * **广播 (Broadcast):** 当后端有任何变更时（如卡片移动），后端**必须**向此主题广播一个消息。
      * **消息体 (Payload):** 消息体**必须**是结构化的 JSON，包含 `actionType` (如 `CARD_MOVED`, `CARD_CREATED`) 和 `payload` (具体数据)。

### 4.2. 模块五：事件解耦 (Spring Events)

这是实现低耦合和 WebSocket 广播的关键。

1.  **定义领域事件:**
      * AI Agent 需创建多个 POJO 事件类，如：
          * `CardMovedEvent` (包含 card, oldListId, newListId)
          * `CardCreatedEvent`
          * `ProjectMemberAddedEvent`
2.  **发布事件:**
      * 在“阶段三”的**核心业务逻辑**（如 `CardMovementService`）完成数据库操作**之后**，**必须**注入 `ApplicationEventPublisher` 并发布相应的事件。
3.  **创建事件监听器:**
      * **必须**创建**至少两个**监听器，它们监听相同的事件。
      * **监听器1: `WebSocketNotifierService`**
          * **职责:** 监听（如）`CardMovedEvent`。
          * **逻辑:** 构造一个广播消息，并使用 `SimpMessagingTemplate` 将其发送到正确的 WebSocket 主题（如 `/topic/board/{board.id}`）。
      * **监听器2: `ActivityLogService`**
          * **职责:** 监听所有业务事件（`CardMovedEvent`, `CardCreatedEvent`...）。
          * **逻辑:** 将事件信息翻译成人类可读的字符串（如“Achilles 将卡片 'X' 从 '待办' 移动到了 '进行中'”），并将其存入 `ActivityLog` 数据库表。
      * **关键指令:** 这两个监听器**必须**使用 `@Async` 注解，在**单独的线程**中异步执行，以确保主 API 请求（如拖拽卡片）的响应时间**不**受其影响。

-----

## 阶段五：质量与部署 (Quality & Deployment)

1.  **API 文档:**
      * 配置 `springdoc-openapi`。AI Agent **必须**为所有 `Controller` 和 DTO 添加清晰的 Swagger 注解（`@Operation`, `@Schema`）。
2.  **测试策略:**
      * **单元测试:** 针对 `domain` 层的实体（如 `Card.moveTo()`）和 `PermissionService`。
      * **集成测试:** 针对 `Controller` 层，使用 `MockMvc` 和 `@SpringBootTest` 验证 API 流程和安全规则。
3.  **容器化:**
      * **`Dockerfile`:** AI Agent 需生成一个**多阶段构建 (multi-stage build)** 的 `Dockerfile`，以创建最小的、安全的 Java 运行时镜像。
      * **`docker-compose.yml`:** AI Agent 需生成一个 `docker-compose` 文件，用于一键启动整个 `aether` 系统，它**必须**包含两个服务：
        1.  `aether-api` (从 `Dockerfile` 构建)
        2.  `mysql` (使用官方镜像，并挂载数据卷)

-----

这是一个非常棒的决定。作为你的项目架构师，我将为你提供这份\*\*“aether”项目\*\*的顶层设计蓝图。

这份蓝图将作为你（以及你的 AI Agent）的“单一事实来源”(Single Source of Truth)，确保项目的每一个部分都协同一致、目标明确。我们不谈论具体代码，我们只定义**方向、契约和架构**。

-----

# 项目蓝图 (Project Blueprint): "aether"

  * **项目名称:** `aether`
  * **项目愿景:** 一个基于 Spring Boot 和 Firebase 的实时、敏捷项目协作平台。它以“领域驱动设计”(DDD)为核心，构建一个高度内聚、低耦合、易于扩展的后端系统，为团队提供“以太”般无所不在的丝滑协作体验。

-----

## 阶段一：地基与架构 (Foundation & Architecture)

此阶段的目标是定义项目的“骨架”和“灵魂”。

### 1.1. 技术栈选型 (Tech Stack)

  * **核心框架:** Spring Boot 3.x
  * **认证服务:** Firebase Authentication
  * **数据持久化:** Spring Data JPA (Hibernate)
  * **数据库:** MySQL 8+
  * **实时通信:** Spring WebSocket (STOMP)
  * **安全框架:** Spring Security 6
  * **构建工具:** Maven
  * **API 文档:** springdoc-openapi (Swagger 3)
  * **部署:** Docker / Docker Compose

### 1.2. 核心架构原则 (Core Principles)

你（和你的 AI Agent）在生成任何代码时，都**必须**遵守以下原则：

1.  **领域驱动设计 (DDD) - 高内聚：**
      * **拒绝贫血模型：** 业务逻辑（如“一个卡片如何移动”、“一个项目如何归档”）**必须**封装在领域实体（Entity）自身的方法中。
      * **拒绝臃肿服务：** `Service` 层应保持“薄”，主要充当协调者，调用领域模型的方法来完成工作。
2.  **事件驱动架构 (EDA) - 低耦合：**
      * 核心业务（如“移动卡片”）和附加业务（如“发送通知”、“记录日志”）**必须**解耦。
      * 使用 Spring Events 机制。主流程只负责发布事件，其他监听器（如通知服务、日志服务）异步处理。
3.  **安全优先 (Security-First)：**
      * **职责分离：** Firebase **只负责**身份认证（Authentication，你是谁？）；Spring Security **只负责**访问授权（Authorization，你能做什么？）。
      * **零信任：** 任何 API 端点都不能假设用户是合法的。所有需要授权的端点都**必须**受 Spring Security 保护。

### 1.3. 项目模块结构 (Package Structure)

你的 AI Agent 必须按**领域**（业务功能）组织包，**而不是**按技术分层（如 `controller`, `service`, `repository`）。这是 DDD 的基本要求。

```
com.aether.platform
├── domain                  # 核心领域层 (POJO 实体, 领域服务, 仓储接口)
│   ├── user              # 用户领域 (User 实体, UserRepository 接口)
│   ├── project           # 项目领域 (Project, ProjectMember, ProjectRepository)
│   ├── board             # 看板领域 (Board, CardList, Card, BoardRepository...)
│   └── shared            # 共享值对象 (如 UserId, ProjectId)
│
├── application             # 应用层 (协调者)
│   ├── service           # 应用服务 (AppService, 编排领域服务)
│   ├── dto               # 数据传输对象 (Request/Response DTOs)
│   └── security          # 安全配置与过滤器
│
├── infrastructure          # 基础设施层 (具体技术实现)
│   ├── persistence       # 持久化实现 (JPA Repository 的实现)
│   ├── firebase          # Firebase Admin SDK 的封装
│   ├── websocket         # WebSocket 消息处理器
│   └── config            # 所有 Spring 配置类 (DB, Security, WebSocket)
│
└── interfaces              # 接口层 (对外暴露)
    └── rest              # REST API 控制器 (Controllers)
```

-----

## 阶段二：数据建模与持久化 (Data Modeling)

此阶段定义系统的数据“蓝图”。你的 AI Agent 需要根据这些定义生成 JPA 实体。

### 2.1. 实体关系模型 (ERM) 描述

  * **User (用户):**
      * 与 `ProjectMember` 呈**一对多**关系（一个用户可以是多个项目的成员）。
      * 与 `Card` 呈**多对多**关系（通过 `CardAssignment` 实体，一个用户可被指派到多个卡片）。
  * **Project (项目):**
      * 与 `ProjectMember` 呈**一对多**关系。
      * 与 `Board` (看板) 呈**一对多**关系。
  * **Board (看板):**
      * 与 `Project` 呈**多对一**关系。
      * 与 `CardList` (列表) 呈**一对多**关系。
  * **CardList (卡片列表):**
      * 与 `Board` 呈**多对一**关系。
      * 与 `Card` (卡片) 呈**一对多**关系。
  * **Card (卡片):**
      * 与 `CardList` 呈**多对一**关系。

### 2.2. 核心实体属性定义

1.  **User (用户) 实体:**

      * **`uid` (String):** **主键**。这**必须**用于存储从 Firebase 获取的 `UID`，而不是自增 ID。
      * `email` (String): 唯一，用于显示。
      * `username` (String): 显示名称。
      * `avatarUrl` (String): 头像链接。

2.  **Project (项目) 实体:**

      * `id` (Long): 主键。
      * `name` (String): 项目名称。
      * `description` (Text): 项目描述。
      * *关系:* `owner` (指向 `User` 的多对一)。
      * *关系:* `members` (指向 `ProjectMember` 的一对多)。
      * *关系:* `boards` (指向 `Board` 的一对多)。

3.  **ProjectMember (项目成员) 实体:**

      * *复合主键:* `projectId` 和 `userId`。
      * `role` (Enum): 角色（如 `OWNER`, `ADMIN`, `MEMBER`）。

4.  **Board (看板) 实体:**

      * `id` (Long): 主键。
      * `name` (String): 看板名称。
      * *关系:* `project` (指向 `Project` 的多对一)。
      * *关系:* `lists` (指向 `CardList` 的一对多，**必须**支持排序)。

5.  **CardList (卡片列表) 实体:**

      * `id` (Long): 主键。
      * `name` (String): 列表名称 (如 "待办", "进行中")。
      * `position` (Double/Integer): **必须**有此字段，用于列表的拖拽排序。
      * *关系:* `board` (指向 `Board` 的多对一)。
      * *关系:* `cards` (指向 `Card` 的一对多，**必须**支持排序)。

6.  **Card (卡片) 实体:**

      * `id` (Long): 主键。
      * `title` (String): 卡片标题。
      * `description` (Text): 卡片描述。
      * `dueDate` (Timestamp): 截止日期。
      * `position` (Double/Integer): **必须**有此字段，用于卡片在列表内的拖拽排序。
      * *关系:* `list` (指向 `CardList` 的多对一)。
      * *关系:* `assignees` (指向 `User` 的多对多)。

-----

## 阶段三：核心 API 与安全 (Core API & Security)

此阶段构建系统的“骨架”——认证和 CRUD。

### 3.1. 模块一：认证与安全 (Firebase + Spring Security)

这是本项目的**第一个里程碑**。

1.  **生成安全配置 (`SecurityConfig`):**
      * **必须**禁用 `CSRF`（因为我们使用 JWT，无状态）。
      * **必须**禁用 `Session`（`STATELESS` 策略）。
      * **必须**配置 `CORS`，允许你的前端域名访问。
      * **必须**启用方法级安全 (`@EnableMethodSecurity`)。
2.  **生成 `FirebaseTokenFilter` (认证过滤器):**
      * 这是你的**核心认证器**。
      * **职责:** 继承 `OncePerRequestFilter`。
      * **逻辑:**
        1.  从 `Authorization` 请求头中提取 `Bearer Token`。
        2.  使用 `FirebaseAuth.getInstance().verifyIdToken(token)` 验证此 Token。
        3.  如果验证成功，从 Firebase 返回的 `DecodedToken` 中获取 `UID` 和 `email`。
        4.  使用这些信息，创建一个 Spring Security 的 `UsernamePasswordAuthenticationToken`（或自定义 Token）。
        5.  将此 Token 放入 `SecurityContextHolder.getContext().setAuthentication(...)`。
      * **必须**将此 Filter 添加到 Spring Security 过滤链的 `UsernamePasswordAuthenticationFilter` 之前。
3.  **生成 `UserSync` 逻辑:**
      * 当 Firebase 认证成功后，Filter **必须**检查本地 `User` 表中是否存在该 `UID`。
      * 如果不存在，**必须**调用一个 `UserService` 的 `syncUser` 方法，将 Firebase 的 `UID`, `email`, `username` 等信息**同步**到你本地的 `aether_db` 数据库的 `User` 表中。

### 3.2. 模块二：核心 CRUD 端点

你的 AI Agent 现在可以根据我们之前定义的 API 列表，为 `Project`, `Board`, `CardList`, `Card` 生成全套的 RESTful `Controller`。

**关键指令：**

  * **使用 DTOs:** `Controller` 的所有输入和输出**必须**使用 `application/dto` 中定义的 DTO 对象，**严禁**直接暴露 JPA 实体。
  * **权限控制:** **必须**在 `Service` 层的方法上（**而不是** Controller）使用 `@PreAuthorize` 注解来做权限控制。
      * **示例:**
          * `getBoardDetails(boardId)`: **必须**校验 `@permissionService.isBoardMember(authentication, #boardId)`。
          * `deleteCard(cardId)`: **必须**校验 `@permissionService.canEditCard(authentication, #cardId)`。
  * **生成 `PermissionService`:**
      * AI Agent 需生成一个 `PermissionService` (或类似名称的 Bean)。
      * 它包含多个公开的 `boolean` 方法（如 `isBoardMember`），这些方法内部封装了复杂的数据库查询逻辑，专门用于被 `@PreAuthorize` 注解调用。

### 3.3. 模块三：核心交互逻辑 (拖拽)

1.  **生成“列表排序”端点:** `PUT /api/v1/boards/{boardId}/lists/order`
      * 它接收一个**有序**的 `listId` 数组。
      * 服务层**必须**在一个事务中，遍历此数组，并更新每个 `CardList` 的 `position` 字段。
2.  **生成“卡片移动”端点:** `PATCH /api/v1/cards/{cardId}/move`
      * 它接收 `targetListId` 和 `newPosition`。
      * 这是**最复杂的业务逻辑**，AI Agent 必须小心处理：
        1.  **场景1：列表内移动。** (只更新受影响卡片的 `position` 字段)。
        2.  **场景2：跨列表移动。** (更新卡片的 `list_id` 关联，并更新新旧两个列表中受影响卡片的 `position` 字段)。
      * **必须**在一个数据库事务中完成。

-----

## 阶段四：高级功能 (Real-time & EDA)

此阶段为项目“注入灵魂”，是拉开差距的亮点。

### 4.1. 模块四：实时协作 (WebSocket)

1.  **生成 `WebSocketConfig`:**
      * **必须**配置一个基于 STOMP 的消息代理。
      * **必须**定义 `/topic` 作为广播前缀，`/app` 作为应用目标前缀。
2.  **定义 WebSocket “契约”:**
      * **订阅 (Subscribe):** 客户端在进入看板时，**必须**订阅一个动态主题：`/topic/board/{boardId}`。
      * **广播 (Broadcast):** 当后端有任何变更时（如卡片移动），后端**必须**向此主题广播一个消息。
      * **消息体 (Payload):** 消息体**必须**是结构化的 JSON，包含 `actionType` (如 `CARD_MOVED`, `CARD_CREATED`) 和 `payload` (具体数据)。

### 4.2. 模块五：事件解耦 (Spring Events)

这是实现低耦合和 WebSocket 广播的关键。

1.  **定义领域事件:**
      * AI Agent 需创建多个 POJO 事件类，如：
          * `CardMovedEvent` (包含 card, oldListId, newListId)
          * `CardCreatedEvent`
          * `ProjectMemberAddedEvent`
2.  **发布事件:**
      * 在“阶段三”的**核心业务逻辑**（如 `CardMovementService`）完成数据库操作**之后**，**必须**注入 `ApplicationEventPublisher` 并发布相应的事件。
3.  **创建事件监听器:**
      * **必须**创建**至少两个**监听器，它们监听相同的事件。
      * **监听器1: `WebSocketNotifierService`**
          * **职责:** 监听（如）`CardMovedEvent`。
          * **逻辑:** 构造一个广播消息，并使用 `SimpMessagingTemplate` 将其发送到正确的 WebSocket 主题（如 `/topic/board/{board.id}`）。
      * **监听器2: `ActivityLogService`**
          * **职责:** 监听所有业务事件（`CardMovedEvent`, `CardCreatedEvent`...）。
          * **逻辑:** 将事件信息翻译成人类可读的字符串（如“Achilles 将卡片 'X' 从 '待办' 移动到了 '进行中'”），并将其存入 `ActivityLog` 数据库表。
      * **关键指令:** 这两个监听器**必须**使用 `@Async` 注解，在**单独的线程**中异步执行，以确保主 API 请求（如拖拽卡片）的响应时间**不**受其影响。

-----

## 阶段五：质量与部署 (Quality & Deployment)

1.  **API 文档:**
      * 配置 `springdoc-openapi`。AI Agent **必须**为所有 `Controller` 和 DTO 添加清晰的 Swagger 注解（`@Operation`, `@Schema`）。
2.  **测试策略:**
      * **单元测试:** 针对 `domain` 层的实体（如 `Card.moveTo()`）和 `PermissionService`。
      * **集成测试:** 针对 `Controller` 层，使用 `MockMvc` 和 `@SpringBootTest` 验证 API 流程和安全规则。
3.  **容器化:**
      * **`Dockerfile`:** AI Agent 需生成一个**多阶段构建 (multi-stage build)** 的 `Dockerfile`，以创建最小的、安全的 Java 运行时镜像。
      * **`docker-compose.yml`:** AI Agent 需生成一个 `docker-compose` 文件，用于一键启动整个 `aether` 系统，它**必须**包含两个服务：
        1.  `aether-api` (从 `Dockerfile` 构建)
        2.  `mysql` (使用官方镜像，并挂载数据卷)

-----

## 最终项目里程碑 (Roadmap Checklist)

1.  **Milestone 1: 认证闭环 (Auth Loop)**
      * [ ] 阶段三 (3.1) 完成。
      * *可交付成果:* 前端用户可以通过 Firebase 登录，后端 `FirebaseTokenFilter` 能成功验证 Token 并将用户同步到本地 `User` 表。
2.  **Milestone 2: 核心 CRUD (Core CRUD)**
      * [ ] 阶段二 (Data Model) 和 阶段三 (3.2) 完成。
      * *可交付成果:* 用户可以创建项目、看板、列表和卡片。所有操作均受 `@PreAuthorize` 权限保护。
3.  **Milestone 3: 核心交互 (Core Interaction)**
      * [ ] 阶段三 (3.3) 完成。
      * *可交付成果:* 用户可以通过 API 拖拽卡片和列表。
4.  **Milestone 4: 实时同步 (Real-time)**
      * [ ] 阶段四 (4.1, 4.2) 完成。
      * *可交付成果:* 用户 A 拖拽卡片，用户 B 的界面**无需刷新**即可实时看到卡片移动。活动日志被异步记录。
5.  **Milestone 5: 部署 (Go-Live)**
      * [ ] 阶段五 (全部) 完成。
      * *可交付成果:* 一个 `docker-compose up` 命令即可在任何机器上启动完整的 `aether` 平台。

