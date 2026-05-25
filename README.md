# Voice Input Tool - 语音输入助手

一款轻量级 Windows 桌面语音输入工具，点击浮动按钮或按 F8 即可录音，自动将语音转为文字并粘贴到当前光标位置。

## 功能特点

- **一键语音输入**：点击浮动麦克风按钮开始/停止录音
- **流式实时预览**：说话时实时显示部分识别文字，边说边出字
- **高精度中文语音识别**：基于 FunASR Paraformer 本地模型，无需联网
- **专业词汇热词**：自定义热词文件，提升专业术语识别准确率
- **智能文本后处理**：利用 GLM-5.1 大模型自动纠错、添加标点
- **自动粘贴**：识别完成后自动将文本粘贴到当前光标位置
- **剪贴板保护**：粘贴后自动恢复原有剪贴板内容
- **录音时长显示**：录音时实时显示已录时长，最长 60 秒自动停止
- **提示音反馈**：开始/停止录音时播放不同音调的提示音
- **全场景通知**：超时、识别失败、录音太短等异常均有托盘通知
- **历史记录**：自动保存最近 10 条语音输入，托盘菜单可重新粘贴
- **开机自启**：勾选后系统启动自动运行，无需手动打开
- **开关纠错**：托盘菜单可关闭 GLM 纠错，直接输出 ASR 原文
- **托盘快捷操作**：左键托盘图标也可触发录音
- **位置记忆**：拖拽后自动记住按钮位置，重启恢复
- **可拖拽浮动按钮**：悬浮于所有窗口之上，可自由拖拽移动
- **系统托盘**：最小化到系统托盘，不占用任务栏空间

## 架构设计

```
用户点击按钮 / 左键托盘图标
        │
        ▼
┌──────────────┐
│  FloatingMic  │  PySide6 浮动按钮 UI (ui.py)
│  三态切换     │  状态：空闲→录音→处理→空闲
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ AudioRecorder │  sounddevice 录音
│ (recorder.py) │  16kHz 单声道 int16
│  chunk回调    │  每 600ms 推送音频块
└──────┬───────┘
       │ numpy float32
       ├──→ ┌──────────────────┐
       │    │ StreamingASRClient│  paraformer-zh-streaming
       │    │ 实时预览（边说边出字）│  chunk_size=[0,10,5]
       │    └──────────────────┘
       │
       ▼ (停止录音后)
┌──────────────┐
│   ASRClient   │  FunASR Paraformer-zh
│ (asr_client)  │  本地推理 + 热词增强
└──────┬───────┘
       │ 原始文本
       ▼
┌──────────────┐
│ TextProcessor │  GLM-5.1 API
│(text_processor│  纠错 + 加标点 + 热词引导
└──────┬───────┘
       │ 精修文本
       ▼
┌──────────────┐
│  Clipboard +  │  pyperclip + Ctrl+V
│  Auto Paste   │  剪贴板还原
└──────────────┘
```

## 快速开始

### 环境要求

- Windows 10/11
- Python 3.10+（推荐 3.12）
- 麦克风设备

### 安装

```bash
# 克隆仓库
git clone https://github.com/Gern713/voice_input_tool.git
cd voice_input_tool

# 创建虚拟环境（推荐 conda）
conda create -n voice python=3.12 -y
conda activate voice

# 安装依赖
pip install -r requirements.txt

# 配置 API Key（用于文本后处理）
# 方式一：设置环境变量
set ZHIPU_API_KEY=your_api_key_here

# 方式二：直接编辑 config.py
```

获取智谱 AI API Key：[https://open.bigmodel.cn](https://open.bigmodel.cn)

### 运行

```bash
python main.py
```

首次运行会自动下载 ASR 模型（约 900MB），请耐心等待。

## 使用方法

1. **启动程序**：运行后在屏幕右侧出现蓝色麦克风浮动按钮
2. **开始录音**：点击按钮，听到高音提示，按钮变红闪烁
3. **实时预览**：说话时按钮下方显示部分识别文字
4. **停止录音**：再次点击按钮，听到低音提示，按钮变黄处理中
5. **自动粘贴**：处理完成后文本自动粘贴到当前光标位置，按钮恢复蓝色
6. **取消处理**：处理中点击按钮可取消
7. **移动按钮**：按住拖拽可移动按钮位置
8. **退出**：右键系统托盘图标 → 退出

### 热词配置

编辑项目根目录的 `hotwords.txt`，每行一个专业术语：

```
PyTorch
FunASR
Paraformer
GLM
```

也可通过托盘菜单 → 编辑热词 快速打开编辑。保存后重启程序生效。

### 状态说明

| 状态 | 颜色 | 说明 |
|------|------|------|
| 空闲 | 蓝色 | 等待用户操作 |
| 录音中 | 红色脉冲 | 正在录音，显示识别文字或时长 |
| 处理中 | 黄色 | ASR + GLM 处理中 |

## 项目结构

```
voice_input_tool/
├── main.py            # 程序入口
├── ui.py              # FloatingMic 浮动按钮 UI
├── app.py             # VoiceInputApp 流程编排
├── history.py         # 历史记录模块
├── recorder.py        # 音频录制模块（支持 chunk 回调）
├── asr_client.py      # ASR 客户端（离线 + 流式）
├── text_processor.py  # GLM 文本后处理
├── config.py          # 配置文件
├── hotwords.txt       # 热词配置文件
├── requirements.txt   # Python 依赖
├── tests/             # 单元测试（71 项）
│   ├── test_recorder.py
│   ├── test_asr_client.py
│   ├── test_streaming_asr.py
│   ├── test_text_processor.py
│   ├── test_config.py
│   ├── test_history.py
│   ├── test_ui_state.py
│   ├── test_paste_flow.py
│   └── test_integration.py
└── README.md
```

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 语音识别 | FunASR Paraformer-zh | 阿里达摩院开源，本地推理 |
| 流式识别 | FunASR Paraformer-zh-streaming | 边说边出字，600ms 粒度 |
| 文本后处理 | GLM-5.1 | 智谱 AI 大模型 API |
| 桌面 UI | PySide6 (Qt) | 浮动窗口 + 系统托盘 |
| 音频录制 | sounddevice | 跨平台音频输入 |
| 粘贴功能 | ctypes + pyperclip | Windows 原生键盘模拟 |

## 第三方依赖

| 包名 | 用途 |
|------|------|
| PySide6 | Qt 桌面 GUI 框架 |
| sounddevice | 麦克风音频录制 |
| numpy | 音频数据处理 |
| funasr | 语音识别模型推理 |
| modelscope | ASR 模型下载 |
| pyperclip | 剪贴板操作 |

## 测试

```bash
pip install pytest
python -m pytest tests/ -v
```

## 演示视频

[演示视频链接（待补充）]

## 许可证

MIT License
