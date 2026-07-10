# 💬 GreenChat

GreenChat 是一个使用 Python 3、Flask、Bootstrap-Flask、AJAX 和 SQLite3 构建的自托管私人聊天应用。它提供基于浏览器的账户管理、私人会话、多行消息、文件传输、未读消息跟踪、实时用户搜索、会话管理以及易于阅读的 TXT 聊天记录导出功能。

本项目包含两个版本：

- 📁 **标准多文件版** —— 使用独立的模板和静态资源文件，推荐用于常规开发。
- 📦 **独立单文件版** —— 将 Flask 后端、模板、CSS 和 JavaScript 全部整合在一个 Python 文件中。

GreenChat 适用于小规模私人部署、内部团队、课堂、局域网、个人服务器以及 Flask 开发练习。用户只需使用现代网页浏览器，无需安装桌面端或移动端客户端。

## 🎯 项目用途

GreenChat 允许用户注册、登录、搜索其他账户，并通过以下形式的路由开启私人会话：

```text
/chat/username
```

消息通过 AJAX 发送和获取，因此每次操作后页面都不需要重新加载。用户账户、密码哈希、消息元数据、已读位置和会话历史记录均存储在 SQLite3 中。上传的文件存储在本地 `uploads` 目录中。

界面设计参考了常见的 QQ 和微信布局，包括可点击的会话列表项、未读消息徽标、消息预览、时间戳、右键上下文菜单、左右消息气泡，以及位于聊天页面底部的消息输入区域。

## ✨ 主要功能

### 👤 账户与身份验证

- 用户注册
- 用户登录与退出
- 修改密码页面
- 用户名不区分大小写且必须唯一
- 基于 Session 的身份验证
- PBKDF2-HMAC-SHA256 密码哈希
- 随机密码盐值
- 对会修改数据的请求进行 CSRF 验证
- 应用层不限制密码长度，但密码不能为空

密码不会以可读明文形式存储。SQLite3 数据库保存的是带随机盐值的 PBKDF2-HMAC-SHA256 密码哈希。

### 💬 私人消息

- 通过 `/chat/<username>` 进行一对一私人聊天
- 使用 AJAX 发送消息并轮询新消息
- 区分接收与发送消息气泡
- 消息时间戳
- 未读消息数量
- 自动更新已读位置
- 使用 `Ctrl+Enter` 发送消息
- 使用 `Enter` 插入新行

### 🧾 精确保留文本格式

GreenChat 会保留消息的原始结构，适合发送源代码、配置文件、日志、命令以及其他需要预格式化显示的内容。

支持保留：

- 换行
- 行首空格
- 连续空格
- Tab 缩进
- 空白行
- 较长的多行消息

服务器在保存消息前会检查消息中是否包含可见内容，但不会删除原始缩进。

### 📎 文件传输

- 可以单独发送文件，也可以同时附带文字消息
- 显示原始文件名和文件大小
- 下载文件前必须通过身份验证
- 只有会话双方可以下载对应文件
- Flask 请求最大尺寸为 4 GiB

Flask 中设置 4 GiB 并不会覆盖 Nginx、Apache、Cloudflare、托管平台或其他反向代理设置的上传限制。这些限制必须分别配置。

### 🔎 实时用户搜索

- 输入时通过 AJAX 实时显示搜索建议
- 保留原有完整用户列表页面
- 使用最长公共子序列算法计算匹配分数
- 按 LCS 分数从高到低排序结果
- 支持使用方向键进行键盘导航
- 按 Enter 打开当前选中的搜索结果
- 按 Esc 关闭建议菜单
- 点击搜索结果可直接打开 `/chat/<username>`

### 📋 会话管理

会话页面的使用方式类似 QQ 或微信的消息列表。每一行显示：

- 对方用户名
- 最新消息预览
- 最近活动时间
- 未读消息数量

点击整行即可打开聊天。右键点击某个会话会打开上下文菜单，可以进入聊天或导出完整聊天记录。

### 🤝 双向会话显示规则

只有双方都至少向对方发送过一条消息后，该会话才会出现在常规会话列表中。

```text
Alice 向 Bob 发送了一条消息。
Bob 尚未回复。
结果：该会话不会显示在常规会话列表中。

Bob 打开 /chat/Alice 并发送回复。
结果：该会话会显示在双方的会话列表中。
```

此规则可以减少由陌生账户单方面发送消息所造成的会话列表垃圾信息。

### 📤 导出 TXT 聊天记录

用户可以通过聊天页面或会话列表的右键菜单，将完整私人会话导出为易于阅读的 UTF-8 TXT 文件。

导出的聊天记录包含：

- 双方参与者的用户名
- 导出日期与时间
- 消息总数
- 消息序号
- 发送者与接收者姓名
- 消息时间戳与方向
- 原始多行文本与缩进
- 附件名称与大小
- 相关消息标识符

只有会话参与者可以导出对应的聊天记录。

## 🗂️ 项目结构

```text
GreenChat/
├── greenchat_server.py          # 标准多文件版 Flask 入口
├── greenchat_standalone.py      # 完整独立单文件版
├── requirements.txt
├── README.md
├── README_CN.md
├── LICENSE
├── chat.db                      # 首次启动后自动创建
├── uploads/                     # 用于保存上传文件，首次启动后自动创建
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── change_password.html
│   ├── conversations.html
│   ├── users.html
│   ├── chat.html
│   └── error.html
└── static/
    ├── css/
    │   └── app.css
    └── js/
        ├── common.js
        ├── conversations.js
        ├── users.js
        └── chat.js
```

## 📦 环境要求

- 推荐使用 Python 3.10 或更高版本
- pip
- Git
- 现代网页浏览器

标准版使用 `requirements.txt` 中列出的依赖：

```text
Flask>=3.1,<4
Bootstrap-Flask>=2.5,<3
```

独立单文件版只需要 Flask。

## 🚀 标准版：完整安装与启动

复制下面的完整命令块即可。每条命令单独占一行，既方便阅读，也可以通过一个复制按钮一次性复制全部命令。

### Linux 和 macOS

```bash
git clone https://github.com/wangyifan349/GreenChat.git
cd GreenChat
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
export CHAT_SECRET_KEY="replace-this-with-a-long-random-secret-key"
python3 greenchat_server.py
```

### Windows PowerShell

```powershell
git clone https://github.com/wangyifan349/GreenChat.git
cd GreenChat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:CHAT_SECRET_KEY="replace-this-with-a-long-random-secret-key"
python greenchat_server.py
```

服务器启动后，打开：

```text
http://127.0.0.1:5000
```

应用会自动创建 `chat.db`、所需的数据库表以及 `uploads` 目录。

## 📦 独立单文件版：完整安装与启动

独立单文件版不使用 `templates` 或 `static` 目录。完整的前端和后端代码都包含在 `greenchat_standalone.py` 中。

### Linux 和 macOS

```bash
git clone https://github.com/wangyifan349/GreenChat.git
cd GreenChat
python3 -m pip install --upgrade pip
python3 -m pip install Flask
export CHAT_SECRET_KEY="replace-this-with-a-long-random-secret-key"
python3 greenchat_standalone.py
```

### Windows PowerShell

```powershell
git clone https://github.com/wangyifan349/GreenChat.git
cd GreenChat
python -m pip install --upgrade pip
python -m pip install Flask
$env:CHAT_SECRET_KEY="replace-this-with-a-long-random-secret-key"
python greenchat_standalone.py
```

不要在同一主机和同一端口上同时运行 `greenchat_server.py` 与 `greenchat_standalone.py`。

## 🌐 公网部署说明

Flask 内置服务器适用于开发、测试以及受信任的本地环境。若要部署到公网，请使用生产级 WSGI 服务器和正确配置的反向代理。

重要部署要求：

- 设置一个足够长且固定不变的 `CHAT_SECRET_KEY`
- 关闭 Flask 调试模式
- 使用 HTTPS
- 限制数据库和上传目录的文件权限
- 同时备份 `chat.db` 与 `uploads`
- 配置反向代理的上传大小限制和超时时间
- 监控可用磁盘空间
- 不要把 `chat.db` 或 `uploads` 作为不受限制的公共静态文件暴露

对于 Nginx，若要允许 4 GiB 请求体，至少需要配置：

```nginx
client_max_body_size 4G;
```

大文件目前会通过单个 HTTP 请求上传。上传中断后暂时无法继续传输。如果经常传输数 GiB 的文件，后续应实现分块上传与断点续传。

## 💾 数据库与备份

GreenChat 在 SQLite3 中存储以下数据：

- 用户名
- 密码哈希
- 账户创建时间
- 消息文本
- 发送者与接收者关系
- 附件元数据
- 消息时间戳
- 已读位置

上传文件的实际内容单独存储在 `uploads` 中。完整备份必须同时包含 `chat.db` 和整个 `uploads` 目录。

## ❤️ 赞助

如果 GreenChat 对你有帮助，可以通过自愿的加密货币捐赠支持项目继续开发。

```text
Bitcoin (BTC): bc1qxqfhumpqtnxrznkx9r4xsp8m6zsedtgusjns7p
Ethereum (ETH): 0x2d92f9e4d8ac7effa9cd7cd5eccd364cac7c201b
```

发布前请仔细核对每个地址。加密货币交易通常不可撤销。

## ⚖️ 许可证

GreenChat 仅使用 **GNU Affero General Public License v3.0**（`AGPL-3.0-only`）授权。

你可以按照许可证条款使用、修改和重新分发本项目。如果你修改了该软件，并通过网络向用户提供交互服务，则必须按照 AGPL 的要求，向这些用户提供相应源代码的获取方式。完整许可证内容请参阅项目中的 `LICENSE` 文件。

## 🔓 安全与加密说明

GreenChat **不是加密通信工具**。它不提供端到端加密、加密消息存储、加密附件或密码学身份验证。

服务器可以读取消息和上传文件。服务器管理员，或任何获得足够服务器访问权限的人，都可能读取这些内容。HTTPS 可以保护浏览器与服务器之间的传输过程，但不能阻止服务器本身访问消息内容。

在没有加入适当的加密设计并完成专业安全审查之前，请勿将本项目用于高度敏感、机密或受监管的通信。
