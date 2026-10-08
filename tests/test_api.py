from __future__ import annotations

import io
import time

from fastapi.testclient import TestClient


def wait_for_task(client: TestClient, task_id: int, timeout: float = 15.0) -> dict:
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        response = client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        last = response.json()
        if last["task_status"] in {"success", "failed", "cancelled"}:
            return last
        time.sleep(0.1)
    raise AssertionError(f"任务未在超时时间内完成: {last}")


def test_chat_attachment_history_and_delete(analyst_client: TestClient) -> None:
    created = analyst_client.post("/api/chat/create", json={"title": "附件测试"}).json()
    conversation_id = created["conversation_id"]

    upload = analyst_client.post(
        "/api/attachment/upload",
        data={"conversation_id": str(conversation_id)},
        files={"file": ("notes.txt", io.BytesIO("曝光下降，重点检查类目属性".encode()), "text/plain")},
    )
    assert upload.status_code == 200
    attachment = upload.json()
    assert attachment["parse_status"] == "parsed"

    listed = analyst_client.get(
        "/api/attachment/ls",
        params={"conversation_id": conversation_id},
    ).json()
    assert len(listed) == 1

    download = analyst_client.get(
        "/api/attachment/get",
        params={"attachment_id": attachment["attachment_id"]},
    )
    assert download.status_code == 200
    assert "曝光下降" in download.content.decode("utf-8")

    sent = analyst_client.post(
        "/api/chat/send",
        json={
            "conversation_id": conversation_id,
            "content": "请分析商品目录问题",
            "attachment_ids": [attachment["attachment_id"]],
            "scenario": "auto",
        },
    )
    assert sent.status_code == 200
    task = wait_for_task(analyst_client, sent.json()["task_id"])
    assert task["task_status"] == "success"

    messages = analyst_client.get(f"/api/chat/ls/{conversation_id}").json()
    assert messages[0]["attachments"][0]["file_name"] == "notes.txt"
    assert messages[1]["message_type"] == "result"

    deleted = analyst_client.post(
        "/api/chat/delete",
        json={"conversation_ids": [conversation_id]},
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted_count"] == 1
    assert analyst_client.get(f"/api/chat/ls/{conversation_id}").status_code == 404


def test_catalog_analysis_result_and_export(analyst_client: TestClient) -> None:
    conversation_id = analyst_client.post(
        "/api/chat/create", json={"title": "商品目录分析"}
    ).json()["conversation_id"]
    response = analyst_client.post(
        "/api/chat/send",
        json={
            "conversation_id": conversation_id,
            "content": "请分析最近30天商品目录曝光、点击和转化问题",
            "attachment_ids": [],
            "scenario": "auto",
        },
    )
    task_id = response.json()["task_id"]
    assert wait_for_task(analyst_client, task_id)["task_status"] == "success"
    result = analyst_client.get(f"/api/results/{task_id}")
    assert result.status_code == 200
    payload = result.json()
    assert "商品目录" in payload["problem_definition"]
    assert len(payload["key_metrics"]) >= 5
    assert len(payload["evidence_list"]) >= 3
    assert "下一步建议" in payload["result_markdown"]
    assert len([line for line in payload["next_action_text"].splitlines() if line.strip()]) >= 2
    download = analyst_client.get(f"/api/results/{task_id}/download")
    assert download.status_code == 200
    assert "经营归因分析报告" in download.content.decode("utf-8")


def test_customer_analysis_result(analyst_client: TestClient) -> None:
    conversation_id = analyst_client.post(
        "/api/chat/create", json={"title": "客户漏斗分析"}
    ).json()["conversation_id"]
    response = analyst_client.post(
        "/api/chat/send",
        json={
            "conversation_id": conversation_id,
            "content": "请分析客户行为漏斗，定位访问到加购、加购到下单的主要流失环节",
            "attachment_ids": [],
            "scenario": "auto",
        },
    )
    task_id = response.json()["task_id"]
    assert wait_for_task(analyst_client, task_id)["task_status"] == "success"
    payload = analyst_client.get(f"/api/results/{task_id}").json()
    assert "访问到加购率" in " ".join(item["metric_name"] for item in payload["key_metrics"])
    assert "加购到下单率" in " ".join(item["metric_name"] for item in payload["key_metrics"])
    assert "社交/北京" in payload["conclusion_text"] or "自然流量/上海" in payload["conclusion_text"]


def test_websocket_token_and_ping(analyst_client: TestClient) -> None:
    conversation_id = analyst_client.post(
        "/api/chat/create", json={"title": "WebSocket 测试"}
    ).json()["conversation_id"]
    token_response = analyst_client.post(
        "/api/chat/ws-token",
        params={"conversation_id": conversation_id},
    )
    assert token_response.status_code == 200
    token = token_response.json()["websocket_token"]
    with analyst_client.websocket_connect(
        f"/api/chat/ws/chat?websocket_token={token}&conversation_id={conversation_id}"
    ) as websocket:
        websocket.send_text("ping")
        event = websocket.receive_json()
        assert event["event"] == "pong"


def test_config_update_and_reload(admin_client: TestClient) -> None:
    update = admin_client.put(
        "/api/admin/configs/analysis.low_ctr_threshold",
        json={"config_value": "0.041", "config_group": "analysis"},
    )
    assert update.status_code == 200
    reload_response = admin_client.post("/api/admin/reload")
    assert reload_response.status_code == 200
    assert reload_response.json()["status"] == "ok"
    effective = admin_client.get("/api/config/effective").json()
    assert effective["low_ctr_threshold"] == 0.041


def test_authentication_required(client: TestClient) -> None:
    response = client.get("/api/chat/ls")
    assert response.status_code == 401
