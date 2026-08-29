"""astrbot_plugin_persona_switch 插件测试脚本。

验证：
1. 指令注册与基本功能
2. 会话级人设设置/获取/清除
3. 全局人设模式
4. 权限控制（restrict_non_admin / allowed 列表 / 数量上限）
5. 人设列表与描述
6. 恢复默认 / 随机人设
"""
import asyncio
import json
import os
import sys
import tempfile
import types

sys.path.insert(0, "/root/.local/share/uv/tools/astrbot")

import importlib.util

spec = importlib.util.spec_from_file_location(
    "persona_switch",
    "/root/dsh_projects/astrbot_plugin_persona_switch/main.py",
)
plugin_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin_mod)

from astrbot.core.utils.shared_preferences import SharedPreferences


class MockPersona:
    def __init__(self, persona_id, system_prompt=""):
        self.persona_id = persona_id
        self.system_prompt = system_prompt


class MockPersonaManager:
    def __init__(self, personas):
        self._personas = personas

    async def get_all_personas(self):
        return self._personas


class MockContext:
    def __init__(self, personas):
        self.persona_manager = MockPersonaManager(personas)


class MockEvent:
    def __init__(self, admin=False, message_str="", umo="test:GroupMessage:1111"):
        self._admin = admin
        self.message_str = message_str
        self.unified_msg_origin = umo
        self.results = []

    def is_admin(self):
        return self._admin

    def plain_result(self, text):
        return types.SimpleNamespace(text=text)


def collect_agen(agen):
    out = []

    async def runner():
        async for item in agen:
            out.append(item)

    asyncio.get_event_loop().run_until_complete(runner())
    return out


def make_plugin(config_overrides=None):
    config = {
        "session_mode": True,
        "show_desc": True,
        "restrict_non_admin": False,
        "max_personas_for_non_admin": 0,
        "allowed_personas_for_non_admin": [],
    }
    if config_overrides:
        config.update(config_overrides)

    personas = [
        MockPersona("default", "默认人设，普通助手"),
        MockPersona("猫娘", "你是一只可爱的猫娘，喜欢撒娇"),
        MockPersona("胡桃", "你是原神中的胡桃，古灵精怪"),
        MockPersona("老师", "你是一位严谨的老师"),
    ]
    ctx = MockContext(personas)
    plugin = plugin_mod.PersonaSwitchPlugin(ctx, config)
    # 重定向会话存储到临时内存（避免写真实数据库）
    plugin._session_store = {}
    return plugin


# ---------- 测试 1: 插件初始化与指令注册 ----------
def test_init():
    plugin = make_plugin()
    assert plugin._is_session_mode() is True, "默认应开启会话级模式"
    plugin2 = make_plugin({"session_mode": False})
    assert plugin2._is_session_mode() is False, "应可关闭会话级模式"
    print("PASS 测试1: 插件初始化与模式判断")


# ---------- 测试 2: 人设列表（会话级，显示描述） ----------
def test_list_status():
    plugin = make_plugin()
    event = MockEvent(message_str="/人设")
    results = collect_agen(plugin.cmd_persona_status(event))
    assert len(results) == 1, f"应产出 1 条结果，实际 {len(results)}"
    text = results[0].text
    assert "当前人设" in text, f"应显示当前人设: {text}"
    assert "猫娘" in text, "应包含猫娘人设"
    assert "会话级" in text, "应显示会话级模式"
    assert "可爱" in text, "应显示人设描述"
    print("PASS 测试2: 人设列表显示描述与模式")


# ---------- 测试 3: 会话级人设切换（核心功能） ----------
def test_session_switch():
    plugin = make_plugin()
    # 模拟 sp 存储
    store = {}
    plugin._set_session_persona = None  # 不覆盖，用 monkeypatch
    orig = plugin._set_session_persona

    async def fake_set(umo, pid):
        store[umo] = pid
        return True

    async def fake_get(umo):
        return store.get(umo)

    plugin._set_session_persona = fake_set
    plugin._get_session_persona = fake_get

    event = MockEvent(message_str="/人设切换 猫娘", umo="groupA")
    results = collect_agen(plugin.cmd_switch_persona(event))
    assert "已切换" in results[0].text, f"切换失败: {results[0].text}"
    assert store.get("groupA") == "猫娘", "会话级存储应记录猫娘"
    # 另一个会话不受影响
    assert "groupB" not in store, "其他会话不应受影响"
    print("PASS 测试3: 会话级人设切换（A群不影响B群）")


# ---------- 测试 4: 不存在的人设 ----------
def test_switch_not_found():
    plugin = make_plugin()
    event = MockEvent(message_str="/人设切换 不存在的")
    results = collect_agen(plugin.cmd_switch_persona(event))
    assert "不存在" in results[0].text, f"应提示不存在: {results[0].text}"
    print("PASS 测试4: 切换不存在的人设给出提示")


# ---------- 测试 5: 恢复默认（会话级） ----------
def test_reset_session():
    plugin = make_plugin()
    store = {"groupA": "猫娘"}

    async def fake_set(umo, pid):
        if pid is None:
            store.pop(umo, None)
        else:
            store[umo] = pid
        return True

    async def fake_get(umo):
        return store.get(umo)

    plugin._set_session_persona = fake_set
    plugin._get_session_persona = fake_get

    event = MockEvent(message_str="/人设恢复", umo="groupA")
    results = collect_agen(plugin.cmd_reset_persona(event))
    assert "恢复" in results[0].text, f"恢复失败: {results[0].text}"
    assert "groupA" not in store, "会话级人设应被清除"
    print("PASS 测试5: 恢复默认人设（会话级清除）")


# ---------- 测试 6: 随机人设 ----------
def test_random_persona():
    plugin = make_plugin()
    store = {}

    async def fake_set(umo, pid):
        store[umo] = pid
        return True

    plugin._set_session_persona = fake_set
    plugin._get_session_persona = lambda umo: None

    # 多次随机，确保都在可用列表中
    seen = set()
    for _ in range(20):
        event = MockEvent(message_str="/人设随机", umo="groupA")
        results = collect_agen(plugin.cmd_random_persona(event))
        seen.add(store.get("groupA"))
    assert seen.issubset({"猫娘", "胡桃", "老师"}), f"随机范围错误: {seen}"
    print(f"PASS 测试6: 随机人设（覆盖 {len(seen)} 种人设）")


# ---------- 测试 7: 权限控制 - 非管理员受限 ----------
def test_permission_restrict():
    plugin = make_plugin(
        {
            "restrict_non_admin": True,
            "allowed_personas_for_non_admin": ["猫娘"],
        }
    )
    # 非管理员只能看到/切换到猫娘
    event = MockEvent(admin=False, message_str="/人设切换 胡桃")
    results = collect_agen(plugin.cmd_switch_persona(event))
    assert "没有权限" in results[0].text, f"应拒绝切换未允许的人设: {results[0].text}"

    event2 = MockEvent(admin=False, message_str="/人设切换 猫娘")
    results2 = collect_agen(plugin.cmd_switch_persona(event2))
    assert "已切换" in results2[0].text, f"应允许切换允许的人设: {results2[0].text}"
    print("PASS 测试7: 非管理员权限限制（允许列表）")


# ---------- 测试 8: 权限控制 - 数量上限 ----------
def test_permission_count():
    plugin = make_plugin(
        {
            "restrict_non_admin": True,
            "max_personas_for_non_admin": 2,
        }
    )
    event = MockEvent(admin=False, message_str="/人设列表")
    results = collect_agen(plugin.cmd_list_personas(event))
    assert "上限" in results[0].text, f"应提示数量超限: {results[0].text}"
    print("PASS 测试8: 非管理员数量上限限制")


# ---------- 测试 9: 管理员不受限制 ----------
def test_admin_no_restrict():
    plugin = make_plugin(
        {
            "restrict_non_admin": True,
            "allowed_personas_for_non_admin": ["猫娘"],
        }
    )
    event = MockEvent(admin=True, message_str="/人设切换 胡桃")
    results = collect_agen(plugin.cmd_switch_persona(event))
    assert "已切换" in results[0].text, f"管理员应可切换任何人设: {results[0].text}"
    print("PASS 测试9: 管理员不受限制")


# ---------- 测试 10: 人设详情 ----------
def test_persona_info():
    plugin = make_plugin()
    event = MockEvent(message_str="/人设信息 猫娘 胡桃")
    results = collect_agen(plugin.cmd_persona_info(event))
    text = results[0].text
    assert "猫娘" in text and "胡桃" in text, f"应显示两人设详情: {text[:100]}"
    assert "可爱" in text or "古灵精怪" in text, "应显示 system_prompt"
    print("PASS 测试10: 人设详情查看")


# ---------- 测试 11: 全局模式只改人设字段，不覆盖其他配置（高危修复） ----------
def test_global_update_preserves_config():
    # 模拟真实 AstrBot 配置（含 provider_settings 里的模型/密钥等）
    real_config = {
        "provider_settings": {
            "default_provider_id": "MiMo/mimo-v2.5",
            "default_personality": "default",
            "api_key": "sk-secret-key",
        },
        "platform": [{"id": "default", "type": "aiocqhttp", "enable": True}],
    }

    # 模拟 AstrBotConfig 的 save_config（写盘后从磁盘回读）
    import copy as _copy

    class FakeAstrBotConfig(dict):
        def save_config(self, replace_config=None):
            if replace_config:
                self.update(replace_config)
            saved["disk"] = _copy.deepcopy(dict(self))

    cfg_obj = FakeAstrBotConfig(real_config)
    saved = {}

    class MockCtx:
        def get_config(self):
            return cfg_obj

    class MockEvent2:
        def __init__(self):
            self.unified_msg_origin = "test:GroupMessage:1111"

        def plain_result(self, text):
            return types.SimpleNamespace(text=text)

    plugin = plugin_mod.PersonaSwitchPlugin(MockCtx(), {"session_mode": False})

    # 模拟全局切换：config 传完整配置但只改 default_personality
    config = dict(real_config)
    config.setdefault("provider_settings", {})["default_personality"] = "猫娘"

    ok = asyncio.get_event_loop().run_until_complete(plugin._update_config(config))
    assert ok, "更新应成功"
    # 验证：其他配置未被覆盖
    assert cfg_obj["provider_settings"]["default_provider_id"] == "MiMo/mimo-v2.5", "不应覆盖默认模型"
    assert cfg_obj["provider_settings"]["api_key"] == "sk-secret-key", "不应覆盖密钥"
    assert cfg_obj["provider_settings"]["default_personality"] == "猫娘", "应更新人设"
    # 验证已写盘
    assert saved["disk"]["provider_settings"]["default_personality"] == "猫娘", "应已写盘"
    print("PASS 测试11: 全局模式只改人设字段，不覆盖模型/密钥等配置（高危修复）")


if __name__ == "__main__":
    test_init()
    test_list_status()
    test_session_switch()
    test_switch_not_found()
    test_reset_session()
    test_random_persona()
    test_permission_restrict()
    test_permission_count()
    test_admin_no_restrict()
    test_persona_info()
    test_global_update_preserves_config()
    print("\n✅ 全部 11 项测试通过")
