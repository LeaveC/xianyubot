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
- Node.js (Windows系统必需，macOS/Linux上可选)
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

### Windows特定安装步骤
如果您使用的是Windows系统，请确保：

1. 安装Node.js（必需）：
   - 访问 [Node.js官网](https://nodejs.org/)下载并安装LTS版本
   - 安装时勾选"Add to PATH"选项
   - 安装完成后，在命令提示符中验证：`node --version`

2. 创建数据目录：
   ```cmd
   mkdir data
   ```

3. 解决可能的权限问题：
   - 以管理员身份运行命令提示符或PowerShell
   - 或确保您有足够的权限创建和写入文件

4. 如果遇到SSL验证错误，可使用：
   ```cmd
   set PYTHONHTTPSVERIFY=0
   ```

5. **JavaScript运行时解决方案**：
   - **方案一**: 确保Node.js安装且在PATH中（推荐）
   - **方案二**: 如果无法安装Node.js，系统会尝试使用js2py作为备选方案
   - **方案三**: 如果上述方案都失败，关键功能会回退到纯Python实现

6. **Node.js安装故障排除**：
   - 如果执行`node --version`时提示"不是内部或外部命令"
   - 检查Node.js是否正确安装
   - 确认Node.js目录已添加到系统PATH
   - 在安装后重启命令提示符或PowerShell
   - 如果路径中有空格，尝试使用短路径名称

### 获取登录凭证
XianyuBot会自动管理登录凭证，不需要手动设置cookies：

- 首次运行时，系统会自动打开浏览器让您登录闲鱼
- 登录成功后，凭证会自动保存，下次启动无需再次登录
- 如需刷新登录状态，可使用 `--login` 参数

#### 方式一：使用独立脚本获取
```bash
# 运行自动获取脚本
python scripts/get_cookies.py
```

#### 方式二：使用命令行参数强制刷新
```bash
# 使用--login参数强制刷新登录凭证
python run.py --login
```

### 使用方法

运行主程序：
```bash
python run.py
```

## 系统兼容性

### Windows支持
本项目已针对Windows系统进行了优化：
- 使用`Chromium`浏览器代替Firefox获取登录凭证
- 优化路径处理，解决目录分隔符问题
- 解决`asyncio`事件循环兼容性问题
- 添加Node.js环境检测和配置
- 多级JavaScript运行时解决方案：
  - 主方案：Node.js（自动检测常见安装路径）
  - 备选方案：js2py纯Python实现
  - 兜底方案：纯Python实现关键函数

### macOS/Linux支持
在macOS和Linux系统上：
- 默认使用Firefox浏览器
- 自动处理路径和权限

## 📁 项目结构

```