"""외부 API 통합시험 client의 격리·비밀 보호 계약을 검사한다."""

import io
import json
import urllib.error

import pytest

from llm import (
    ModelCallError,
    ModelClient,
    ModelResponseError,
    OpenAICompatibleIntegrationClient,
)
from llm.openai_compatible import _RejectRedirectHandler


API_KEY_ENV = "SONGRYEON_TEST_API_KEY"
API_KEY = "integration-test-secret-value"


class FakeHTTPResponse:
    def __init__(self, payload):
        self.body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


def valid_payload():
    return {
        "model": "provider/large-model",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": (
                        '{"verdict":"permit","reason":"증거가 충분하다."}'
                    ),
                },
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
        },
    }


def make_client(opener):
    return OpenAICompatibleIntegrationClient(
        base_url="https://provider.example/v1",
        model_name="provider/large-model",
        api_key_env=API_KEY_ENV,
        opener=opener,
    )


def test_complete_uses_env_key_https_and_strict_schema(
    monkeypatch,
):
    captured = {}

    def fake_opener(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeHTTPResponse(valid_payload())

    monkeypatch.setenv(API_KEY_ENV, API_KEY)
    client = make_client(fake_opener)
    schema = {
        "type": "object",
        "properties": {"verdict": {"type": "string"}},
        "required": ["verdict"],
        "additionalProperties": False,
    }

    reply = client.complete(
        system_prompt="검사 노드다.",
        user_prompt="증거를 검사하라.",
        response_schema=schema,
        num_predict=256,
    )

    request = captured["request"]
    sent = json.loads(request.data.decode("utf-8"))
    assert request.full_url == (
        "https://provider.example/v1/chat/completions"
    )
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == f"Bearer {API_KEY}"
    assert captured["timeout"] == 180
    assert sent == {
        "model": "provider/large-model",
        "messages": [
            {"role": "system", "content": "검사 노드다."},
            {"role": "user", "content": "증거를 검사하라."},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "songryeon_node_output",
                "strict": True,
                "schema": schema,
            },
        },
        "stream": False,
        "temperature": 0,
        "seed": 42,
        "max_tokens": 256,
    }
    assert reply.content == (
        '{"verdict":"permit","reason":"증거가 충분하다."}'
    )
    assert reply.thinking == ""
    assert reply.model == "provider/large-model"
    assert reply.done_reason == "stop"
    assert reply.metrics == {
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "total_tokens": 120,
    }
    assert client.provider == "openai_compatible"
    assert client.execution_mode == "external_api_integration"
    assert isinstance(client, ModelClient)


@pytest.mark.parametrize(
    "base_url",
    [
        "http://provider.example/v1",
        "https://user:password@provider.example/v1",
        "https://provider.example/v1?api_key=secret",
        "https://provider.example/v1#fragment",
    ],
)
def test_base_url_rejects_insecure_or_secret_bearing_forms(base_url):
    with pytest.raises(ValueError):
        OpenAICompatibleIntegrationClient(
            base_url=base_url,
            model_name="provider/large-model",
            api_key_env=API_KEY_ENV,
        )


def test_missing_key_fails_before_http(monkeypatch):
    called = False

    def fake_opener(request, timeout):
        nonlocal called
        called = True
        return FakeHTTPResponse(valid_payload())

    monkeypatch.delenv(API_KEY_ENV, raising=False)
    client = make_client(fake_opener)

    with pytest.raises(ModelCallError, match=API_KEY_ENV):
        client.check_configuration()

    assert called is False


def test_repr_and_http_error_do_not_expose_key_or_body(monkeypatch):
    secret_body = b"provider body with TOP_SECRET_RESPONSE"

    def fake_opener(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            401,
            "unauthorized",
            {},
            io.BytesIO(secret_body),
        )

    monkeypatch.setenv(API_KEY_ENV, API_KEY)
    client = make_client(fake_opener)

    with pytest.raises(ModelCallError) as captured:
        client.complete(
            system_prompt="system",
            user_prompt="user",
            response_schema={"type": "object"},
            num_predict=64,
        )

    exposed = repr(client) + str(captured.value) + repr(captured.value)
    assert API_KEY not in exposed
    assert "TOP_SECRET_RESPONSE" not in exposed
    assert captured.value.__cause__ is None


def test_redirect_handler_refuses_redirect_request():
    handler = _RejectRedirectHandler()

    redirected = handler.redirect_request(
        object(),
        None,
        307,
        "Temporary Redirect",
        {},
        "https://different-provider.example/v1/chat/completions",
    )

    assert redirected is None


def test_response_must_report_requested_model(monkeypatch):
    payload = valid_payload()
    payload["model"] = "different/model"
    monkeypatch.setenv(API_KEY_ENV, API_KEY)
    client = make_client(
        lambda request, timeout: FakeHTTPResponse(payload)
    )

    with pytest.raises(ModelResponseError, match="다른 모델 이름"):
        client.complete(
            system_prompt="system",
            user_prompt="user",
            response_schema={"type": "object"},
            num_predict=64,
        )
