import unittest
from unittest.mock import MagicMock, patch

from veroq import VeroqClient
from veroq.exceptions import AuthenticationError, NotFoundError, RateLimitError


def _mock_response(status_code=200, json_data=None, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = str(json_data)
    resp.headers = headers or {}
    return resp


class TestVeroqClient(unittest.TestCase):
    def setUp(self):
        self.client = VeroqClient(api_key="test-key", base_url="https://api.test.com")

    @patch.object(VeroqClient, "_request")
    def test_feed(self, mock_req):
        mock_req.return_value = {
            "briefs": [
                {"id": "1", "headline": "Test Brief", "category": "tech"}
            ],
            "total": 1,
            "page": 1,
            "per_page": 20,
            "generated_at": "2026-01-01T00:00:00Z",
        }
        result = self.client.feed(category="tech", limit=5)
        mock_req.assert_called_once_with("GET", "/api/v1/feed", params={"category": "tech", "per_page": 5})
        self.assertEqual(len(result.briefs), 1)
        self.assertEqual(result.briefs[0].headline, "Test Brief")
        self.assertEqual(result.total, 1)

    @patch.object(VeroqClient, "_request")
    def test_brief(self, mock_req):
        mock_req.return_value = {
            "brief": {
                "id": "abc",
                "headline": "Deep Dive",
                "summary": "A summary",
                "confidence": 0.95,
                "sources": [{"name": "Reuters", "url": "https://reuters.com", "verified": True}],
            }
        }
        result = self.client.brief("abc", include_full_text=True)
        mock_req.assert_called_once_with("GET", "/api/v1/brief/abc", params={"include_full_text": "true"})
        self.assertEqual(result.headline, "Deep Dive")
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(len(result.sources), 1)
        self.assertEqual(result.sources[0].name, "Reuters")

    @patch.object(VeroqClient, "_request")
    def test_search(self, mock_req):
        mock_req.return_value = {
            "briefs": [{"id": "s1", "headline": "Search Result"}],
            "total": 42,
            "took_ms": 15,
        }
        result = self.client.search("AI regulation", category="policy", per_page=10)
        mock_req.assert_called_once_with(
            "GET", "/api/v1/search",
            params={"q": "AI regulation", "category": "policy", "per_page": 10},
        )
        self.assertEqual(result.total, 42)
        self.assertEqual(result.took_ms, 15)
        self.assertEqual(result.briefs[0].headline, "Search Result")

    @patch.object(VeroqClient, "_request")
    def test_generate(self, mock_req):
        mock_req.return_value = {
            "brief": {"id": "gen1", "headline": "Generated Brief", "category": "tech"}
        }
        result = self.client.generate("quantum computing", category="tech")
        mock_req.assert_called_once_with(
            "POST", "/api/v1/generate/brief",
            json_body={"topic": "quantum computing", "category": "tech"},
        )
        self.assertEqual(result.headline, "Generated Brief")

    @patch.object(VeroqClient, "_request")
    def test_entities(self, mock_req):
        mock_req.return_value = {
            "entities": [{"name": "OpenAI", "type": "organization", "mention_count": 150}]
        }
        result = self.client.entities(q="open", limit=5)
        self.assertEqual(len(result.entities), 1)
        self.assertEqual(result.entities[0].name, "OpenAI")
        self.assertEqual(result.entities[0].mention_count, 150)

    @patch.object(VeroqClient, "_request")
    def test_clusters(self, mock_req):
        mock_req.return_value = {
            "clusters": [{"cluster_id": "c1", "topic": "AI", "brief_count": 5}],
            "period": "24h",
        }
        result = self.client.clusters(period="24h")
        self.assertEqual(len(result.clusters), 1)
        self.assertEqual(result.clusters[0].topic, "AI")
        self.assertEqual(result.period, "24h")

    @patch.object(VeroqClient, "_request")
    def test_trending(self, mock_req):
        mock_req.return_value = {
            "briefs": [{"id": "t1", "headline": "Trending Story"}]
        }
        result = self.client.trending(period="24h", limit=5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].headline, "Trending Story")

    def test_auth_error(self):
        resp = _mock_response(401, {"error": "Unauthorized"})
        with patch("requests.Session.request", return_value=resp):
            with self.assertRaises(AuthenticationError) as ctx:
                self.client.feed()
            self.assertEqual(ctx.exception.status_code, 401)

    def test_not_found_error(self):
        resp = _mock_response(404, {"error": "Not found"})
        with patch("requests.Session.request", return_value=resp):
            with self.assertRaises(NotFoundError) as ctx:
                self.client.brief("nonexistent")
            self.assertEqual(ctx.exception.status_code, 404)

    def test_rate_limit_error(self):
        resp = _mock_response(429, {"error": "Too many requests"}, headers={"Retry-After": "30"})
        with patch("requests.Session.request", return_value=resp):
            with self.assertRaises(RateLimitError) as ctx:
                self.client.feed()
            self.assertEqual(ctx.exception.status_code, 429)
            self.assertEqual(ctx.exception.retry_after, 30)

    def test_auth_header_set(self):
        client = VeroqClient(api_key="my-key")
        self.assertEqual(client._session.headers["Authorization"], "Bearer my-key")

    def test_no_auth_header_when_no_key(self):
        client = VeroqClient()
        self.assertNotIn("Authorization", client._session.headers)

    def test_backwards_compat_alias(self):
        """Test that PolarisClient alias works."""
        from veroq import PolarisClient
        self.assertIs(PolarisClient, VeroqClient)


if __name__ == "__main__":
    unittest.main()
