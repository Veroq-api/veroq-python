import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from veroq.async_client import AsyncVeroqClient
from veroq.exceptions import AuthenticationError, RateLimitError


def _mock_response(status_code=200, json_data=None, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = str(json_data)
    resp.headers = headers or {}
    return resp


@pytest.fixture
def client():
    return AsyncVeroqClient(api_key="test-key", base_url="https://api.test.com")


@pytest.mark.asyncio
async def test_extract(client):
    mock_data = {
        "results": [
            {"url": "https://example.com/article", "title": "Test", "text": "Content here", "word_count": 2, "success": True, "domain": "example.com"}
        ],
        "credits_used": 1,
    }
    with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_data):
        result = await client.extract(["https://example.com/article"])
        assert len(result.results) == 1
        assert result.results[0].success is True
        assert result.results[0].word_count == 2
        assert result.credits_used == 1


@pytest.mark.asyncio
async def test_feed_with_include_sources(client):
    mock_data = {
        "briefs": [{"id": "1", "headline": "Reuters Story"}],
        "total": 1,
        "page": 1,
        "per_page": 20,
    }
    with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_data) as mock_req:
        result = await client.feed(include_sources="reuters.com")
        mock_req.assert_called_once_with("GET", "/api/v1/feed", params={"include_sources": "reuters.com"})
        assert len(result.briefs) == 1


@pytest.mark.asyncio
async def test_search_with_depth(client):
    mock_data = {
        "briefs": [{"id": "1", "headline": "Deep Result"}],
        "total": 1,
        "took_ms": 500,
        "depth_metadata": {"depth": "deep", "search_ms": 45, "cross_ref_ms": 120, "verification_ms": 350, "total_ms": 515},
    }
    with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_data) as mock_req:
        result = await client.search("AI", depth="deep")
        mock_req.assert_called_once_with("GET", "/api/v1/search", params={"q": "AI", "depth": "deep"})
        assert result.depth_metadata is not None
        assert result.depth_metadata.depth == "deep"
        assert result.depth_metadata.total_ms == 515


@pytest.mark.asyncio
async def test_search_with_exclude_sources(client):
    mock_data = {"briefs": [], "total": 0}
    with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_data) as mock_req:
        await client.search("AI", exclude_sources="foxnews.com")
        mock_req.assert_called_once_with("GET", "/api/v1/search", params={"q": "AI", "exclude_sources": "foxnews.com"})


@pytest.mark.asyncio
async def test_auth_error(client):
    resp = _mock_response(401, {"error": "Unauthorized"})
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=resp):
        with pytest.raises(AuthenticationError):
            await client.feed()


@pytest.mark.asyncio
async def test_rate_limit_error(client):
    resp = _mock_response(429, {"error": "Too many requests"}, headers={"Retry-After": "30"})
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=resp):
        with pytest.raises(RateLimitError) as exc_info:
            await client.feed()
        assert exc_info.value.retry_after == 30


@pytest.mark.asyncio
async def test_agent_feed_with_source_filtering(client):
    mock_data = {
        "briefs": [{"id": "1", "headline": "Filtered"}],
        "total": 1,
        "page": 1,
        "per_page": 20,
    }
    with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_data) as mock_req:
        result = await client.agent_feed(include_sources="bbc.com,reuters.com")
        mock_req.assert_called_once_with("GET", "/api/v1/agent-feed", params={"include_sources": "bbc.com,reuters.com"})
        assert result.briefs[0].headline == "Filtered"
