import asyncio
import json
import random
import re
from pathlib import Path

import httpx

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api import logger
from astrbot.api.star import Context, Star
from astrbot.core import sp
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

DEFAULT_PERSONA = "default"


class PersonaSwitchPlugin(Star):
    """人设切换插件。

    功能：
    - 会话级人设：每个会话（群/私聊）独立切换人设，互不影响（可配置）
    - 全局人设：也支持切换全局默认人设（关闭会话级时生效）
    - 人设列表：显示所有人设及当前生效人设，支持显示描述
    - 人设详情：查看单个或多个人的设详细信息
    - 恢复默认：一键恢复为默认人设
    - 随机人设：随机切换一个人设
    - 权限控制：限制非管理员可切换的人设范围与数量
    """

    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.astrbot_api = self._get_dashboard_url()
        self.jwt_token = None

    # ------------------------------------------------------------------ #
    # 基础工具                                                           #
    # ------------------------------------------------------------------ #

    def _get_dashboard_url(self) -> str:
        """从配置文件读取仪表板地址（端口不再硬编码）。"""
        try:
            config_path = Path(get_astrbot_data_path()) / "cmd_config.json"
            with open(config_path, encoding="utf-8-sig") as f:
                cfg = json.load(f)
            dash = cfg.get("dashboard", {})
            host = dash.get("host", "127.0.0.1")
            port = dash.get("port", 6185)
            return f"http://{host}:{port}"
        except Exception as e:
            logger.error(f"读取仪表板配置失败: {e}")
            return "http://127.0.0.1:6185"

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
                    json={"username": username, "password": password},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "ok":
                        self.jwt_token = data["data"]["token"]
                        return self.jwt_token
                logger.error(f"登录失败: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"登录异常: {e}")
        return None

    async def _get_headers(self) -> dict:
        if not self.jwt_token:
            await self._login()
        return {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json",
        }

    async def _get_config(self) -> dict:
        """获取 AstrBot 全局配置。"""
        try:
            headers = await self._get_headers()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.astrbot_api}/api/config/default",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "ok":
                        return data["data"]["config"]
        except Exception as e:
            logger.error(f"获取配置异常: {e}")
        return None

    async def _update_config(self, config: dict) -> bool:
        """更新 AstrBot 全局配置。"""
        try:
            headers = await self._get_headers()
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.astrbot_api}/api/config/astrbot/update",
                    headers=headers,
                    json={"config": config, "conf_id": "default"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("status") == "ok"
        except Exception as e:
            logger.error(f"更新配置异常: {e}")
        return False

    async def _get_personas(self) -> list:
        """获取所有人设列表。"""
        try:
            return await self.context.persona_manager.get_all_personas()
        except Exception as e:
            logger.error(f"获取人设列表失败: {e}")
            return []

    def _persona_desc(self, persona) -> str:
        """获取人设描述（取 system_prompt 首行）。"""
        prompt = getattr(persona, "system_prompt", "") or ""
        first_line = prompt.strip().splitlines()[0] if prompt.strip() else ""
        return first_line[:50]

    async def _get_global_persona(self) -> str:
        """获取全局默认人设 ID。"""
        config = await self._get_config()
        if config:
            return config.get("provider_settings", {}).get(
                "default_personality", DEFAULT_PERSONA
            )
        return DEFAULT_PERSONA

    async def _get_session_persona(self, umo: str) -> str | None:
        """获取会话级人设（None 表示未设置，跟随全局）。"""
        try:
            svc = await sp.get_async(
                scope="umo",
                scope_id=umo,
                key="session_service_config",
                default={},
            )
            return (svc or {}).get("persona_id")
        except Exception as e:
            logger.error(f"获取会话人设失败: {e}")
            return None

    async def _set_session_persona(self, umo: str, persona_id: str | None) -> bool:
        """设置/清除会话级人设。persona_id 为 None 时清除。

        使用读-改-写方式，仅修改 persona_id 字段，保留会话的其他配置
        （如 llm_enabled、tts_enabled 等），避免误删。
        """
        try:
            svc = await sp.get_async(
                scope="umo",
                scope_id=umo,
                key="session_service_config",
                default={},
            )
            svc = dict(svc or {})
            if persona_id is None:
                svc.pop("persona_id", None)
            else:
                svc["persona_id"] = persona_id
            await sp.put_async(
                scope="umo",
                scope_id=umo,
                key="session_service_config",
                value=svc,
            )
            return True
        except Exception as e:
            logger.error(f"设置会话人设失败: {e}")
            return False

    def _is_session_mode(self) -> bool:
        """是否启用会话级人设模式。"""
        return bool(self.config.get("session_mode", True))

    # ------------------------------------------------------------------ #
    # 权限检查                                                           #
    # ------------------------------------------------------------------ #

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

    def _visible_personas(self, event: AstrMessageEvent, personas: list) -> list:
        """过滤非管理员可见的人设。"""
        if not event.is_admin() and self.config.get("restrict_non_admin", False):
            return [p for p in personas if self._is_allowed_persona(p.persona_id)]
        return personas

    # ------------------------------------------------------------------ #
    # 指令                                                               #
    # ------------------------------------------------------------------ #

    @filter.command("人设")
    async def cmd_persona_status(self, event: AstrMessageEvent):
        """查看当前人设与列表"""
        yield await self._show_status(event)

    @filter.command("人设列表")
    async def cmd_list_personas(self, event: AstrMessageEvent):
        """列出所有可用人设"""
        yield await self._show_status(event)

    async def _show_status(self, event: AstrMessageEvent):
        personas = await self._get_personas()
        if not personas:
            return event.plain_result("没有人设，请先在 AstrBot 面板添加人设")

        allowed, msg = self._check_non_admin_limit(event, personas)
        if not allowed:
            return event.plain_result(msg)

        umo = event.unified_msg_origin
        session_mode = self._is_session_mode()

        # 当前生效人设
        current = None
        if session_mode:
            current = await self._get_session_persona(umo)
        if current is None:
            current = await self._get_global_persona()

        visible = self._visible_personas(event, personas)
        show_desc = self.config.get("show_desc", True)

        lines = [
            f"📌 当前人设: **{current}**",
            f"模式: {'会话级（本会话独立）' if session_mode else '全局（所有会话生效）'}",
            "",
            "可用人设:",
        ]
        for p in visible:
            marker = " 👈" if p.persona_id == current else ""
            desc = f" - {self._persona_desc(p)}" if show_desc else ""
            lines.append(f"  · {p.persona_id}{marker}{desc}")

        return event.plain_result("\n".join(lines))

    @filter.command("人设切换")
    async def cmd_switch_persona(self, event: AstrMessageEvent):
        """切换人设：/人设切换 <ID>"""
        msg = re.sub(r'\[MSG_ID:\d+\]', '', event.message_str).strip()
        parts = msg.split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("用法: /人设切换 <人设ID>（可用 /人设 查看列表）")
            return

        target = parts[1].strip()

        personas = await self._get_personas()
        if not personas:
            yield event.plain_result("没有人设，请先在 AstrBot 面板添加人设")
            return

        allowed, msg = self._check_non_admin_limit(event, personas)
        if not allowed:
            yield event.plain_result(msg)
            return

        matched = next((p for p in personas if p.persona_id == target), None)
        if not matched:
            available = [p.persona_id for p in personas]
            yield event.plain_result(f"人设 '{target}' 不存在，可用人设: {', '.join(available)}")
            return

        # 非管理员权限检查
        if not event.is_admin() and self.config.get("restrict_non_admin", False):
            if not self._is_allowed_persona(matched.persona_id):
                yield event.plain_result(f"你没有权限切换到人设: {matched.persona_id}")
                return

        umo = event.unified_msg_origin
        if self._is_session_mode():
            # 会话级切换（写入会话存储，立即生效）
            if await self._set_session_persona(umo, target):
                yield event.plain_result(f"✅ 本会话已切换人设到: **{target}**（立即生效，无需重启）")
            else:
                yield event.plain_result("❌ 切换人设失败")
        else:
            # 全局切换（通过配置 API，保存后即时生效）
            config = await self._get_config()
            if not config:
                yield event.plain_result("❌ 获取配置失败")
                return
            config.setdefault("provider_settings", {})["default_personality"] = target
            if await self._update_config(config):
                yield event.plain_result(f"✅ 已全局切换人设到: **{target}**（立即生效，无需重启）")
            else:
                yield event.plain_result("❌ 切换人设失败")

    @filter.command("人设恢复")
    async def cmd_reset_persona(self, event: AstrMessageEvent):
        """恢复默认人设"""
        umo = event.unified_msg_origin
        if self._is_session_mode():
            # 清除会话级人设，恢复为跟随全局（立即生效）
            if await self._set_session_persona(umo, None):
                global_p = await self._get_global_persona()
                yield event.plain_result(
                    f"✅ 本会话已恢复默认人设（立即生效，当前跟随全局: {global_p}）"
                )
            else:
                yield event.plain_result("❌ 恢复人设失败")
        else:
            # 全局恢复
            config = await self._get_config()
            if not config:
                yield event.plain_result("❌ 获取配置失败")
                return
            config.setdefault("provider_settings", {})["default_personality"] = DEFAULT_PERSONA
            if await self._update_config(config):
                yield event.plain_result(f"✅ 已恢复全局默认人设: {DEFAULT_PERSONA}（立即生效）")
            else:
                yield event.plain_result("❌ 恢复人设失败")

    @filter.command("人设随机")
    async def cmd_random_persona(self, event: AstrMessageEvent):
        """随机切换一个人设"""
        personas = await self._get_personas()
        if not personas:
            yield event.plain_result("没有人设，请先在 AstrBot 面板添加人设")
            return

        allowed, msg = self._check_non_admin_limit(event, personas)
        if not allowed:
            yield event.plain_result(msg)
            return

        visible = self._visible_personas(event, personas)
        # 排除默认人设，随机切换应换到其他风格
        candidates = [p for p in visible if p.persona_id != DEFAULT_PERSONA]
        if not candidates:
            yield event.plain_result("没有可随机切换的人设（除默认人设外）")
            return

        target = random.choice(candidates).persona_id

        umo = event.unified_msg_origin
        if self._is_session_mode():
            if await self._set_session_persona(umo, target):
                yield event.plain_result(f"🎲 本会话随机切换人设到: **{target}**（立即生效，无需重启）")
            else:
                yield event.plain_result("❌ 切换人设失败")
        else:
            config = await self._get_config()
            if not config:
                yield event.plain_result("❌ 获取配置失败")
                return
            config.setdefault("provider_settings", {})["default_personality"] = target
            if await self._update_config(config):
                yield event.plain_result(f"🎲 已随机切换全局人设到: **{target}**（立即生效，无需重启）")
            else:
                yield event.plain_result("❌ 切换人设失败")

    @filter.command("人设信息")
    async def cmd_persona_info(self, event: AstrMessageEvent):
        """查看人设详情：/人设信息 <ID>（可多个，用空格分隔）"""
        msg = re.sub(r'\[MSG_ID:\d+\]', '', event.message_str).strip()
        parts = msg.split()
        if len(parts) < 2:
            yield event.plain_result("用法: /人设信息 <人设ID> [人设ID...]（/人设 可查看列表）")
            return

        targets = parts[1:]
        personas = await self._get_personas()
        if not personas:
            yield event.plain_result("没有人设")
            return

        # 权限过滤
        visible = self._visible_personas(event, personas)
        visible_ids = [p.persona_id for p in visible]

        lines = []
        for t in targets:
            p = next((x for x in personas if x.persona_id == t), None)
            if not p:
                lines.append(f"❌ 人设 '{t}' 不存在")
                continue
            if not event.is_admin() and self.config.get("restrict_non_admin", False) and t not in visible_ids:
                lines.append(f"🔒 人设 '{t}'：你没有权限查看")
                continue
            prompt = getattr(p, "system_prompt", "") or "(无)"
            lines.append(f"📋 **{t}**\n{prompt}\n")

        yield event.plain_result("\n".join(lines) if lines else "未找到人设")
