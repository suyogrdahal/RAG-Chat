import asyncio
import httpx

from app.llm.wrapper import FALLBACK_ANSWER, generate_llm_response


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, response=None, exc=None, timeout=None):
        self._response = response
        self._exc = exc
        self.timeout = timeout
        self.called = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        self.called = True
        if self._exc is not None:
            raise self._exc
        return self._response


def test_successful_response_returns_expected_dict(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_client = _FakeClient(
        response=_FakeResponse(
            {
                "choices": [{"message": {"content": "Hello from model"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
        )
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=None: fake_client)

    result = asyncio.run(generate_llm_response("test prompt"))
    assert result == {
        "answer": "Hello from model",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    assert fake_client.called is True


def test_api_failure_handled_gracefully(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_client = _FakeClient(response=_FakeResponse({}, status_code=500))
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=None: fake_client)

    result = asyncio.run(generate_llm_response("test prompt"))
    assert result == {"answer": FALLBACK_ANSWER, "usage": {}}


def test_timeout_handled(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_client = _FakeClient(exc=httpx.TimeoutException("timeout"))
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=None: fake_client)

    result = asyncio.run(generate_llm_response("test prompt"))
    assert result == {"answer": FALLBACK_ANSWER, "usage": {}}


def test_no_real_external_api_call(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    calls = {"count": 0}

    class _NoNetworkClient(_FakeClient):
        async def post(self, *args, **kwargs):
            calls["count"] += 1
            return _FakeResponse({"choices": [{"message": {"content": "ok"}}], "usage": {}})

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=None: _NoNetworkClient())
    result = asyncio.run(generate_llm_response("prompt"))
    assert result["answer"] == "ok"
    assert calls["count"] == 1
