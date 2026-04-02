# 🌧️ 长江雨课堂 AI 学习助手

基于 [aglorice/Raincourse](https://github.com/aglorice/Raincourse) 项目改编，专为长江雨课堂场景优化的学习辅助工具。

> ⚠️ **免责声明**：本项目仅用于学习交流和技术研究，请遵守学校与平台规则。

---

## 🎯 项目简介

这是一个面向长江雨课堂的学习辅助项目，提供以下能力：

- 🔐 微信扫码登录与会话复用
- 🤖 AI 辅助作答（多模型支持）
- 📊 题目导出（JSON / CSV / Excel / Markdown）
- 🖥️ GUI + CLI 双入口

---

## 🚀 版本说明

### ✅ GUI 版本（推荐）

GUI 是当前主维护入口，功能完整、交互直观，推荐优先使用。

主要能力：

- 账号登录与会话管理
- 课程/作业列表浏览
- AI 作答与实时日志
- 本地题目导出
- API 配置与连通性测试

启动方式：

```bat
run_gui.bat
```

或：

```bash
pythonw gui.py
```

调试时：

```bash
python gui.py
```

### ⚙️ CLI 版本

CLI 入口为 `main.py`，适合脚本化使用。

```bash
python main.py
```

---

## 🧩 快速开始

### 环境要求

- Python 3.10+
- Windows 10/11（当前主要测试环境）

### 安装依赖

```bash
pip install -r requirements.txt
```

---

## 📝 GUI 使用流程

1. 登录账号（扫码或复用已保存会话）
2. 选择课程与作业/考试
3. 启动 AI 辅助作答并观察实时日志
4. 完成后手动复核并提交

> 💡 提示：AI 结果仅供参考，提交前建议逐题检查。

---

## 🤖 支持的模型平台

支持多种 OpenAI 兼容与 Anthropic 兼容平台，包含但不限于：

- MiniMax
- OpenAI
- Anthropic
- DeepSeek
- 智谱 GLM
- 通义千问
- 豆包
- 硅基流动

可在设置页配置 API Key、测试连接并切换模型。

---

## 📁 项目结构

```text
Raincourse/
├── api/                     # 平台接口封装
├── utils/                   # 核心业务模块（答题、登录、导出、配置）
├── web/                     # GUI 前端资源
├── user/                    # 本地用户会话
├── answer/                  # 本地答题记录与报告
├── exports/                 # 导出文件
├── config/                  # 本地配置
├── gui.py                   # GUI 入口
├── main.py                  # CLI 入口
├── requirements.txt         # Python 依赖
├── build.spec               # PyInstaller 配置
└── build.bat                # 打包脚本
```

---

## 🔧 打包 EXE

```bat
build.bat
```

产物默认位于 `dist/` 目录。

---

## 🔒 隐私与安全

- 登录会话与本地记录仅保存在本机
- API 密钥保存于本地配置文件
- 已通过 `.gitignore` 忽略敏感信息与运行产物，降低误提交风险

---

## 📚 相关文档

- GUI 使用说明：`README_GUI.md`
- 贡献指南：`CONTRIBUTING.md`
- 开源协议：`LICENSE`

---

## 🙏 致谢

- 原始项目：[aglorice/Raincourse](https://github.com/aglorice/Raincourse)

---

## 💬 反馈

欢迎提交 Issue 或 Pull Request。
