### **项目蓝图：MauiTelegramClient**

**1.0 核心目标 (Objective)**
构建一个功能性的、基于 MVVM 架构的 macOS 聊天客户端。该客户端使用 .NET MAUI 作为 UI 框架，并利用 TdSharp/TdLib.Native 包与 Telegram 的 MTProto API 进行通信。

**2.0 核心技术栈 (Core Stack)**
* **运行时**: .NET 8
* **UI 框架**: .NET MAUI (目标平台: Mac Catalyst)
* **架构模式**: MVVM (Model-View-ViewModel)
* **核心逻辑**: TdSharp (TdLib C# Wrapper)
* **原生库**: TdLib.Native (预编译的 `libtdjson.dylib`)
* **DI 容器**: `Microsoft.Extensions.DependencyInjection` (MAUI 内置)

**3.0 架构定义 (Architecture)**

项目将严格遵循 MVVM 模式，并辅以服务层。

* **Views (V)**: `.xaml` 文件。纯粹的 UI 定义。无业务逻辑。
* **ViewModels (VM)**: `.cs` 文件。`ObservableObject` (来自 CommunityToolkit.Mvvm)。管理 View 的状态，处理 UI 命令 (ICommand)，并与 Services 交互。
* **Services (S)**:
    * `ITelegramService`: 核心服务接口。定义所有与 TDLib 交互的“契约”。
    * `TelegramService`: `ITelegramService` 的**单例 (Singleton)** 实现。此类将是**唯一**持有 `TdClient` 实例的类。它负责初始化客户端、管理主更新循环 (Update loop) 并向相关 ViewModel 广播事件。
    * `INavigationService`: (可选但推荐) 用于解耦 ViewModel 和 MAUI 导航的包装器。

**4.0 关键依赖包 (Dependencies)**

在项目 `.csproj` 文件中必须添加以下 NuGet 包：
1.  `TdSharp`
2.  `TdLib.Native`
3.  `CommunityToolkit.Mvvm` (用于 MVVM 基础类和命令)

---

### **执行阶段 (Phased Execution Plan)**

#### 阶段 0：项目基础结构 (Infrastructure Setup)

1.  **项目创建**:
    * 执行 `dotnet new maui -n MauiTelegramClient`。
2.  **依赖注入 (DI) 配置**:
    * 修改 `MauiProgram.cs`。
    * 注册所有 Services, ViewModels, 和 Views。
    * **关键**: `ITelegramService` 必须注册为 `AddSingleton<ITelegramService, TelegramService>()`。
    * ViewModels (如 `LoginViewModel`, `ChatListViewModel`) 注册为 `AddTransient`。
    * Views (如 `LoginPage`, `ChatListPage`) 注册为 `AddTransient`。
3.  **创建核心服务 (`ITelegramService`)**:
    * 定义 `ITelegramService` 接口。
    * 必须包含方法：`InitializeAsync()`, `ExecuteAuthenticationCommand(TdApi.Function command)`。
    * 必须包含事件/Observable：`IObservable<TdApi.Update> UpdateObservable` 或 `event EventHandler<TdApi.Update> OnUpdateReceived`。
4.  **创建核心服务 (`TelegramService`)**:
    * 实现 `ITelegramService`。
    * **构造函数**: 实例化 `TdClient`。
    * **`InitializeAsync`**: 启动 `TdClient.Run()` 循环（**警告**: `Run` 是阻塞的，必须在 `Task.Run` 中执行）。
    * **更新循环**: 在 `TdClient` 构造时，订阅 `UpdateReceived` 事件。
    * **`OnUpdateReceived` 方法**: 这是**系统的心跳**。它接收所有 `TdApi.Update`。它唯一的职责是将此 `update` 广播给所有订阅者（例如，通过 `UpdateObservable` 或 C# 事件）。
5.  **创建 Shell 导航**:
    * 修改 `AppShell.xaml`。
    * 定义路由。将 `LoginPage` 设置为初始显示页面。
    * 为 `ChatListPage` 和 `ChatPage` 定义路由 (e.g., `Routing.RegisterRoute(nameof(ChatListPage), typeof(ChatListPage));`)。

#### 阶段 1：认证流程 (Authentication Flow)

1.  **View (`LoginPage.xaml`)**:
    * 创建一个 `Grid`，包含多个用于不同登录状态的 `StackLayout`。
    * **状态 1 (Phone)**: `Entry` (用于手机号), `Button` ("下一步")。
    * **状态 2 (Code)**: `Entry` (用于验证码), `Button` ("登录")。
    * **状态 3 (Password)**: `Entry` (用于 2FA 密码), `Button` ("提交")。
    * 使用 `IsVisible` 属性将它们的可见性绑定到 ViewModel 的布尔属性。
2.  **ViewModel (`LoginViewModel.cs`)**:
    * **构造函数**: 注入 `ITelegramService`。
    * **订阅**: 立即订阅 `ITelegramService.OnUpdateReceived`。
    * **状态属性**:
        * `string PhoneNumber`, `string VerificationCode`, `string Password`
        * `bool IsWaitingForPhoneNumber`, `bool IsWaitingForCode`, `bool IsWaitingForPassword`
    * **命令**:
        * `ICommand SubmitCommand`
    * **更新处理器 (Handler)**:
        * 创建一个私有方法 `HandleAuthorizationUpdate(TdApi.UpdateAuthorizationState update)`。
        * **`case AuthorizationStateWaitTdlibParameters`**: 调用 `ITelegramService.ExecuteAuthenticationCommand` 并传入 `SetTdlibParameters`（包含 `api_id`, `api_hash`, `DatabaseDirectory` 等）。
        * **`case AuthorizationStateWaitPhoneNumber`**: 设置 `IsWaitingForPhoneNumber = true`。
        * **`case AuthorizationStateWaitCode`**: 隐藏手机号输入，设置 `IsWaitingForCode = true`。
        * **`case AuthorizationStateWaitPassword`**: 隐藏验证码输入，设置 `IsWaitingForPassword = true`。
        * **`case AuthorizationStateReady`**: 登录成功。调用 `Shell.Current.GoToAsync($"//{nameof(ChatListPage)}")` 导航到主聊天列表。
    * **`SubmitCommand` 逻辑**:
        * 根据当前 `IsWaitingFor...` 状态，获取对应的属性（`PhoneNumber` 或 `VerificationCode`）并调用 `ITelegramService.ExecuteAuthenticationCommand`（传入 `SetAuthenticationPhoneNumber` 或 `CheckAuthenticationCode`）。

#### 阶段 2：聊天列表显示 (Chat List Display)

1.  **View (`ChatListPage.xaml`)**:
    * 主要控件为 `CollectionView`。
    * `CollectionView.ItemsSource` 绑定到 `ChatListViewModel` 的 `ObservableCollection<TdApi.Chat>`。
    * **`DataTemplate`**: 定义一个聊天项 (Cell) 的外观。
        * `Image` (用于头像，暂时留空)。
        * `Label` (用于 `chat.Title`)。
        * `Label` (用于 `chat.LastMessage.Content` 的摘要)。
        * `Label` (用于 `chat.LastMessage.Date` 的格式化时间戳)。
2.  **ViewModel (`ChatListViewModel.cs`)**:
    * **构造函数**: 注入 `ITelegramService`。
    * **属性**: `ObservableCollection<TdApi.Chat> Chats { get; }`。
    * **命令**: `ICommand LoadChatsCommand`, `ICommand SelectChatCommand`。
    * **`LoadChatsCommand` 逻辑** (或在页面 `OnAppearing` 时触发):
        * 调用 `ITelegramService.ExecuteAsync<TdApi.Chats>(new TdApi.GetChats { Limit = 50, ChatList = new TdApi.ChatList.ChatListMain() })`。
        * **异步注意**: `ExecuteAsync` 是 `TdSharp` 提供的便捷方法。
        * 获取返回的 `TdApi.Chats` 对象，遍历 `chat.ChatIds`，然后逐个调用 `ITelegramService.ExecuteAsync<TdApi.Chat>(new TdApi.GetChat { ChatId = id })` 来获取完整聊天对象。
        * 将获取的 `TdApi.Chat` 对象添加到 `Chats` 集合中。
    * **`SelectChatCommand` 逻辑**:
        * 当 `CollectionView` 的 `SelectionChanged` 事件触发时，获取选中的 `TdApi.Chat`。
        * 导航到聊天页面：`Shell.Current.GoToAsync($"{nameof(ChatPage)}?ChatId={selectedChat.Id}")`。
    * **实时更新**: 订阅 `ITelegramService.OnUpdateReceived`。
        * **`case UpdateNewChat`**: 将 `update.Chat` 添加到 `Chats` 集合顶部。
        * **`case UpdateChatLastMessage`**: 查找 `Chats` 集合中对应的 `Chat`，并更新其 `LastMessage` 属性。

#### 阶段 3：聊天消息视图 (Chat Message View)

1.  **View (`ChatPage.xaml`)**:
    * 使用 `Grid` 布局。顶部是 `CollectionView` (用于消息)，底部是 `HorizontalStackLayout` (用于输入)。
    * **`CollectionView`**:
        * `ItemsSource` 绑定到 `ChatPageViewModel` 的 `ObservableCollection<TdApi.Message>`。
        * **关键**: 使用 `DataTemplateSelector` 来区分**入站消息 (Incoming)** 和**出站消息 (Outgoing)** (`message.IsOutgoing`)。
        * 入站模板 `Grid` (靠左)，出站模板 `Grid` (靠右)。
    * **输入区域**: `Editor` (绑定 `OutgoingText`) 和 `Button` (绑定 `SendCommand`)。
2.  **ViewModel (`ChatPageViewModel.cs`)**:
    * **实现**: `IQueryAttributable` 接口，以接收导航传入的 `ChatId`。
    * **属性**:
        * `[ObservableProperty] long ChatId`。
        * `[ObservableProperty] string OutgoingText`。
        * `ObservableCollection<TdApi.Message> Messages { get; }`。
    * **`IQueryAttributable.ApplyQueryAttributes`**:
        * 解析 `query["ChatId"]` 并设置 `ChatId` 属性。
        * 一旦 `ChatId` 被设置，立即触发 `LoadMessagesCommand`。
    * **命令**:
        * `ICommand LoadMessagesCommand`: 调用 `ITelegramService.ExecuteAsync<TdApi.Messages>(new TdApi.GetChatHistory { ChatId = this.ChatId, Limit = 100 })`。将返回的 `messages.Messages_` 填充到 `Messages` 集合。
        * `ICommand SendCommand`:
            1.  获取 `OutgoingText`。
            2.  清空 `OutgoingText`。
            3.  构建 `TdApi.InputMessageContent.InputMessageText`。
            4.  调用 `ITelegramService.ExecuteAsync(new TdApi.SendMessage { ChatId = this.ChatId, InputMessageContent = content })`。
    * **实时更新**: 订阅 `ITelegramService.OnUpdateReceived`。
        * **`case UpdateNewMessage`**:
            * 检查 `update.Message.ChatId`是否等于当前的 `ChatId`。
            * 如果是，将 `update.Message` 添加到 `Messages` 集合的末尾 (或开头，取决于排序)。


#### 阶段 4：文件与媒体处理 (File & Media Handling)

**目标**: 实现图片、视频、文档的下载与上传功能。这是聊天软件的核心体验。

1.  **服务层 (`TelegramService`) 扩展**:
    * **下载管理**: TDLib 不会自动下载大文件（如视频、文档）。它只会下载缩略图。
    * 创建 `RequestDownload(int fileId)` 方法。此方法调用 TDLib 的 `DownloadFile(fileId, ...)`。
    * **更新广播**: 必须**精细处理** `UpdateFile`。此更新包含 `file.Local.Path` (下载完成路径), `file.Local.IsDownloadingActive`, `file.Local.DownloadedPrefixSize` (用于进度条)。`TelegramService` 必须将这些细粒度的更新广播出去。
    * 创建 `GetFile(int fileId)` 方法，用于检查文件本地状态。

2.  **ViewModel (`ChatPageViewModel`) 扩展**:
    * **DataTemplateSelector**: 这是必需的。必须创建一个 `MessageTemplateSelector` 类，它在 `ChatPage.xaml` 的 `CollectionView` 中使用。
    * **Selector 逻辑**: 根据 `message.Content` 的类型 (e.g., `MessageText`, `MessagePhoto`, `MessageDocument`)，返回不同的 `DataTemplate` (e.g., `TextMessageTemplate`, `PhotoMessageTemplate`)。

3.  **Views (`ChatPage.xaml`)**:
    * 在 `<ContentPage.Resources>` 中定义所有新的 `DataTemplate`。
    * **`PhotoMessageTemplate`**:
        * 包含一个 `Image` 控件。
        * `Image.Source` 绑定到 `message.Content.Photo.Sizes[...].Photo.Local.Path`。
        * **关键**: 如果 `Path` 为空（未下载），则显示一个“下载”按钮，该按钮绑定到 ViewModel 上的 `DownloadAttachmentCommand(message.Content.Photo.Sizes[...].Photo.Id)`。
    * **`DocumentMessageTemplate`**:
        * 包含一个“文件”图标、`Label` (文件名) 和一个“下载”/“打开”按钮。
        * 逻辑同上。

4.  **上传逻辑 (`ChatPageViewModel`)**:
    * **View**: 在 `ChatPage.xaml` 的输入区域添加一个“📎” (附件) 按钮。
    * **命令**: `AttachFileCommand`。
    * **逻辑**:
        1.  调用 MAUI 的 `FilePicker.PickAsync()` API，让用户从 macOS 文件系统中选择文件。
        2.  获取文件路径 (`result.FullPath`)。
        3.  构建 `InputMessageContent`。如果是图片，则为 `new TdApi.InputMessageContent.InputMessagePhoto { Photo = new TdApi.InputFile.InputFileLocal { Path = result.FullPath } }`。
        4.  调用 `ITelegramService.ExecuteAsync(new TdApi.SendMessage { ... })`。

#### 阶段 5：实时状态与交互 (Real-time Presence & Interactions)

**目标**: 为应用注入“灵魂”，使其感觉“实时在线”。

1.  **服务层 (`TelegramService`) 扩展**:
    * 必须处理并广播以下更新：
        * `UpdateUserStatus`: 用户在线状态（在线、离线、最后在线时间）。
        * `UpdateChatUserIsTyping`: “...正在输入”状态。
        * `UpdateMessageContent`: 消息被编辑。
        * `UpdateDeleteMessages`: 消息被删除。
        * `UpdateChatReadInbox/UpdateChatReadOutbox`: 消息已读回执（双勾）。

2.  **ViewModel (`ChatListViewModel`) 扩展**:
    * **处理 `UpdateUserStatus`**: 查找 `Chats` 集合中相关的 `Chat`，并更新其关联的 `User` 状态（用于在列表上显示“在线”）。
    * **处理 `UpdateChatUserIsTyping`**: 查找对应 `Chat`，设置一个临时状态 `IsTyping = true`。必须启动一个 `Timer` (e.g., 5秒)，时间到了自动将 `IsTyping = false`（因为 "停止输入" 事件不总是可靠）。

3.  **ViewModel (`ChatPageViewModel`) 扩展**:
    * **页面标题**: 绑定一个 `UserStatusText` 属性。当收到 `UpdateUserStatus` 时，更新此属性（例如 "在线" 或 "最后上线于 5 分钟前"）。
    * **处理 `UpdateMessageContent`**: 在 `Messages` 集合中找到对应的 `message.Id`，并用新内容替换它。
    * **处理 `UpdateDeleteMessages`**: 在 `Messages` 集合中找到并**移除**所有匹配 `messageIds` 的消息。
    * **发送已读回执**: 在 `OnAppearing` (页面出现时) 或当用户滚动到底部时，ViewModel 必须调用 `ITelegramService.ExecuteAsync(new TdApi.ViewMessages { ChatId = this.ChatId, ... })`。

#### 阶段 6：用户与群组详情 (Profiles & Context)

**目标**: 允许用户查看联系人、群组和频道信息。

1.  **新页面 (View + ViewModel): `ProfilePage`**:
    * **View**: 显示一个 `Image` (头像), `Label` (姓名), `Label` (电话/用户名), `Label` (简介)。如果是群组，则显示 `CollectionView` (成员列表)。
    * **ViewModel**:
        * 接收 `ChatId` 或 `UserId` 作为导航参数。
        * 调用 `GetUser(userId)` 或 `GetChat(chatId)` 来获取详细信息。
        * 实现头像下载逻辑 (复用阶段 4)。

2.  **导航**:
    * 在 `ChatPage.xaml` 的顶部标题栏添加一个点击手势，导航到 `ProfilePage`。
    * 在 `ChatListViewModel` 的 `SelectChatCommand` 中，区分是打开 `ChatPage` 还是 `ProfilePage`（例如，点击头像是 `ProfilePage`，点击消息是 `ChatPage`）。

3.  **新页面 (View + ViewModel): `ContactsPage`**:
    * **View**: 一个 `CollectionView` 显示联系人列表。
    * **ViewModel**: 调用 `GetContacts()`，将结果填充到 `ObservableCollection`。

#### 阶段 7：应用状态与连接管理 (App State & Connectivity)

**目标**: 使应用启动流程健壮，并处理网络问题。

1.  **新页面 (View + ViewModel): `LoadingPage`** (启动页):
    * **`MauiProgram.cs` 修改**: 将 `AppShell.CurrentItem` 的初始路由指向 `LoadingPage`。
    * **`LoadingViewModel`**:
        1.  构造时注入 `ITelegramService`。
        2.  订阅 `ITelegramService.OnUpdateReceived`。
        3.  **关键逻辑**: 等待**第一个** `UpdateAuthorizationState`。
        4.  `case AuthorizationStateReady`: 导航到 `ChatListPage` (`Shell.Current.GoToAsync(...)`)。
        5.  `case AuthorizationStateWait...` (任何非 Ready 状态): 导航到 `LoginPage`。
    * **`TelegramService` 修改**: 必须在 `InitializeAsync` (启动时) 立即开始处理更新，以便 `LoadingPage` 能接收到初始状态。

2.  **连接状态 (全局 UI)**:
    * **`TelegramService`**: 处理 `UpdateConnectionState` (`Connecting`, `Updating`, `Ready`, `WaitingForNetwork`)。
    * 将此状态保存在一个**全局可观察属性**中（例如，在一个 `ConnectionService` 单例中）。
    * **`AppShell.xaml`**: 在页面顶部（例如 `FlyoutHeader` 或底部）添加一个 `Label` 或 `ActivityIndicator`，其 `IsVisible` 和 `Text` 绑定到 `ConnectionService` 的状态。
    * **效果**: 当断网时，App 顶部显示“正在连接...”。

#### 阶段 8：错误处理与优化 (Error Handling & Refinement)

**目标**: 捕获所有 TDLib 异常，并提供流畅的用户体验。

1.  **`TelegramService` 扩展**:
    * `ExecuteAsync` (TdSharp 提供的) 会抛出 `TdException`。
    * 在所有 `ViewModel` 的 `Command` 逻辑中，必须使用 `try...catch (TdException ex)` 块。
    * **Catch 块**: 使用 MAUI 的 `Page.DisplayAlert("错误", ex.Message, "确定")` 向用户显示错误。
2.  **UI 优化 (虚拟化)**:
    * **`ChatListPage` / `ChatPage`**: 对于 `CollectionView`，确保使用 `ItemsUpdatingScrollMode="KeepLastItemInView"` (用于聊天页面) 或 `KeepItemsInView` (用于列表)。
    * **增量加载**: 在 `ChatPageViewModel` 中，当 `CollectionView` 滚动到顶部时 (`Scrolled` 事件)，触发 `LoadMoreMessagesCommand`，调用 `GetChatHistory` 并传入 `fromMessageId` (当前列表顶端的消息 ID) 来加载更早的消息。
3.  **退出逻辑**:
    * 创建一个 `SettingsPage`。
    * 添加“退出登录”按钮，绑定 `LogoutCommand`。
    * **`LogoutCommand`**: 调用 `ITelegramService.ExecuteAsync(new TdApi.LogOut())`。
    * **`TelegramService`**: 必须监听 `UpdateAuthorizationState` 变为 `AuthorizationStateClosed`。
    * 当 `Closed` 时，App 必须清理本地数据库（或在下次启动时重建），并立即导航回 `LoginPage` (`Shell.Current.GoToAsync($"//{nameof(LoginPage)}")`)。

---
明白了。您需要一个**完整且详尽**的蓝图，涵盖从“最小可行产品 (MVP)”到“功能完备的商业级应用”的**所有**阶段。

之前的 8 个阶段是核心功能。现在，我们将扩展蓝图，包括高级交互、数据管理、应用设置以及最终的打包部署。

这是为您和您的 Agent 准备的**最终版完整项目蓝图**。

---



#### 阶段 9：高级消息交互 (Advanced Interactions)

**目标**: 实现除“发送”之外的所有核心聊天交互，使用户体验完整。

1.  **View (`ChatPage.xaml`)**:
    * **消息 `DataTemplate`**: 在每条消息上添加一个上下文菜单 (Context Menu) 或长按/右键点击手势 (`TapGestureRecognizer` / `PointerGestureRecognizer`)。
    * **交互按钮**: 菜单应包含“回复”、“转发”、“编辑”、“删除”按钮。
    * **回复 UI**: 在底部的消息输入区域上方，添加一个“回复预览” `Grid` (绑定 `IsVisible` 和 `ReplyToMessage.Content` 摘要)，以及一个“取消回复”按钮。

2.  **ViewModel (`ChatPageViewModel`)**:
    * **属性**: `[ObservableProperty] TdApi.Message ReplyToMessage`。
    * **命令**:
        * `ICommand BeginReplyCommand(TdApi.Message message)`:
            1.  设置 `ReplyToMessage = message`。
            2.  将 `Editor` (输入框) 设为焦点。
        * `ICommand CancelReplyCommand`: 设置 `ReplyToMessage = null`。
        * `ICommand BeginEditCommand(TdApi.Message message)`:
            1.  设置 `OutgoingText = (message.Content as TdApi.MessageContent.MessageText).Text.Text`。
            2.  保存一个 `Message EditingMessage` 状态。
            3.  将 `SendCommand` 的逻辑切换为“编辑模式”。
        * `ICommand ForwardCommand(TdApi.Message message)`: (复杂) 需要导航到一个“聊天选择器”页面，选择目标聊天后，调用 `ForwardMessages`。
        * `ICommand DeleteMessageCommand(TdApi.Message message)`: 调用 `DeleteMessages` (注意 `revoke` 参数，决定是“为我删除”还是“为所有人删除”)。
    * **`SendCommand` 逻辑 (扩展)**:
        * **检查**: 如果 `ReplyToMessage != null`，构建 `TdApi.SendMessage` 并设置 `ReplyToMessageId = ReplyToMessage.Id`。
        * **检查**: 如果处于 `EditingMessage` 状态，调用 `EditMessageText`。
        * **完成后**: 必须重置 `ReplyToMessage = null` 和 `EditingMessage = null`。

#### 阶段 10：头像与文件缓存 (Avatar & File Caching)

**目标**: 高效加载、显示和缓存用户/群组头像及其他媒体，减少网络请求和 TDLib 负载。

1.  **服务层 (新服务): `IAvatarCacheService` (Singleton)**
    * **职责**: 充当 `Image` 控件和 `TelegramService` 之间的中间层。
    * **方法**: `async Task<string> GetProfilePhotoPathAsync(long entityId, TdApi.ProfilePhoto photo)` (entityId 可以是 `ChatId` 或 `UserId`)。
    * **逻辑**:
        1.  检查 `photo.Small.Local.Path` 是否存在。如果存在，直接返回。
        2.  如果不存在，检查一个本地字典 (内存缓存) 看是否正在下载 `photo.Small.Id`。
        3.  如果未下载，调用 `ITelegramService.DownloadFileAsync(photo.Small.Id)`。
        4.  监听 `UpdateFile` 事件，当该 `FileId` 下载完成时，获取 `local.Path`，存入内存缓存，并返回路径。
    * **`TelegramService` 扩展**: `DownloadFileAsync` 必须是一个 `Task`，它内部调用 `DownloadFile`，然后等待（或轮询）`UpdateFile` 直到该 `FileId` 完成。

2.  **ViewModel (所有 VM，如 `ChatListViewModel`)**:
    * **禁止**: ViewModel **不应**直接处理文件。
    * **绑定**: `Chat` 对象应扩展一个 `AvatarPath` 属性。
    * **逻辑**: 当 `Chat` 对象被加载时 (e.g., in `LoadChatsCommand`)，**异步**调用 `IAvatarCacheService.GetProfilePhotoPathAsync` 并设置 `AvatarPath` 属性。

3.  **View (所有 View，如 `ChatListPage.xaml`)**:
    * **`Image` 绑定**: `<Image Source="{Binding AvatarPath}" />`。
    * **占位符**: 使用 MAUI 的 `.Handler` 或第三方库（如 `FFImageLoading` - 如果支持 MAUI）来实现平滑加载和占位符（例如，显示 `chat.Title` 的首字母作为默认头像）。

#### 阶段 11：应用设置与本地持久化 (App Settings & Persistence)

**目标**: 允许用户配置应用行为，并将这些设置持久化在设备本地。

1.  **新页面 (View + ViewModel): `SettingsPage`**:
    * **View**: 使用 `TableView` 或 `VerticalStackLayout` 创建设置项。
        * `SwitchCell` (开关): "启用通知", "下载大文件"
        * `EntryCell` (输入): "本地缓存路径" (或使用 `FileSystem.AppDataDirectory`)
        * `Button`: "退出登录" (已在阶段 8 定义), "清理缓存"

2.  **新服务 (新服务): `ISettingsService` (Singleton)**:
    * **职责**: 管理应用偏好设置。
    * **技术**: 使用 MAUI 内置的 `Preferences` API (`Microsoft.Maui.Storage.Preferences`)。
    * **属性**: `bool AreNotificationsEnabled { get; set; }`, `bool AutoDownloadMedia { get; set; }`。
    * `get` 和 `set` 访问器应自动从 `Preferences.Get()` 和 `Preferences.Set()` 读写。
    * **`SettingsViewModel`**: 注入 `ISettingsService` 并将其属性直接暴露给 View。

3.  **`TelegramService` 扩展**:
    * 注入 `ISettingsService`。
    * **逻辑**: 在下载逻辑（阶段 4）中，必须检查 `_settingsService.AutoDownloadMedia` 属性，再决定是否自动调用 `DownloadFile`。

#### 阶段 12：通知 (Notifications)

**目标**: 当应用在后台或未激活时，向用户推送新消息通知。

1.  **macOS 权限**:
    * 在 `Platforms/MacCatalyst/Info.plist` 中添加 `NSUserNotificationsUsageDescription` 键，描述为何需要通知权限。
2.  **服务层 (`TelegramService`) 扩展**:
    * **注入**: `INotificationManager` (来自 `CommunityToolkit.Maui` 或自定义)。
    * **权限请求**: 在 `AuthorizationStateReady` (登录成功) 后，立即请求本地通知权限。
    * **更新处理器 (`OnUpdateReceived`)**:
        * **`case UpdateNewMessage`**:
            1.  检查 `message.IsOutgoing` (不通知自己的消息)。
            2.  检查 `ISettingsService.AreNotificationsEnabled`。
            3.  检查 `message.ChatId` 是否被静音 ( `chat.NotificationSettings.UseDefaultMuteUntil` )。
            4.  如果所有检查通过，调用 `INotificationManager.Show(title, messageContent)` 来显示一个 macOS 本地通知。

#### 阶段 13：多账户支持 (Multi-Account Support)

**目标**: (非常高级) 允许用户同时登录和切换多个 Telegram 账户。

1.  **架构重构 (核心)**:
    * **`TelegramService` 必须重构**。它不能再是一个**单例 (Singleton)**。
    * **新服务: `IAccountManagerService` (Singleton)**:
        * 职责: 管理一个 `Dictionary<int, ITelegramService>` 列表，`int` 是账户 `UserId`。
        * 方法: `CreateAccountInstance()`, `SwitchAccount(int userId)`, `GetCurrentAccountService()`。
    * **`ITelegramService` (重构)**:
        * 必须成为**作用域 (Scoped)** 或**瞬态 (Transient)** 实例。
        * 它的构造函数必须接受一个 `accountId` 或 `databaseDirectory` 参数。
        * `SetTdlibParameters` 中的 `DatabaseDirectory` 必须是唯一的（例如 `tdlib-data/account1`, `tdlib-data/account2`）。
    * **DI 变更**: `MauiProgram.cs` 注册 `IAccountManagerService` 为 Singleton。
    * **ViewModel 变更**: 所有 ViewModel 现在注入 `IAccountManagerService`。当它们需要 `ITelegramService` 时，它们调用 `_accountManager.GetCurrentAccountService()`。

2.  **UI 变更**:
    * **`AppShell.xaml` (Flyout)**: 必须在汉堡菜单中显示一个“账户切换器” UI。
    * **`LoadingPage` / `LoginPage`**: 必须重构以处理多账户登录（如果无账户，显示登录；如果有账户，显示 `LoadingPage` 并加载默认账户）。

#### 阶段 14：打包与部署 (Packaging & Deployment)

**目标**: 将项目构建为可在其他 Mac 电脑上安装和运行的 `.app` 包。

1.  **配置 `Info.plist`**:
    * 位于 `Platforms/MacCatalyst/Info.plist`。
    * 必须设置 `CFBundleIdentifier` (应用包ID, e.g., `com.mycompany.mauitelegramclient`)。
    * 必须设置 `CFBundleDisplayName` (应用名称)。
    * 必须设置 `MinimumOSVersion`。
2.  **配置 `.csproj` (项目文件)**:
    * 在 `Release` 配置下，设置 `$(ApplicationId)` 和 `$(ApplicationTitle)`。
    * **关键**: 为 Mac Catalyst 配置代码签名。这需要一个 [Apple Developer Program](https://developer.apple.com/programs/) 账户。
    * 设置 `CodeSignKey` 和 `ProvisioningProfile` (用于 App Store) 或 `CodeSignKey` 和 `PackageSigningKey` (用于 Developer ID，在 App Store 之外分发)。
3.  **构建命令**:
    * 执行 `dotnet publish -f:net8.0-maccatalyst -c:Release /p:CreatePackage=true`。
    * **公证 (Notarization)**: 如果在 App Store 之外分发，构建的 `.app` 必须上传到 Apple 的公证服务以进行安全扫描，否则 macOS 的 Gatekeeper 将阻止其运行。
4.  **图标 (AppIcon)**:
    * 必须在 `Resources/AppIcon/appicon.svg` (或 .png) 放置高质量的应用图标。MAUI 会自动为 macOS 生成所有需要的尺寸。

---

