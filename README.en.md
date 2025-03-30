<p align="right">
   <a href="./README.md">中文</a> | <strong>English</strong>
</p>

<div align="center">

# 🚀 XianyuBot

<img src="./assets/logo.png" alt="XianyuBot Logo" width="180">

A modular Xianyu customer service bot system, providing 24/7 automated support on the Xianyu platform, featuring multi-expert collaborative decision-making, intelligent price negotiation, and context-aware conversations.

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

## 📝 Project Description

> [!NOTE]  
> XianyuBot is a modular Xianyu intelligent customer service system rebuilt based on [XianyuAutoAgent](https://github.com/shaxiu/XianyuAutoAgent), providing a more comprehensive architecture and more powerful features.

> [!IMPORTANT]  
> - This project is for personal learning purposes only, stability is not guaranteed, and it should not be used for commercial purposes.
> - Users must comply with Xianyu platform rules and relevant laws and regulations, and must not use it for illegal purposes.

## ✨ Core Features

<table>
<tr>
<th>Modular Architecture</th>
<th>Intelligent Conversation Engine</th>
</tr>
<tr>
<td>

- 🧩 **Core Module Separation** - Chat context, Agent decision-making, and API interfaces completely decoupled
- 🔌 **Plugin Design** - Support for custom expert plugin development
- 🛠️ **Flexible Configuration** - Independent configuration file management

</td>
<td>

- 💬 **Context Awareness** - Complete dialogue history memory management
- 🧠 **Expert Routing** - Intent-based dynamic dispatch to multiple experts
- 💰 **Negotiation System** - Intelligent tiered price reduction strategy

</td>
</tr>
</table>

## 🚴 Quick Start

### Requirements
- Python 3.8+
- Playwright (for obtaining login credentials)

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/xianyubot.git
cd xianyubot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers
python -m playwright install firefox chromium

# 4. Configure environment variables
cp .env.example .env
# Edit the .env file and fill in the necessary API keys and configurations
```

### Large Language Model Configuration

XianyuBot supports configuration of different large language models through environment variables. You can set the following parameters in the `.env` file:

```bash
# Main model - used for generating responses
LLM_MODEL=gpt-4-turbo

# Lightweight model - used for classification and other simple tasks
LLM_MODEL_LIGHT=gpt-3.5-turbo

# Temperature parameter - controls the creativity of responses (0.0-2.0)
LLM_TEMPERATURE=0.7
```

Supported model types include:
- OpenAI API models: `gpt-4o`, `gpt-4o-mini`, etc.
- Various local or open-source model APIs: `glm-4`, `qwen-max`, `deepseek`, etc. - any model compatible with the OpenAI API format

## 💻 Usage Instructions

### Obtaining Login Credentials

XianyuBot automatically manages login credentials, eliminating the need for manual cookie setup:

<table>
<tr>
<th>Method 1: Using a Standalone Script</th>
<th>Method 2: Using Command Line Parameters for Forced Refresh</th>
</tr>
<tr>
<td>

```bash
# Run the automatic credential acquisition script
python scripts/get_cookies.py
```

</td>
<td>

```bash
# Use the --login parameter to force refresh login credentials
python run.py --login
```

</td>
</tr>
</table>

### Running the Main Program

```bash
python run.py
```

### Command Line Arguments

XianyuBot supports the following command line arguments:

| Parameter | Description |
|------|------|
| `--login` | Force refresh of Xianyu login credentials, regardless of whether valid credentials currently exist |
| `--debug` | Enable debug mode, outputting more detailed log information |

Example:
```bash
# Enable debug mode and force re-login
python run.py --login --debug
```

## 🖥️ System Compatibility

XianyuBot currently supports the following operating systems:

<table>
<tr>
<th>macOS Support</th>
<th>Windows Support</th>
</tr>
<tr>
<td>

- Uses Firefox browser to obtain login credentials
- Automatically handles paths and permissions
- Full support for all features

</td>
<td>

- Uses `Chromium` browser instead of Firefox to obtain login credentials
- Optimized path handling, resolving directory separator issues
- Resolves `asyncio` event loop compatibility issues

</td>
</tr>
</table>

## 📁 Project Structure

```
xianyubot/
├── data/                # Data storage directory (cookies, history, etc.)
├── src/                 # Source code directory
│   ├── api/             # API interface module
│   │   ├── xianyu_api.py        # Xianyu API client
│   │   └── xianyu_websocket.py  # WebSocket real-time communication module
│   ├── agents/          # Intelligent agent module
│   │   ├── base.py              # Agent base class
│   │   └── expert_agents.py     # Expert agent implementation
│   ├── core/            # Core functionality module
│   │   └── context_manager.py   # Conversation context manager
│   └── utils/           # Utility function collection
├── prompts/             # Prompt templates
├── scripts/             # Helper scripts
│   └── get_cookies.py   # Get Xianyu login credentials
├── run.py               # Main program entry point
├── requirements.txt     # Dependency list
├── .env.example         # Environment variable example
└── README.md            # Project documentation
```

## 🧩 System Architecture

XianyuBot adopts a modular layered architecture design:

<table>
<tr>
<th>Layer</th>
<th>Functionality</th>
</tr>
<tr>
<td><strong>API Layer</strong></td>
<td>

- WebSocket connection maintenance
- Message sending and receiving management
- Session state monitoring

</td>
</tr>
<tr>
<td><strong>Core Layer</strong></td>
<td>

- Context Management: Records conversation history
- State Tracking: Follows transaction stages
- Message Routing: Dispatches to appropriate expert agents

</td>
</tr>
<tr>
<td><strong>Agent Layer</strong></td>
<td>

- Base Agent: Provides general conversation capabilities
- Expert Agents: Handles specific scenarios (negotiation, logistics, etc.)
- Collaborative Mechanism: Multi-expert collaborative decision-making

</td>
</tr>
<tr>
<td><strong>Tool Layer</strong></td>
<td>

- Login Management: Automatically obtains and refreshes login credentials
- Configuration Management: Flexible environment variable control

</td>
</tr>
</table>

## 📊 Performance and Limitations

| Metric | Value/Description |
|------|-----------|
| **Response Speed** | Average reply time < 3 seconds |
| **Concurrent Processing** | Single instance supports multiple concurrent sessions |
| **Memory Usage** | Approximately 150-300MB (depending on the number of active sessions) |
| **API Quota** | Depends on your OpenAI API Key limitations |

## 🔮 Future Plans

- [ ] Command-line automatic login (credential acquisition without browser)
- [ ] Knowledge base management (RAG support to enhance reply quality)
- [ ] Web management interface (visual configuration and monitoring)
- [ ] Compatibility with various model backends (suggestions welcome via issues)
- [ ] Add more expert agent types
- [ ] Support for multiple accounts simultaneously online
- [ ] Add statistical analysis functionality

## 🤝 Contributions and Support

Issues and Pull Requests are welcome to help improve XianyuBot! For usage problems, please submit detailed error reports on GitHub.

## 📄 License

This project is open-sourced under the MIT License.

## 🧸 Special Thanks

This project is rebuilt based on the following open-source project:
- [XianyuAutoAgent](https://github.com/shaxiu/XianyuAutoAgent) - An intelligent Xianyu customer service bot system, developed by [@shaxiu](https://github.com/shaxiu) and [@cv-cat](https://github.com/cv-cat)
</rewritten_file> 