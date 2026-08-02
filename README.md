# AstrBot 人设切换插件

[![Version](https://img.shields.io/badge/version-v1.2.0-blue.svg)](https://github.com/yvdi-abc/astrbot_plugin_persona_switch)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![AstrBot](https://img.shields.io/badge/AstrBot-Plugin-orange.svg)](https://github.com/Soulter/AstrBot)

一个为 [AstrBot](https://github.com/Soulter/AstrBot) 设计的人设快速切换插件，支持通过简单命令在多个预设人格之间无缝切换，并提供完善的权限管理功能。

## ✨ 功能特性

### 🎭 核心功能

- **`/人设列表`** - 查看所有可用人设及当前激活的人设
- **`/人设切换 <人设ID>`** - 一键切换到指定人设

### 🔐 权限控制

插件提供了灵活的权限管理功能，适合多用户环境：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `restrict_non_admin` | 限制非管理员用户切换人设 | `false` |
| `max_personas_for_non_admin` | 非管理员用户可切换的人设数量上限（0=不限制） | `0` |
| `allowed_personas_for_non_admin` | 非管理员用户可切换的人设ID白名单（空=允许所有） | `[]` |

## 📦 安装

### 方法一：通过 AstrBot 插件商店（推荐）

1. 在 AstrBot 控制面板中打开插件商店
2. 搜索 "人设切换"
3. 点击安装并重启 AstrBot

### 方法二：手动安装

1. 下载本仓库
```bash
git clone https://github.com/yvdi-abc/astrbot_plugin_persona_switch.git
```

2. 将 `astrbot_plugin_persona_switch` 文件夹复制到 AstrBot 的插件目录

3. 重启 AstrBot 或在控制面板重载插件

## 🚀 使用示例

### 查看可用人设

```
用户: /人设列表

Bot: 当前人设: default

可用人设:
  - default (当前)
  - assistant
  - creative
  - professional
```

### 切换人设

```
用户: /人设切换 creative

Bot: 已切换人设到: creative
```

### 权限限制示例

当配置了权限限制后，非管理员用户尝试切换未授权的人设：

```
用户: /人设切换 professional

Bot: 你没有权限切换到人设: professional
```

## ⚙️ 配置说明

在 AstrBot 控制面板的插件配置中，你可以设置以下参数：

```json
{
  "restrict_non_admin": false,
  "max_personas_for_non_admin": 0,
  "allowed_personas_for_non_admin": []
}
```

### 配置示例

**场景 1：完全开放**
```json
{
  "restrict_non_admin": false
}
```
所有用户都可以自由切换所有人设。

**场景 2：限制切换数量**
```json
{
  "restrict_non_admin": true,
  "max_personas_for_non_admin": 3
}
```
非管理员用户最多只能看到 3 个人设。

**场景 3：白名单模式**
```json
{
  "restrict_non_admin": true,
  "allowed_personas_for_non_admin": ["default", "assistant"]
}
```
非管理员用户只能切换到 `default` 和 `assistant` 两个人设。

## 🔧 技术实现

- **API 集成**: 通过 AstrBot HTTP API 进行配置管理
- **身份验证**: 使用 JWT token 进行安全的 API 调用鉴权
- **异步处理**: 基于 `httpx` 的异步 HTTP 请求处理
- **配置持久化**: 自动读取仪表板凭据并保持登录状态

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 📝 更新日志

### v1.2.0
- 添加权限控制功能
- 支持非管理员用户限制
- 支持人设白名单配置

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 👤 作者

**MiMoCode**

## 🙏 致谢

- [AstrBot](https://github.com/Soulter/AstrBot) - 优秀的聊天机器人框架
- 所有贡献者和用户

---

如果这个插件对你有帮助，欢迎给个 ⭐ Star！
