# 🌧️ 长江雨课堂AI答题助手

基于 [aglorice/Raincourse](https://github.com/aglorice/Raincourse) 项目改编，专为**长江雨课堂**优化的 AI 智能答题工具。

> ⚠️ **免责声明**：本工具仅用于学习交流和技术研究，请勿用于商业用途或学术作弊！

***

## 🎯 项目说明

本项目是**长江雨课堂**的辅助答题工具，支持：

- 🔐 **微信扫码登录** - 安全便捷的认证方式
- 🤖 **AI智能答题** - 基于多种大模型自动作答
- 📊 **题目导出** - 支持多种格式导出题目
- 🎨 **双界面支持** - 提供 GUI 图形界面和 CLI 命令行界面

***

## ⚠️ 重要说明

### GUI 版本（推荐）

> 🎉 **主要功能界面，功能完整且经过测试**

GUI 版本是本项目的主要开发方向，提供完整的图形化操作体验：

- ✅ 微信扫码登录
- ✅ 课程列表浏览
- ✅ AI智能答题（核心功能）
- ✅ 实时答题日志
- ✅ 题目导出（JSON/CSV/Excel/Markdown）
- ✅ API配置管理
- ✅ 用户会话管理

**推荐使用 GUI 版本**，点击运行 `run_gui.bat` 或执行 `pythonw gui.py` 即可启动。

### CLI 命令行版本

> ⚠️ **仅 AI 答题功能经过测试，其他功能未完整测试**

命令行版本（`main.py`）保留基础功能，仅 **AI答题** 功能进行了测试验证。其他功能（本地答案答题、答案导出等）可能存在未知问题，如需使用请注意。

***

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Windows 10/11（其他系统未测试）

### 安装依赖

```bash
cd Raincourse
pip install -r requirements.txt
```

### 运行 GUI 版本（推荐）

#### 方式一：双击运行

```
run_gui.bat
```

#### 方式二：命令行运行

```bash
pythonw gui.py
```

> 💡 使用 `pythonw` 不会显示命令行窗口，如需调试可使用 `python gui.py`

### 运行 CLI 版本

```bash
python main.py
```

***

## 🎨 GUI 功能介绍

### 登录

支持两种登录方式：

1. **扫码登录**：使用雨课堂APP扫描二维码
2. **已保存账号**：加载之前登录过的会话

### AI答题

1. 在左侧导航选择「AI答题」
2. 选择对应课程
3. 选择要作答的作业/考试
4. 点击「开始AI答题」
5. 观看实时日志了解答题进度
6. **答题完成后手动检查并提交**（重要！）

### 题目导出

在AI答题页面选择课程和作业后：

1. 点击「导出题目到本地」
2. 选择导出格式（JSON/CSV/Excel/Markdown）
3. 确认导出

### API配置

支持多种大模型服务商：

| 服务商                | API类型       | 默认模型           |
| ------------------ | ----------- | -------------- |
| MiniMax Token Plan | Anthropic兼容 | MiniMax-M2.7   |
| MiniMax Official   | OpenAI兼容    | abab6.5-chat   |
| OpenAI             | OpenAI      | gpt-4          |
| Anthropic          | Claude      | claude-3-opus  |
| 智谱AI (GLM)         | OpenAI兼容    | glm-4          |
| DeepSeek           | OpenAI兼容    | deepseek-chat  |
| 通义千问               | OpenAI兼容    | qwen-max       |
| 豆包                 | OpenAI兼容    | doubao-pro-32k |
| 硅基流动               | OpenAI兼容    | Qwen2.5-72B    |

配置步骤：

1. 进入「设置」→「API配置」
2. 选择服务商，点击「配置」
3. 填入API密钥
4. 点击「测试连接」验证
5. 保存配置并启用

***

## 📁 项目结构

```
Raincourse/
├── api/
│   └── api.py              # 雨课堂API封装
├── utils/
│   ├── ai_solver.py        # AI答题核心模块
│   ├── exam.py             # 答题流程控制
│   ├── ws_login.py         # WebSocket扫码登录
│   ├── api_config_manager.py # 多API配置管理
│   ├── question_exporter.py # 题目导出服务
│   ├── seesion_io.py       # 会话管理
│   ├── utils.py            # 通用工具函数
│   └── ui.py               # CLI界面组件
├── web/
│   ├── index.html          # GUI主页面
│   ├── css/style.css       # 样式文件
│   └── js/app.js           # 前端交互逻辑
├── user/                   # 用户会话存储
├── answer/                 # 答题报告存储
├── exports/                # 导出文件存储
├── config/                 # API配置文件
├── main.py                 # CLI命令行入口
├── gui.py                  # GUI图形界面入口
├── config.py               # 全局配置
├── logic.py                # CLI业务逻辑
├── requirements.txt        # 依赖列表
├── build.spec              # PyInstaller配置
└── build.bat               # 打包脚本
```

***

## 🔧 打包为 EXE

如需将 GUI 版本打包为独立可执行文件：

```batch
build.bat
```

打包完成后，`dist/RaincourseAIHelper.exe` 即为独立运行的可执行文件。

***

## 📝 答题说明

### AI答题流程

1. **选择考试**：从课程列表中选择对应的考试
2. **开始答题**：AI会自动分析每道题目并给出答案
3. **实时日志**：右侧面板显示答题进度和状态
4. **手动提交**：AI答题完成后，请手动检查答案并提交

### 答题限制

- AI生成的答案仅供参考，不保证100%正确
- 建议答题后仔细核对答案
- 部分题型（如主观题）可能无法正确作答

***

## 🔒 隐私说明

- 用户会话信息保存在本地 `user/` 目录
- API密钥使用简单加密存储在 `config/` 目录
- 不会上传任何用户数据到第三方服务器
- 所有 `.json` 文件已加入 `.gitignore`，不会同步到仓库

***

## 📜 许可证

本项目基于 [MIT License](LICENSE) 开源。

***

## 🙏 致谢

- 原始项目：[aglorice/Raincourse](https://github.com/aglorice/Raincourse)
- AI支持：[MiniMax](https://platform.minimaxi.com)

***

## 💬 反馈

如有问题或建议，请提交 Issue。

***

**made with ❤️ for study**
