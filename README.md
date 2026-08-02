# AstrBot 人设切换插件

AstrBot 人设切换插件，支持通过命令快速切换预设人设，支持管理员限制非用户切换权限。

## 功能特性

### 核心命令

- `/人设列表` - 查看所有可用人设及当前激活的人设
- `/人设切换 <人设ID>` - 切换到指定人设

### 权限控制

插件提供了灵活的权限管理功能：

1. **restrict_non_admin** - 限制非管理员用户切换人设
2. **max_personas_for_non_admin** - 非管理员用户可切换的人设数量上限（0=不限制）
3. **allowed_personas_for_non_admin** - 非管理员用户可切换的人设ID列表（空=允许所有）

## 安装

1. 将插件放置到 AstrBot 的插件目录
2. 重启 AstrBot 或重载插件
3. 在配置文件中根据需要调整权限设置

## 使用示例

```
/人设列表
# 输出：
# 当前人设: default
# 可用人设:
#   - default (当前)
#   - assistant
#   - creative

/人设切换 assistant
# 输出：已切换人设到: assistant
```

## 技术实现

- 通过 AstrBot API 进行身份验证和配置管理
- 使用 JWT token 进行 API 调用鉴权
- 异步 HTTP 请求处理

## 版本信息

- **版本**: v1.2.0
- **作者**: MiMoCode

## 许可证

MIT License
