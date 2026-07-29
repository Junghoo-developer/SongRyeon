"""실제 Ollama를 호출하지 않는 HTTP transport 단위 테스트."""

import json
import urllib.error

import pytest

from llm import (
    ModelCallError,
    ModelClient,
    ModelConnectionError,
    ModelResponseError,
    OllamaClient,
)


class FakeHTTPResponse:
    """urlopen의 context manager 동작만 흉내 낸다."""

    def __init__(self, payload):
        self.body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


def valid_chat_payload():
    return {
        "model": "gemma4:26b",
        "message": {
            "role": "assistant",
            "content": '{"verdict":"permit","reason":"충분함"}',
        },
        "done": True,
        "done_reason": "stop",
        "total_duration": 100,
        "load_duration": 20,
        "prompt_eval_count": 30,
        "eval_count": 12,
    }


def test_complete_sends_deterministic_nonstream_json_schema_request(
    monkeypatch,
):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeHTTPResponse(valid_chat_payload())

    monkeypatch.setattr("llm.client.urllib.request.urlopen", fake_urlopen)

    schema = {
        "type": "object",
        "properties": {"verdict": {"type": "string"}},
        "required": ["verdict"],
    }
    client = OllamaClient()
    reply = client.complete(
        system_prompt="검토 노드다.",
        user_prompt="입력을 검토하라.",
        response_schema=schema,
        num_predict=256,
    )

    request = captured["request"]
    sent = json.loads(request.data.decode("utf-8"))

    assert request.full_url == "http://127.0.0.1:11434/api/chat"
    assert request.get_method() == "POST"
    assert captured["timeout"] == 180
    assert sent == {
        "model": "gemma4:26b",
        "messages": [
            {"role": "system", "content": "검토 노드다."},
            {"role": "user", "content": "입력을 검토하라."},
        ],
        "format": schema,
        "stream": False,
        "think": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "seed": 42,
            "num_ctx": 16_384,
            "num_predict": 256,
        },
    }
    assert reply.content == '{"verdict":"permit","reason":"충분함"}'
    assert reply.thinking == ""
    assert reply.model == "gemma4:26b"
    assert reply.done_reason == "stop"
    assert reply.metrics == {
        "total_duration": 100,
        "load_duration": 20,
        "prompt_eval_count": 30,
        "eval_count": 12,
    }
    assert isinstance(client, ModelClient)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"done": False}, "완료 상태"),
        ({"done_reason": "length"}, "잘렸습니다"),
        ({"model": "other:latest"}, "다른 모델"),
        ({"message": []}, "message 객체"),
        (
            {
                "message": {
                    "role": "assistant",
                    "content": "JSON 아님",
                }
            },
            "유효한 JSON",
        ),
        ({"eval_count": -1}, "eval_count"),
    ],
)
def test_complete_rejects_invalid_nonstream_response(
    monkeypatch,
    change,
    message,
):
    payload = valid_chat_payload()
    payload.update(change)
    monkeypatch.setattr(
        "llm.client.urllib.request.urlopen",
        lambda request, timeout: FakeHTTPResponse(payload),
    )

    with pytest.raises(ModelResponseError, match=message):
        OllamaClient().complete(
            system_prompt="system",
            user_prompt="user",
            response_schema={"type": "object"},
            num_predict=128,
        )


def test_complete_converts_network_failure(monkeypatch):
    def fail_urlopen(request, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(
        "llm.client.urllib.request.urlopen",
        fail_urlopen,
    )

    with pytest.raises(ModelConnectionError):
        OllamaClient().complete(
            system_prompt="system",
            user_prompt="user",
            response_schema={"type": "object"},
            num_predict=128,
        )


def test_complete_converts_http_failure_without_echoing_request(
    monkeypatch,
):
    def fail_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            500,
            "server error",
            {},
            None,
        )

    monkeypatch.setattr(
        "llm.client.urllib.request.urlopen",
        fail_urlopen,
    )

    secret_prompt = "MODEL_INPUT_SHOULD_NOT_APPEAR"
    with pytest.raises(ModelCallError) as captured:
        OllamaClient().complete(
            system_prompt="system",
            user_prompt=secret_prompt,
            response_schema={"type": "object"},
            num_predict=128,
        )
    assert secret_prompt not in str(captured.value)


def test_check_ready_reads_version_and_confirms_installed_model(
    monkeypatch,
):
    requested_urls = []
    replies = iter(
        [
            {"version": "0.32.4"},
            {
                "models": [
                    {"name": "gemma3:12b"},
                    {
                        "name": "gemma4:26b",
                        "digest": "A" * 64,
                    },
                ]
            },
        ]
    )

    def fake_urlopen(request, timeout):
        requested_urls.append(request.full_url)
        assert request.get_method() == "GET"
        return FakeHTTPResponse(next(replies))

    monkeypatch.setattr("llm.client.urllib.request.urlopen", fake_urlopen)

    status = OllamaClient().check_ready()

    assert status == {
        "server_version": "0.32.4",
        "model_name": "gemma4:26b",
        "model_digest": "a" * 64,
    }
    assert requested_urls == [
        "http://127.0.0.1:11434/api/version",
        "http://127.0.0.1:11434/api/tags",
    ]


def test_check_ready_rejects_missing_model(monkeypatch):
    replies = iter(
        [
            {"version": "0.32.4"},
            {"models": [{"name": "gemma3:12b"}]},
        ]
    )
    monkeypatch.setattr(
        "llm.client.urllib.request.urlopen",
        lambda request, timeout: FakeHTTPResponse(next(replies)),
    )

    with pytest.raises(ModelResponseError, match="대상 Ollama 서버에 설치되어 있지"):
        OllamaClient().check_ready()


@pytest.mark.parametrize("digest", [None, "", "abc", "z" * 64])
def test_check_ready_rejects_invalid_selected_model_digest(
    monkeypatch,
    digest,
):
    replies = iter(
        [
            {"version": "0.32.4"},
            {
                "models": [
                    {
                        "name": "gemma4:26b",
                        "digest": digest,
                    }
                ]
            },
        ]
    )
    monkeypatch.setattr(
        "llm.client.urllib.request.urlopen",
        lambda request, timeout: FakeHTTPResponse(next(replies)),
    )

    with pytest.raises(ModelResponseError, match="SHA-256 digest"):
        OllamaClient().check_ready()


def test_complete_rejects_invalid_input_without_http_call(monkeypatch):
    called = False

    def fake_urlopen(request, timeout):
        nonlocal called
        called = True
        return FakeHTTPResponse(valid_chat_payload())

    monkeypatch.setattr("llm.client.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(ValueError, match="num_predict"):
        OllamaClient().complete(
            system_prompt="system",
            user_prompt="user",
            response_schema={"type": "object"},
            num_predict=0,
        )
    assert called is False
