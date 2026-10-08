from __future__ import annotations

import asyncio
import json
from urllib.parse import parse_qs, urlparse

import httpx
import websockets


BACKEND = "http://localhost:8000"
AUTH_SERVER = "http://localhost:8001"


async def run_smoke() -> None:
    async with httpx.AsyncClient(follow_redirects=False, timeout=20) as client:
        login = await client.get(f"{BACKEND}/auth/login")
        assert login.status_code == 302, login.text
        authorize_url = login.headers["location"]

        authorize = await client.get(authorize_url)
        assert authorize.status_code == 200
        assert "同意授权并登录" in authorize.text

        approve = await client.post(
            f"{AUTH_SERVER}/oauth/approve",
            data={
                "client_id": "business-attribution-web",
                "redirect_uri": f"{BACKEND}/auth/callback",
                "state": parse_qs(urlparse(authorize_url).query)["state"][0],
                "username": "analyst",
                "password": "analyst123",
            },
        )
        assert approve.status_code == 302
        callback_url = approve.headers["location"]
        callback_query = parse_qs(urlparse(callback_url).query)

        callback = await client.get(
            f"{BACKEND}/auth/callback",
            params={"code": callback_query["code"][0], "state": callback_query["state"][0]},
        )
        assert callback.status_code == 302
        assert callback.headers["location"].endswith("/auth/callback?login=success")

        me = await client.get(f"{BACKEND}/api/auth/me")
        assert me.status_code == 200, me.text
        user = me.json()

        conversation = await client.post(
            f"{BACKEND}/api/chat/create",
            json={"title": "进程级冒烟测试"},
        )
        assert conversation.status_code == 200
        conversation_id = conversation.json()["conversation_id"]

        sent = await client.post(
            f"{BACKEND}/api/chat/send",
            json={
                "conversation_id": conversation_id,
                "content": "请分析最近30天商品目录高曝光低点击与转化问题",
                "attachment_ids": [],
                "scenario": "auto",
            },
        )
        assert sent.status_code == 200, sent.text
        task_id = sent.json()["task_id"]
        task = {}
        for _ in range(100):
            task_response = await client.get(f"{BACKEND}/api/tasks/{task_id}")
            task = task_response.json()
            if task["task_status"] in {"success", "failed", "cancelled"}:
                break
            await asyncio.sleep(0.1)
        assert task["task_status"] == "success", task

        result = await client.get(f"{BACKEND}/api/results/{task_id}")
        assert result.status_code == 200
        result_payload = result.json()
        assert len(result_payload["key_metrics"]) >= 5
        assert len(result_payload["evidence_list"]) >= 3

        ws_token_response = await client.post(
            f"{BACKEND}/api/chat/ws-token",
            params={"conversation_id": conversation_id},
        )
        ws_token = ws_token_response.json()["websocket_token"]
        ws_url = (
            f"ws://localhost:8000/api/chat/ws/chat"
            f"?websocket_token={ws_token}&conversation_id={conversation_id}"
        )
        events: list[dict] = []
        async with websockets.connect(ws_url) as websocket:
            while True:
                raw = await asyncio.wait_for(websocket.recv(), timeout=5)
                event = json.loads(raw)
                if event.get("task_id") == task_id:
                    events.append(event)
                    if event.get("event") == "done":
                        break
        event_types = {event["event"] for event in events}
        assert {"message_start", "tool_finish", "result_ready", "done"} <= event_types

        print(
            json.dumps(
                {
                    "status": "ok",
                    "user": user["username"],
                    "conversation_id": conversation_id,
                    "task_id": task_id,
                    "task_status": task["task_status"],
                    "key_metrics": len(result_payload["key_metrics"]),
                    "evidence_count": len(result_payload["evidence_list"]),
                    "websocket_events": sorted(event_types),
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    asyncio.run(run_smoke())
