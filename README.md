# YaYaRename🌟

一个基于 PyQt5 的批量文件重命名工具,支持压缩包文件名的智能识别与批量重命名。✨

## 👩‍💻作者
Sherry@https://github.com/SherryBX

## ✨功能特点

- 🗂️支持压缩包文件类型自动识别 (.zip, .rar, .7z)
- ⚙️可配置文件类型与标签的映射关系
- 📝支持自定义前缀/后缀添加
- 📅内置常用前缀/后缀配置(日期、时间、版本号等)
- 🚀多线程处理,提高效率
- 📊实时进度显示
- 📝详细的处理日志

## 🔧安装说明

1. 确保已安装 Python 3.8 或更高版本
2. 安装所需依赖:
```bash
pip install PyQt5 rarfile py7zr
```
3. 对于 RAR 文件支持,需要安装 UnRAR:
   - Windows: 下载并安装 [UnRAR](https://www.win-rar.com/download.html)
   - Linux: `sudo apt-get install unrar` (Ubuntu/Debian)
   - macOS: `brew install unrar` (使用 Homebrew)

## 🎯使用说明

1. 运行程序:
```bash
python YaYaRename.py
```
2. 主要功能:
   - 选择要处理的文件夹
   - 配置文件类型映射关系
   - 添加自定义前缀/后缀
   - 使用预设的前缀/后缀配置
   - 设置处理线程数
   - 查看处理进度和日志

## 🛠️ 文件类型映射

默认支持以下文件类型映射:
- 🎨 .skp -> SU
- 🎮 .max -> 3D
- ✏️ .dwg -> CAD

## 📌 常用配置

### 🏷️ 前缀配置
- 📅 日期 (YYYYMMDD)
- ⏰ 时间 (HHMMSS)
- 📆 日期时间 (YYYYMMDD_HHMMSS)
- 🔖 版本 (V1.0)
- 📝 草稿 (Draft)
- ✅ 最终 (Final)

### 🏷️ 后缀配置
- 📅 修改日期
- 🔢 版本号
- ⭐ 状态
- ✔️ 审核
- 💾 备份

