<p align="right">
   <strong>中文</strong> | <a href="./README.en.md">English</a>
</p>

<div align="center">

# 🚀 XianyuBot

模块化闲鱼客服机器人系统，实现闲鱼平台7×24小时自动化值守，支持多专家协同决策、智能议价和上下文感知对话。

<p align="center">
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python Version">
  </a>
  <a href="https://platform.openai.com/">
    <img src="https://img.shields.io/badge/LLM-powered-FF6F61" alt="LLM Powered">
  </a>
  <a href="https://raw.githubusercontent.com/yourusername/xianyubot/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-brightgreen" alt="license">
  </a>
</p>

</div>

## 📝 项目说明

> [!NOTE]  
> XianyuBot 是基于 [XianyuAutoAgent](https://github.com/shaxiu/XianyuAutoAgent) 重构的模块化闲鱼智能客服系统，提供了更完善的架构和更强大的功能。

> [!IMPORTANT]  
> - 本项目仅供个人学习使用，不保证稳定性，请勿用于商业用途。
> - 使用者必须在遵循闲鱼平台规则以及相关法律法规的情况下使用，不得用于非法用途。

## ✨ 核心特性

<table>
<tr>
<th>模块化架构</th>
<th>智能对话引擎</th>
</tr>
<tr>
<td>

- 🧩 **核心模块分离** - 聊天上下文、Agent决策、API接口完全解耦
- 🔌 **插件式设计** - 支持自定义专家插件开发
- 🛠️ **配置灵活** - 独立配置文件管理

</td>
<td>

- 💬 **上下文感知** - 完整对话历史记忆管理
- 🧠 **专家路由** - 基于意图识别的多专家动态分发
- 💰 **议价系统** - 智能阶梯降价策略

</td>
</tr>
</table>

## 🚴 快速开始

### 环境要求
- Python 3.8+
- Playwright (获取登录凭证)

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/xianyubot.git
cd xianyubot

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装Playwright浏览器
python -m playwright install firefox chromium

# 4. 配置环境变量
cp .env.example .env
# 编辑.env文件，填入必要的API密钥和配置
```

### 大模型配置

XianyuBot支持通过环境变量配置不同的大模型，您可以在`.env`文件中设置以下参数：

```bash
# 主要模型 - 用于生成回复
LLM_MODEL=gpt-4-turbo

# 轻量级模型 - 用于分类等简单任务
LLM_MODEL_LIGHT=gpt-3.5-turbo

# 温度参数 - 控制回复的创意性 (0.0-2.0)
LLM_TEMPERATURE=0.7
```

支持的模型类型包括：
- OpenAI API模型：`gpt-4o`、`gpt-4o-mini`等
- 各类本地或开源模型API：`glm-4`、`qwen-max`、`deepseek`等任何兼容OpenAI API格式的模型

## 💻 使用方法

### 获取登录凭证

XianyuBot会自动管理登录凭证，不需要手动设置cookies：

<table>
<tr>
<th>方式一：使用独立脚本获取</th>
<th>方式二：使用命令行参数强制刷新</th>
</tr>
<tr>
<td>

```bash
# 运行自动获取脚本
python scripts/get_cookies.py
```

</td>
<td>

```bash
# 使用--login参数强制刷新登录凭证
python run.py --login
```

</td>
</tr>
</table>

### 运行主程序

```bash
python run.py
```

### 命令行参数

XianyuBot 支持以下命令行参数：

| 参数 | 说明 |
|------|------|
| `--login` | 强制重新获取闲鱼登录凭证，无论当前是否存在有效凭证 |
| `--debug` | 启用调试模式，输出更详细的日志信息 |

示例：
```bash
# 启用调试模式并强制重新登录
python run.py --login --debug
```

## 🖥️ 系统兼容性

XianyuBot 目前支持以下操作系统：

<table>
<tr>
<th>macOS支持</th>
<th>Windows支持</th>
</tr>
<tr>
<td>

- 使用Firefox浏览器获取登录凭证
- 自动处理路径和权限
- 完全支持所有功能

</td>
<td>

- 使用`Chromium`浏览器代替Firefox获取登录凭证
- 优化路径处理，解决目录分隔符问题
- 解决`asyncio`事件循环兼容性问题

</td>
</tr>
</table>

## 📁 项目结构

```
xianyubot/
├── data/                # 数据存储目录（cookies、历史记录等）
├── src/                 # 源代码目录
│   ├── api/             # API接口模块
│   │   ├── xianyu_api.py        # 闲鱼API客户端
│   │   └── xianyu_websocket.py  # WebSocket实时通信模块
│   ├── agents/          # 智能代理模块
│   │   ├── base.py              # 代理基类
│   │   └── expert_agents.py     # 专家代理实现
│   ├── core/            # 核心功能模块
│   │   └── context_manager.py   # 对话上下文管理器
│   └── utils/           # 工具函数集
├── prompts/             # 提示词模板
├── scripts/             # 辅助脚本
│   └── get_cookies.py   # 获取闲鱼登录凭证
├── run.py               # 主程序入口
├── requirements.txt     # 依赖列表
├── .env.example         # 环境变量示例
└── README.md            # 项目文档
```

## 🧩 系统架构

XianyuBot 采用模块化分层架构设计：

<table>
<tr>
<th>层级</th>
<th>功能</th>
</tr>
<tr>
<td><strong>API层</strong></td>
<td>

- 实现WebSocket连接维护
- 消息收发管理
- 会话状态监控

</td>
</tr>
<tr>
<td><strong>核心层</strong></td>
<td>

- 上下文管理：记忆对话历史
- 状态追踪：跟踪交易阶段
- 消息路由：分发到合适的专家代理

</td>
</tr>
<tr>
<td><strong>代理层</strong></td>
<td>

- 基础代理：提供通用对话能力
- 专家代理：处理特定场景（议价、物流等）
- 协同机制：多专家协作决策

</td>
</tr>
<tr>
<td><strong>工具层</strong></td>
<td>

- 登录管理：自动获取和刷新登录凭证
- 配置管理：灵活的环境变量控制

</td>
</tr>
</table>

## 📊 性能与限制

| 指标 | 数值/说明 |
|------|-----------|
| **响应速度** | 平均回复时间 < 3秒 |
| **并发处理** | 单实例支持多会话并发 |
| **内存占用** | 约150-300MB（取决于活跃会话数量） |
| **API额度** | 取决于您的OpenAI API Key限制 |

## 🔮 未来计划

- [ ] 命令行自动登录（免浏览器获取凭证）
- [ ] 知识库管理（支持RAG增强回复质量）
- [ ] Web管理界面（可视化配置和监控）
- [ ] 兼容各种模型后端（欢迎提交issues建议）
- [ ] 添加更多专家代理类型
- [ ] 支持多账号同时在线
- [ ] 添加统计分析功能

## 🤝 贡献与支持

欢迎提交Issue和Pull Request，共同改进XianyuBot！如有使用问题，请在GitHub上提交详细的错误报告。

## 📄 许可证

本项目采用MIT许可证开源。

## 🧸 特别鸣谢

本项目基于以下开源项目重构：
- [XianyuAutoAgent](https://github.com/shaxiu/XianyuAutoAgent) - 智能闲鱼客服机器人系统，由 [@shaxiu](https://github.com/shaxiu) 和 [@cv-cat](https://github.com/cv-cat) 开发