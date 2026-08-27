# AstrBot 人设切换插件

[![Version](https://img.shields.io/badge/version-v1.3.0-blue.svg)](https://github.com/yvdi-abc/astrbot_plugin_persona_switch)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![AstrBot](https://img.shields.io/badge/AstrBot-Plugin-orange.svg)](https://github.com/Soulter/AstrBot)

一个为 [AstrBot](https://github.com/Soulter/AstrBot) 设计的人设快速切换插件，支持**会话级人设**（每个群/私聊独立）与**全局人设**两种模式，并提供完善的权限管理功能。

## ✨ 功能特性

### 🎭 核心功能

- **`/人设`** - 查看当前人设与可用人设列表（含描述）
- **`/人设列表`** - 查看所有可用人设及当前激活的人设
- **`/人设切换 <人设ID>`** - 一键切换到指定人设
- **`/人设恢复`** - 恢复为默认人设
- **`/人设随机`** - 随机切换一个人设
- **`/人设信息 <人设ID...>`** - 查看人设的完整 system_prompt

### 🎯 两种切换模式（配置项控制）

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **会话级**（默认开启） | 每个群/私聊独立切换人设，互不影响 | 多个群聊需要不同人设 |
| **全局** | 切换所有人设，所有会话生效 | 单一人设统一管理 |

### 🔐 权限控制

插件提供了灵活的权限管理功能，适合多用户环境：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `session_mode` | 会话级人设模式（true=每个会话独立，false=全局） | `true` |
| `show_desc` | 人设列表是否显示描述 | `true` |
| `restrict_non_admin` | 限制非管理员用户切换人设 | `false` |
| `max_personas_for_non_admin` | 非管理员用户可切换的人设数量上限（0=不限制） | `0` |
| `allowed_personas_for_non_admin` | 非管理员用户可切换的人设ID白名单（空=允许所有） | `[]` |

## 📦 安装

### 方法一：通过 AstrBot 插件商店（推荐）

1. 在 AstrBot 控制面板中打开插件商店
2. 搜索 "人设切换"
3. 点击安装并重启 AstrBot

### 方法二：手动安装

```bash
git clone https://github.com/yvdi-abc/astrbot_plugin_persona_switch.git
```

将 `astrbot_plugin_persona_switch` 文件夹复制到 AstrBot 的插件目录，重启 AstrBot 或在控制面板重载插件。

## 🚀 使用示例

### 查看可用人设

```
用户: /人设
Bot: 📌 当前人设: **default**
     模式: 会话级（本会话独立）

     可用人设:
       · 猫娘 - 你是一只可爱的猫娘，喜欢撒娇
       · 胡桃 - 你是原神中的胡桃，古灵精怪
       · 老师 - 你是一位严谨的老师
```

### 切换人设（会话级）

```
用户: /人设切换 猫娘
Bot: ✅ 本会话已切换人设到: **猫娘**
```

### 恢复默认

```
用户: /人设恢复
Bot: ✅ 本会话已恢复默认人设（当前跟随全局: default）
```

### 随机人设

```
用户: /人设随机
Bot: 🎲 本会话随机切换人设到: **胡桃**
```

### 查看人设详情

```
用户: /人设信息 猫娘 胡桃
Bot: 📋 **猫娘**
     你是一只可爱的猫娘，喜欢撒娇...
```

## 🔧 工作原理

### 会话级人设

插件通过 AstrBot 的会话存储（`SharedPreferences`）为每个会话（群/私聊）独立记录 `persona_id`，该值的优先级**高于**全局默认人设。切换只影响当前会话，不影响其他会话。

### 全局人设

关闭 `session_mode` 后，插件通过 AstrBot 配置 API 修改全局 `default_personality`，所有会话生效。

## 📝 注意事项

- 会话级人设需要 AstrBot 4.16+ 版本支持
- 人设列表中的描述取自各人设 `system_prompt` 的首行
- 非管理员权限限制仅在 `restrict_non_admin` 开启时生效
- 全局模式下切换会写入 AstrBot 主配置，请谨慎操作

## 🔄 更新日志

### v1.3.0
- ✨ **新增会话级人设模式**：每个群/私聊独立切换人设，互不影响（`session_mode` 配置）
- ✨ 新增 `/人设` 快捷指令（查看当前人设 + 列表）
- ✨ 新增 `/人设恢复` 指令：一键恢复默认人设
- ✨ 新增 `/人设随机` 指令：随机切换人设
- ✨ 新增 `/人设信息` 指令：查看人设完整 system_prompt
- ✨ 人设列表支持显示人设描述（`show_desc` 配置）
- 🔧 仪表板地址改为从配置文件读取，不再硬编码端口
- 📦 修正仓库结构：插件文件移至仓库根目录（修复嵌套目录导致的安装问题）

### v1.2.0
- 初始功能：人设列表、人设切换、权限控制

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 👤 作者

**yvdi-abc**

---

如果这个插件对你有帮助，欢迎给个 ⭐ Star！
