# 🚀 XianyuBot - 模块化闲鱼客服机器人系统

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/) [![LLM Powered](https://img.shields.io/badge/LLM-powered-FF6F61)](https://platform.openai.com/)

XianyuBot 是基于 XianyuAutoAgent 重构的模块化闲鱼智能客服系统，实现闲鱼平台7×24小时自动化值守，支持多专家协同决策、智能议价和上下文感知对话。

## 🌟 核心特性

### 模块化架构
- 🧩 **核心模块分离** - 聊天上下文、Agent决策、API接口完全解耦
- 🔌 **插件式设计** - 支持自定义专家插件开发
- 🛠️ **配置灵活** - 独立配置文件管理

### 智能对话引擎
- 💬 **上下文感知** - 完整对话历史记忆管理
- 🧠 **专家路由** - 基于意图识别的多专家动态分发
- 💰 **议价系统** - 智能阶梯降价策略

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
python -m playwright install firefox

# 4. 配置环境变量
cp .env.example .env
# 编辑.env文件，填入必要的API密钥和配置
```

### 获取登录凭证
XianyuBot会自动管理登录凭证，不需要手动设置cookies：

- 首次运行时，系统会自动打开浏览器让您登录闲鱼
- 登录成功后，凭证会自动保存，下次启动无需再次登录
- 如需刷新登录状态，可使用 `--login` 参数

#### 方式一：使用独立脚本获取
```bash
# 运行自动获取脚本
python xianyubot/scripts/get_cookies.py
```

#### 方式二：使用命令行参数强制刷新
```bash
# 使用--login参数强制刷新登录凭证
python -m src.main --login
```

### 使用方法

运行主程序：
```bash
python -m src.main
```

## 📁 项目结构

```