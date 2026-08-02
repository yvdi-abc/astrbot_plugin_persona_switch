import re
import json
import httpx
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api import logger
from astrbot.api.star import Context, Star
from astrbot.core.utils.astrbot_path import get_astrbot_data_path


class PersonaSwitchPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.astrbot_api = "http://127.0.0.1:6185"
        self.jwt_token = None

    def _get_dashboard_credentials(self) -> tuple[str, str]:
        """从配置文件读取仪表板凭据"""
        try:
            config_path = Path(get_astrbot_data_path()) / "cmd_config.json"
            with open(config_path, encoding="utf-8-sig") as f:
                cfg = json.load(f)
            dash = cfg.get("dashboard", {})
            return dash.get("username", "astrbot"), dash.get("password", "")
        except Exception as e:
            logger.error(f"读取仪表板配置失败: {e}")
            return "", ""

    async def _login(self) -> str:
        """登录 AstrBot 获取 JWT token"""
        username, password = self._get_dashboard_credentials()
        if not username or not password:
            logger.error("无法获取仪表板凭据")
            return None
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.astrbot_api}/api/auth/login",
                    json={"username": username, "password": password}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "ok":
                        self.jwt_token = data["data"]["token"]
                        return self.jwt_token
                logger.error(f"登录失败: {resp.text}")
        except Exception as e:
            logger.error(f"登录异常: {e}")
        return None

    async def _get_headers(self) -> dict:
        if not self.jwt_token:
            await self._login()
        return {"Authorization": f"Bearer {self.jwt_token}", "Content-Type": "application/json"}

    async def _get_config(self) -> dict:
        try:
            headers = await self._get_headers()
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.astrbot_api}/api/config/default", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "ok":
                        return data["data"]["config"]
        except Exception as e:
            logger.error(f"获取配置异常: {e}")
        return None

    async def _update_config(self, config: dict) -> bool:
        try:
            headers = await self._get_headers()
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.astrbot_api}/api/config/astrbot/update",
                    headers=headers,
                    json={"config": config, "conf_id": "default"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("status") == "ok"
        except Exception as e:
            logger.error(f"更新配置异常: {e}")
        return False

    def _is_allowed_persona(self, persona_id: str) -> bool:
        """检查人设是否在非管理员允许列表中"""
        allowed = self.config.get("allowed_personas_for_non_admin", [])
        if not allowed:
            return True  # 空列表表示允许所有
        return persona_id in allowed

    def _check_non_admin_limit(self, event: AstrMessageEvent, personas: list) -> tuple[bool, str]:
        """检查非管理员用户的限制"""
        if event.is_admin():
            return True, ""

        if not self.config.get("restrict_non_admin", False):
            return True, ""

        max_count = self.config.get("max_personas_for_non_admin", 0)
        if max_count > 0 and len(personas) > max_count:
            return False, f"当前人设数量({len(personas)})超过管理员设置的上限({max_count})"

        return True, ""

    @filter.command("人设列表")
    async def list_personas(self, event: AstrMessageEvent) -> MessageEventResult:
        """列出所有可用人设"""
        try:
            personas = await self.context.persona_manager.get_all_personas()
        except Exception as e:
            logger.error(f"获取人设列表失败: {e}")
            yield event.plain_result("获取人设列表失败")
            return

        if not personas:
            yield event.plain_result("没有人设，请先在 AstrBot 面板添加人设")
            return

        # 非管理员限制检查
        allowed, msg = self._check_non_admin_limit(event, personas)
        if not allowed:
            yield event.plain_result(msg)
            return

        config = await self._get_config()
        current = config.get("provider_settings", {}).get("default_personality", "") if config else ""

        # 过滤非管理员可见的人设
        if not event.is_admin() and self.config.get("restrict_non_admin", False):
            visible = [p for p in personas if self._is_allowed_persona(p.persona_id)]
        else:
            visible = personas

        lines = [f"当前人设: {current}\n", "可用人设:"]
        for p in visible:
            marker = " (当前)" if p.persona_id == current else ""
            lines.append(f"  - {p.persona_id}{marker}")

        yield event.plain_result("\n".join(lines))

    @filter.command("人设切换")
    async def switch_persona(self, event: AstrMessageEvent) -> MessageEventResult:
        """切换人设"""
        msg = re.sub(r'\[MSG_ID:\d+\]', '', event.message_str).strip()
        parts = msg.split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("用法: /人设切换 <人设ID>")
            return

        target = parts[1].strip()

        try:
            personas = await self.context.persona_manager.get_all_personas()
        except Exception as e:
            logger.error(f"获取人设列表失败: {e}")
            yield event.plain_result("获取人设列表失败")
            return

        # 非管理员限制检查
        allowed, msg = self._check_non_admin_limit(event, personas)
        if not allowed:
            yield event.plain_result(msg)
            return

        # 匹配人设
        matched = None
        for p in personas:
            if p.persona_id == target:
                matched = p
                break

        if not matched:
            available = [p.persona_id for p in personas]
            yield event.plain_result(f"人设 '{target}' 不存在，可用人设: {', '.join(available)}")
            return

        # 非管理员权限检查
        if not event.is_admin() and self.config.get("restrict_non_admin", False):
            if not self._is_allowed_persona(matched.persona_id):
                yield event.plain_result(f"你没有权限切换到人设: {matched.persona_id}")
                return

        # 获取完整配置
        config = await self._get_config()
        if not config:
            yield event.plain_result("获取配置失败")
            return

        # 修改人设
        config.setdefault("provider_settings", {})["default_personality"] = matched.persona_id

        # 通过API更新配置（会触发pipeline重载）
        if await self._update_config(config):
            yield event.plain_result(f"已切换人设到: {matched.persona_id}")
        else:
            yield event.plain_result("切换人设失败")
