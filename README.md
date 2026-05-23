# Voice Input Tool - 语音输入助手

一款轻量级 Windows 桌面语音输入工具，点击浮动按钮即可录音，自动将语音转为文字并粘贴到当前光标位置。

## 功能特点

- **一键语音输入**：点击浮动麦克风按钮开始/停止录音
- **高精度中文语音识别**：基于 FunASR Paraformer 本地模型，无需联网
- **智能文本后处理**：利用 GLM-4-flash 大模型自动纠错、添加标点
- **自动粘贴**：识别完成后自动将文本粘贴到当前光标位置
- **可拖拽浮动按钮**：悬浮于所有窗口之上，可自由拖拽移动
- **系统托盘**：最小化到系统托盘，不占用任务栏空间

## 架构设计

```
用户点击按钮
    │
    ▼
┌──────────────┐
│  FloatingMic  │  PySide6 浮动按钮 UI
│  (main.py)    │  状态：空闲→录音→处理→空闲
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ AudioRecorder │  sounddevice 录音
│ (recorder.py) │  16kHz 单声道 int16
└──────┬───────┘
       │ numpy float32
       ▼
┌──────────────┐
│   ASRClient   │  FunASR Paraformer-zh
│ (asr_client)  │  本地推理，RTF ~0.15
└──────┬───────┘
       │ 原始文本
       ▼
┌──────────────┐
│ TextProcessor │  GLM-4-flash API
│(text_processor│  纠错 + 加标点
└──────┬───────┘
       │ 精修文本
       ▼
┌──────────────┐
│   paster.py   │  剪贴板 + Ctrl+V 模拟
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
git clone https://github.com/YOUR_USERNAME/voice-input-tool.git
cd voice-input-tool

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
2. **开始录音**：点击按钮，变为红色闪烁表示正在录音
3. **停止录音**：再次点击，变为黄色表示正在处理
4. **自动粘贴**：处理完成后文本自动粘贴到当前光标位置，按钮恢复蓝色
5. **移动按钮**：按住拖拽可移动按钮位置
6. **退出**：右键系统托盘图标 → 退出

## 项目结构

```
voice-input-tool/
├── main.py            # 主程序入口，PySide6 UI + 流程控制
├── recorder.py        # 音频录制模块
├── asr_client.py      # ASR 语音识别客户端
├── text_processor.py  # GLM 文本后处理
├── paster.py          # 剪贴板粘贴模块
├── config.py          # 配置文件
├── requirements.txt   # Python 依赖
├── tests/             # 单元测试
│   ├── test_recorder.py
│   ├── test_asr_client.py
│   ├── test_text_processor.py
│   ├── test_paster.py
│   └── test_config.py
└── README.md
```

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 语音识别 | FunASR Paraformer-zh | 阿里达摩院开源，本地推理 |
| 文本后处理 | GLM-4-flash | 智谱 AI 大模型 API |
| 桌面 UI | PySide6 (Qt) | 浮动窗口 + 系统托盘 |
| 音频录制 | sounddevice | 跨平台音频输入 |
| 粘贴功能 | ctypes + pyperclip | Windows 原生键盘模拟 |

## 测试

```bash
pip install pytest
python -m pytest tests/ -v
```

## 许可证

MIT License
