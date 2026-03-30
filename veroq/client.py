import json
import os

import requests

from .exceptions import APIError, AuthenticationError, NotFoundError, VeroqError, RateLimitError


def _read_credentials():
    """Read API key from VEROQ_API_KEY or POLARIS_API_KEY env var, or ~/.veroq/credentials or ~/.polaris/credentials."""
    # Check VEROQ first, fall back to POLARIS for backwards compatibility
    key = os.environ.get("VEROQ_API_KEY") or os.environ.get("POLARIS_API_KEY")
    if key:
        return key
    # Try ~/.veroq/credentials first, then ~/.polaris/credentials
    for cred_path in ["~/.veroq/credentials", "~/.polaris/credentials"]:
        try:
            with open(os.path.expanduser(cred_path), "r") as f:
                key = f.read().strip()
                if key:
                    return key
        except (OSError, IOError):
            continue
    return None

from .types import (
    Brief,
    ClustersResponse,
    ComparisonResponse,
    DataResponse,
    EntitiesResponse,
    ExtractResponse,
    FeedResponse,
    ResearchResponse,
    SearchResponse,
    _parse_brief,
    _parse_cluster,
    _parse_data_point,
    _parse_depth_metadata,
    _parse_entity,
    _parse_extract_result,
    _parse_research_response,
    _parse_verify_response,
    _parse_source_analysis,
)


class VeroqClient:
    """Client for the VEROQ API — verified intelligence for AI agents."""

    DEFAULT_BASE_URL = "https://api.thepolarisreport.com"

    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or _read_credentials()
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._session = requests.Session()
        if self.api_key:
            self._session.headers["Authorization"] = "Bearer {}".format(self.api_key)

    def _request(self, method, path, params=None, json_body=None):
        url = "{}{}".format(self.base_url, path)
        resp = self._session.request(method, url, params=params, json=json_body)
        if resp.status_code >= 400:
            self._raise_error(resp)
        return resp.json()

    def _raise_error(self, resp):
        try:
            body = resp.json()
        except Exception:
            body = resp.text

        msg = body.get("error", resp.text) if isinstance(body, dict) else resp.text

        if resp.status_code == 401:
            raise AuthenticationError(msg, status_code=401, response_body=body)
        elif resp.status_code == 404:
            raise NotFoundError(msg, status_code=404, response_body=body)
        elif resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After") or resp.headers.get("RateLimit-Reset")
            if retry_after is not None:
                try:
                    retry_after = int(retry_after)
                except (ValueError, TypeError):
                    pass
            raise RateLimitError(msg, status_code=429, response_body=body, retry_after=retry_after)
        else:
            raise APIError(msg, status_code=resp.status_code, response_body=body)

    # -- Hero Methods: Ask & Verify --

    def ask(self, question, context=None):
        """Ask any financial question. Routes to 40+ endpoints automatically.

            result = client.ask("How is NVDA doing?")
            print(result["summary"])
            print(result["trade_signal"])
        """
        body = {"question": question}
        if context:
            body["context"] = context
        return self._request("POST", "/api/v1/ask", json_body=body)

    def ask_stream(self, question):
        """Stream financial intelligence via SSE. Yields events as they arrive.

            for event in client.ask_stream("How is NVDA doing?"):
                print(event["type"], event.get("data", {}).get("key", ""))
        """
        import json as _json
        resp = self._session.get(
            f"{self.base_url}/api/v1/ask/stream",
            params={"question": question},
            stream=True,
            timeout=30,
        )
        resp.raise_for_status()
        current_event = ""
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("event: "):
                current_event = line[7:]
            elif line.startswith("data: "):
                raw = line[6:]
                try:
                    data = _json.loads(raw)
                    yield {"type": current_event or data.get("type", ""), "data": data}
                except _json.JSONDecodeError:
                    pass
                current_event = ""

    def verify(self, claim, context=None):
        """Fact-check a claim against the intelligence corpus. Costs 3 API credits."""
        body = {"claim": claim}
        if context is not None:
            body["context"] = context
        data = self._request("POST", "/api/v1/verify", json_body=body)
        return _parse_verify_response(data)

    # -- Feed & Search --

    def feed(self, category=None, limit=None, page=None, per_page=None, min_confidence=None,
             include_sources=None, exclude_sources=None):
        """Get the news feed."""
        params = {}
        if category is not None:
            params["category"] = category
        if limit is not None:
            params["per_page"] = limit
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if min_confidence is not None:
            params["min_confidence"] = min_confidence
        if include_sources is not None:
            params["include_sources"] = include_sources
        if exclude_sources is not None:
            params["exclude_sources"] = exclude_sources
        data = self._request("GET", "/api/v1/feed", params=params)
        meta = data.get("meta", {})
        return FeedResponse(
            briefs=[_parse_brief(b) for b in data.get("briefs", [])],
            total=meta.get("total", data.get("total", 0)),
            page=meta.get("page", data.get("page", 1)),
            per_page=meta.get("per_page", data.get("per_page", 20)),
            generated_at=data.get("generated_at"),
            agent_version=data.get("agent_version"),
            sources_scanned_24h=meta.get("sources_scanned_24h", data.get("sources_scanned_24h")),
        )

    def brief(self, brief_id, include_full_text=None):
        """Get a single brief by ID."""
        params = {}
        if include_full_text is not None:
            params["include_full_text"] = str(include_full_text).lower()
        data = self._request("GET", "/api/v1/brief/{}".format(brief_id), params=params)
        return _parse_brief(data.get("brief", data))

    def timeline(self, brief_id: str) -> dict:
        """Get the story evolution timeline for a living brief."""
        return self._request("GET", "/api/v1/brief/{}/timeline".format(brief_id))

    def search(self, query, category=None, page=None, per_page=None, sort=None,
               min_confidence=None, from_date=None, to_date=None, entity=None, sentiment=None,
               depth=None, include_sources=None, exclude_sources=None):
        """Search briefs."""
        params = {"q": query}
        if category is not None:
            params["category"] = category
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if sort is not None:
            params["sort"] = sort
        if min_confidence is not None:
            params["min_confidence"] = min_confidence
        if from_date is not None:
            params["from"] = from_date
        if to_date is not None:
            params["to"] = to_date
        if entity is not None:
            params["entity"] = entity
        if sentiment is not None:
            params["sentiment"] = sentiment
        if depth is not None:
            params["depth"] = depth
        if include_sources is not None:
            params["include_sources"] = include_sources
        if exclude_sources is not None:
            params["exclude_sources"] = exclude_sources
        data = self._request("GET", "/api/v1/search", params=params)
        return SearchResponse(
            briefs=[_parse_brief(b) for b in data.get("briefs", [])],
            total=data.get("total", 0),
            facets=data.get("facets"),
            related_queries=data.get("related_queries"),
            did_you_mean=data.get("did_you_mean"),
            took_ms=data.get("took_ms"),
            meta=data.get("meta"),
            depth_metadata=_parse_depth_metadata(data.get("depth_metadata")),
        )

    def search_suggest(self, q):
        """Get search autocomplete suggestions."""
        params = {"q": q}
        return self._request("GET", "/api/v1/search/suggest", params=params)

    def generate(self, topic, category=None):
        """Generate a brief on a given topic."""
        body = {"topic": topic}
        if category is not None:
            body["category"] = category
        data = self._request("POST", "/api/v1/generate/brief", json_body=body)
        return _parse_brief(data.get("brief", data))

    def entities(self, q=None, type=None, limit=None):
        """List entities."""
        params = {}
        if q is not None:
            params["q"] = q
        if type is not None:
            params["type"] = type
        if limit is not None:
            params["limit"] = limit
        data = self._request("GET", "/api/v1/entities", params=params)
        return EntitiesResponse(
            entities=[_parse_entity(e) for e in data.get("entities", [])],
        )

    def entity_briefs(self, name, role=None, limit=None, offset=None):
        """Get briefs for a specific entity."""
        params = {}
        if role is not None:
            params["role"] = role
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = self._request("GET", "/api/v1/entities/{}/briefs".format(name), params=params)
        return [_parse_brief(b) for b in data.get("briefs", [])]

    def trending_entities(self, limit=None):
        """Get trending entities."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        data = self._request("GET", "/api/v1/entities/trending", params=params)
        return [_parse_entity(e) for e in data.get("entities", [])]

    def similar(self, brief_id, limit=None):
        """Get similar briefs."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        data = self._request("GET", "/api/v1/similar/{}".format(brief_id), params=params)
        return [_parse_brief(b) for b in data.get("briefs", [])]

    def clusters(self, period=None, limit=None):
        """Get brief clusters."""
        params = {}
        if period is not None:
            params["period"] = period
        if limit is not None:
            params["limit"] = limit
        data = self._request("GET", "/api/v1/clusters", params=params)
        return ClustersResponse(
            clusters=[_parse_cluster(c) for c in data.get("clusters", [])],
            period=data.get("period"),
        )

    def data(self, entity=None, type=None, limit=None):
        """Get structured data points."""
        params = {}
        if entity is not None:
            params["entity"] = entity
        if type is not None:
            params["type"] = type
        if limit is not None:
            params["limit"] = limit
        data = self._request("GET", "/api/v1/data", params=params)
        return DataResponse(
            data=[_parse_data_point(d) for d in data.get("data", [])],
        )

    def agent_feed(self, category=None, tags=None, limit=None, min_confidence=None,
                   include_sources=None, exclude_sources=None):
        """Get the agent-optimized feed."""
        params = {}
        if category is not None:
            params["category"] = category
        if tags is not None:
            params["tags"] = tags
        if limit is not None:
            params["limit"] = limit
        if min_confidence is not None:
            params["min_confidence"] = min_confidence
        if include_sources is not None:
            params["include_sources"] = include_sources
        if exclude_sources is not None:
            params["exclude_sources"] = exclude_sources
        data = self._request("GET", "/api/v1/agent-feed", params=params)
        return FeedResponse(
            briefs=[_parse_brief(b) for b in data.get("briefs", [])],
            total=data.get("total", 0),
            page=data.get("page", 1),
            per_page=data.get("per_page", 20),
            generated_at=data.get("generated_at"),
            agent_version=data.get("agent_version"),
            sources_scanned_24h=data.get("sources_scanned_24h"),
        )

    def compare_sources(self, brief_id):
        """Compare sources for a brief."""
        params = {"brief_id": brief_id}
        data = self._request("GET", "/api/v1/compare/sources", params=params)
        brief_data = data.get("polaris_brief")
        return ComparisonResponse(
            topic=data.get("topic"),
            share_id=data.get("share_id"),
            polaris_brief=_parse_brief(brief_data) if brief_data else None,
            source_analyses=[_parse_source_analysis(s) for s in data.get("source_analyses", [])],
            polaris_analysis=data.get("polaris_analysis"),
            generated_at=data.get("generated_at"),
        )

    def extract(self, urls, include_metadata=True):
        """Extract clean article content from URLs."""
        body = {"urls": urls, "include_metadata": include_metadata}
        data = self._request("POST", "/api/v1/extract", json_body=body)
        return ExtractResponse(
            results=[_parse_extract_result(r) for r in data.get("results", [])],
            credits_used=data.get("credits_used", 0),
        )

    def research(self, query, max_sources=None, depth=None, category=None,
                 include_sources=None, exclude_sources=None, output_schema=None):
        """Run deep research on a topic. Requires Growth plan or above. Costs 5 API credits."""
        body = {"query": query}
        if max_sources is not None:
            body["max_sources"] = max_sources
        if depth is not None:
            body["depth"] = depth
        if category is not None:
            body["category"] = category
        if include_sources is not None:
            body["include_sources"] = include_sources
        if exclude_sources is not None:
            body["exclude_sources"] = exclude_sources
        if output_schema is not None:
            body["output_schema"] = output_schema
        data = self._request("POST", "/api/v1/research", json_body=body)
        return _parse_research_response(data)

    def trending(self, period=None, limit=None):
        """Get trending briefs."""
        params = {}
        if period is not None:
            params["period"] = period
        if limit is not None:
            params["limit"] = limit
        data = self._request("GET", "/api/v1/trending", params=params)
        return [_parse_brief(b) for b in data.get("briefs", [])]

    def forecast(self, topic, depth='standard', period='30d', timeframe='30d'):
        """Generate a forward-looking forecast for a topic."""
        body = {"topic": topic, "depth": depth, "period": period, "timeframe": timeframe}
        return self._request("POST", "/api/v1/forecast", json_body=body)

    def diff(self, brief_id, since=0):
        """Get changes to a living brief since a given timestamp."""
        params = {"since": since}
        return self._request("GET", "/api/v1/brief/{}/diff".format(brief_id), params=params)

    def contradictions(self, severity=None, category=None, limit=20):
        """Get detected contradictions across briefs."""
        params = {"limit": limit}
        if severity is not None:
            params["severity"] = severity
        if category is not None:
            params["category"] = category
        return self._request("GET", "/api/v1/contradictions", params=params)

    def events(self, type=None, subject=None, category=None, period='30d', limit=30):
        """Get structured events extracted from briefs."""
        params = {"period": period, "limit": limit}
        if type is not None:
            params["type"] = type
        if subject is not None:
            params["subject"] = subject
        if category is not None:
            params["category"] = category
        return self._request("GET", "/api/v1/events", params=params)

    def subscribe_brief(self, brief_id):
        """Subscribe to updates for a living brief."""
        return self._request("POST", "/api/v1/brief/{}/subscribe".format(brief_id), json_body={})

    def unsubscribe_brief(self, brief_id):
        """Unsubscribe from a living brief."""
        return self._request("DELETE", "/api/v1/brief/{}/subscribe".format(brief_id))

    def create_watchlist(self, name, **kwargs):
        """Create a new watchlist."""
        body = {"name": name}
        body.update(kwargs)
        return self._request("POST", "/api/v1/watchlists", json_body=body)

    def watchlists(self):
        """List all watchlists."""
        return self._request("GET", "/api/v1/watchlists")

    def add_watch_item(self, watchlist_id, type, **kwargs):
        """Add an item to a watchlist."""
        body = {"type": type}
        body.update(kwargs)
        return self._request("POST", "/api/v1/watchlists/{}/items".format(watchlist_id), json_body=body)

    def watchlist_matches(self, watchlist_id):
        """Get matched briefs for a watchlist."""
        return self._request("GET", "/api/v1/watchlists/{}/matches".format(watchlist_id))

    def create_monitor(self, type, callback_url, **kwargs):
        """Create a webhook monitor."""
        body = {"type": type, "callback_url": callback_url}
        body.update(kwargs)
        return self._request("POST", "/api/v1/monitor", json_body=body)

    def monitors(self):
        """List all monitors."""
        return self._request("GET", "/api/v1/monitors")

    def create_session(self, name='default', metadata=None):
        """Create an agent session."""
        body = {"name": name}
        if metadata is not None:
            body["metadata"] = metadata
        return self._request("POST", "/api/v1/agent/session", json_body=body)

    def sessions(self):
        """List all agent sessions."""
        return self._request("GET", "/api/v1/agent/sessions")

    def mark_read(self, session_name, brief_ids):
        """Mark briefs as read in an agent session."""
        body = {"brief_ids": brief_ids}
        return self._request("POST", "/api/v1/agent/session/{}/read".format(session_name), json_body=body)

    def agent_feed_filtered(self, session='default', limit=20, category=None):
        """Get agent feed with session filtering and read-state tracking."""
        params = {"session": session, "limit": limit}
        if category is not None:
            params["category"] = category
        return self._request("GET", "/api/v1/agent/feed", params=params)

    def web_search(self, q, limit=5, freshness=None, region=None, verify=False):
        """Web search with optional trust scoring."""
        params = {"q": q, "limit": limit}
        if freshness:
            params["freshness"] = freshness
        if region:
            params["region"] = region
        if verify:
            params["verify"] = "true"
        return self._request("GET", "/api/v1/web-search", params=params)

    def crawl(self, url, depth=1, max_pages=5, include_links=True):
        """Extract structured content from URL with optional link following."""
        return self._request("POST", "/api/v1/crawl", json_body={
            "url": url,
            "depth": depth,
            "max_pages": max_pages,
            "include_links": include_links,
        })

    def stream(self, categories=None):
        """Stream briefs via SSE. Yields Brief objects.

        Usage:
            for brief in client.stream(categories="technology,science"):
                print(brief.headline)
        """
        params = {}
        if categories is not None:
            params["categories"] = categories
        url = "{}{}".format(self.base_url, "/api/v1/stream")
        resp = self._session.get(url, params=params, stream=True, headers={"Accept": "text/event-stream"})
        if resp.status_code >= 400:
            self._raise_error(resp)
        for line in resp.iter_lines(decode_unicode=True):
            if line and line.startswith("data:"):
                payload = line[5:].strip()
                if payload and payload != "[DONE]":
                    try:
                        data = json.loads(payload)
                        yield _parse_brief(data)
                    except (json.JSONDecodeError, TypeError):
                        continue

    # -- Trading --

    def ticker_resolve(self, symbols):
        """Resolve ticker symbols to canonical entities."""
        params = {"q": symbols}
        return self._request("GET", "/api/v1/ticker/resolve", params=params)

    def ticker(self, symbol):
        """Get ticker overview for a symbol."""
        return self._request("GET", "/api/v1/ticker/{}".format(symbol))

    def ticker_prices(self, symbols, paid=False):
        """Get live prices for one or more ticker symbols."""
        params = {"symbols": ",".join(symbols)}
        if paid:
            params["paid"] = "true"
        return self._request("GET", "/api/v1/ticker/prices", params=params)

    def ticker_sentiment(self, symbol, period='7d'):
        """Get sentiment breakdown for a ticker over a period."""
        params = {"period": period}
        return self._request("GET", "/api/v1/ticker/{}/sentiment".format(symbol), params=params)

    def ticker_analysis(self, symbol):
        """Get full analysis for a ticker."""
        return self._request("GET", "/api/v1/ticker/{}/analysis".format(symbol))

    def ticker_news(self, symbol, limit=10):
        """Get recent news briefs for a ticker."""
        params = {"limit": limit}
        return self._request("GET", "/api/v1/ticker/{}/news".format(symbol), params=params)

    def ticker_history(self, symbol, days=30):
        """Get sentiment history for a ticker."""
        params = {"days": days}
        return self._request("GET", "/api/v1/ticker/{}/history".format(symbol), params=params)

    def ticker_signals(self, symbol, days=30, threshold=0.3):
        """Get trading signals for a ticker."""
        params = {"days": days, "threshold": threshold}
        return self._request("GET", "/api/v1/ticker/{}/signals".format(symbol), params=params)

    def ticker_correlations(self, symbol, days=30, limit=15):
        """Get news-sentiment correlations for a ticker."""
        params = {"days": days, "limit": limit}
        return self._request("GET", "/api/v1/ticker/{}/correlations".format(symbol), params=params)

    def ticker_score(self, symbol):
        """Get composite trading score for a ticker."""
        return self._request("GET", "/api/v1/ticker/{}/score".format(symbol))

    def sectors(self, days=7):
        """Get sector-level sentiment overview."""
        params = {"days": days}
        return self._request("GET", "/api/v1/sectors", params=params)

    def sector_tickers(self, sector, days=7, sort='sentiment'):
        """Get tickers within a sector."""
        params = {"days": days, "sort": sort}
        return self._request("GET", "/api/v1/sectors/{}/tickers".format(sector), params=params)

    def events_calendar(self, days=30, ticker=None, type=None, limit=50):
        """Get upcoming market events calendar."""
        params = {"days": days, "limit": limit}
        if ticker is not None:
            params["ticker"] = ticker
        if type is not None:
            params["type"] = type
        return self._request("GET", "/api/v1/events/calendar", params=params)

    def ipo_calendar(self, status=None):
        """Get IPO calendar, optionally filtered by status."""
        params = {}
        if status is not None:
            params["status"] = status
        return self._request("GET", "/api/v1/ipo/calendar", params=params or None)

    def portfolio_feed(self, holdings, days=7, limit=30):
        """Get a personalized feed for a portfolio of holdings."""
        body = {"holdings": holdings}
        params = {"days": days, "limit": limit}
        return self._request("POST", "/api/v1/portfolio/feed", params=params, json_body=body)

    # -- Market Data --

    def candles(self, symbol, interval='1d', range='6mo'):
        """Get OHLCV candle data for a ticker."""
        params = {"interval": interval, "range": range}
        return self._request("GET", "/api/v1/ticker/{}/candles".format(symbol), params=params)

    def financials(self, symbol):
        """Get financial statements for a ticker."""
        return self._request("GET", "/api/v1/ticker/{}/financials".format(symbol))

    def earnings(self, symbol):
        """Get earnings data for a ticker."""
        return self._request("GET", "/api/v1/ticker/{}/earnings".format(symbol))

    def indicators(self, symbol, type, period=None, range='6mo'):
        """Get technical indicators for a ticker."""
        params = {"type": type, "range": range}
        if period is not None:
            params["period"] = period
        return self._request("GET", "/api/v1/ticker/{}/indicators".format(symbol), params=params)

    def technicals(self, symbol, range='6mo'):
        """Get full technical analysis for a ticker."""
        params = {"range": range}
        return self._request("GET", "/api/v1/ticker/{}/technicals".format(symbol), params=params)

    def market_movers(self):
        """Get top market movers (gainers, losers, most active)."""
        return self._request("GET", "/api/v1/market/movers")

    def market_summary(self):
        """Get broad market summary (indices, sectors, volatility)."""
        return self._request("GET", "/api/v1/market/summary")

    def market_earnings(self, days=14, sector=None):
        """Get upcoming earnings calendar."""
        params = {"days": days}
        if sector is not None:
            params["sector"] = sector
        return self._request("GET", "/api/v1/market/earnings", params=params)

    def forex(self, pair=None):
        """Get forex data. If pair is given, get that pair; otherwise list all."""
        if pair is not None:
            return self._request("GET", "/api/v1/forex/{}".format(pair))
        return self._request("GET", "/api/v1/forex")

    def forex_candles(self, pair, interval='1d', range='3mo'):
        """Get OHLCV candle data for a forex pair."""
        params = {"interval": interval, "range": range}
        return self._request("GET", "/api/v1/forex/{}/candles".format(pair), params=params)

    def commodities(self, symbol=None):
        """Get commodities data. If symbol is given, get that commodity; otherwise list all."""
        if symbol is not None:
            return self._request("GET", "/api/v1/commodities/{}".format(symbol))
        return self._request("GET", "/api/v1/commodities")

    def commodity_candles(self, symbol, interval='1d', range='3mo'):
        """Get OHLCV candle data for a commodity."""
        params = {"interval": interval, "range": range}
        return self._request("GET", "/api/v1/commodities/{}/candles".format(symbol), params=params)

    def economy(self, indicator=None, limit=None):
        """Get economic data. If indicator is given, get that series; otherwise list all."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        if indicator is not None:
            return self._request("GET", "/api/v1/economy/{}".format(indicator), params=params or None)
        return self._request("GET", "/api/v1/economy", params=params or None)

    def economy_yields(self):
        """Get Treasury yield curve data."""
        return self._request("GET", "/api/v1/economy/yields")

    def economy_indicator(self, indicator):
        """Get data for a specific economic indicator."""
        return self._request("GET", "/api/v1/economy/{}".format(indicator))

    # -- Crypto --

    def crypto(self, symbol=None):
        """Get crypto data. If symbol is given, get that coin; otherwise list all."""
        if symbol is not None:
            return self._request("GET", "/api/v1/crypto/{}".format(symbol))
        return self._request("GET", "/api/v1/crypto")

    def crypto_top(self, limit=20):
        """Get top cryptocurrencies by market cap."""
        params = {"limit": limit}
        return self._request("GET", "/api/v1/crypto/top", params=params)

    def crypto_chart(self, symbol, days=30):
        """Get price chart data for a cryptocurrency."""
        params = {"days": days}
        return self._request("GET", "/api/v1/crypto/{}/chart".format(symbol), params=params)

    def crypto_defi(self, protocol=None):
        """Get DeFi protocol data. If protocol is given, get that one; otherwise list all."""
        if protocol is not None:
            return self._request("GET", "/api/v1/crypto/defi/{}".format(protocol))
        return self._request("GET", "/api/v1/crypto/defi")

    def defi_protocol(self, protocol):
        """Get detailed data for a specific DeFi protocol."""
        return self._request("GET", "/api/v1/crypto/defi/{}".format(protocol))

    # -- Screener --

    def screener(self, filters):
        """Screen stocks by filters (sentiment, sector, technicals, etc.)."""
        return self._request("POST", "/api/v1/screener", json_body=filters)

    def screener_natural(self, query, limit=None):
        """Screen stocks using natural language query."""
        body = {"query": query}
        if limit is not None:
            body["limit"] = limit
        return self._request("POST", "/api/v1/screener/natural", json_body=body)

    def screener_presets(self):
        """List available screener presets."""
        return self._request("GET", "/api/v1/screener/presets")

    def screener_preset(self, preset_id, **kwargs):
        """Run a screener preset by ID."""
        params = {}
        params.update(kwargs)
        return self._request("GET", "/api/v1/screener/presets/{}".format(preset_id), params=params or None)

    # -- Alerts --

    def create_alert(self, ticker, alert_type, threshold, callback_url=None):
        """Create a price/sentiment alert for a ticker."""
        body = {"ticker": ticker, "alert_type": alert_type, "threshold": threshold}
        if callback_url is not None:
            body["callback_url"] = callback_url
        return self._request("POST", "/api/v1/alerts", json_body=body)

    def list_alerts(self, status=None):
        """List all alerts, optionally filtered by status."""
        params = {}
        if status is not None:
            params["status"] = status
        return self._request("GET", "/api/v1/alerts", params=params or None)

    def delete_alert(self, alert_id):
        """Delete an alert by ID."""
        return self._request("DELETE", "/api/v1/alerts/{}".format(alert_id))

    def triggered_alerts(self, since=None, limit=None):
        """Get recently triggered alerts."""
        params = {}
        if since is not None:
            params["since"] = since
        if limit is not None:
            params["limit"] = limit
        return self._request("GET", "/api/v1/alerts/triggered", params=params or None)

    # -- Backtest --

    def backtest(self, strategy, period='1y', **kwargs):
        """Backtest a news-driven trading strategy."""
        body = {"strategy": strategy, "period": period}
        body.update(kwargs)
        return self._request("POST", "/api/v1/backtest", json_body=body)

    # -- Cross-Ticker Correlation --

    def correlation(self, tickers, days=30):
        """Get correlation matrix for multiple tickers."""
        body = {"tickers": tickers, "days": days}
        return self._request("POST", "/api/v1/correlation", json_body=body)

    # -- Ticker Intelligence --

    def news_impact(self, symbol):
        """Get news impact analysis for a ticker."""
        return self._request("GET", "/api/v1/ticker/{}/impact".format(symbol))

    def competitors(self, symbol):
        """Get competitor landscape for a ticker."""
        return self._request("GET", "/api/v1/ticker/{}/competitors".format(symbol))

    def transcripts(self, symbol, days=None):
        """Get earnings call transcripts for a ticker."""
        params = {}
        if days is not None:
            params["days"] = days
        return self._request("GET", "/api/v1/ticker/{}/transcripts".format(symbol), params=params or None)

    # -- Social --

    def social_sentiment(self, symbol):
        """Get social media sentiment for a ticker."""
        return self._request("GET", "/api/v1/ticker/{}/social".format(symbol))

    def social_trending(self):
        """Get trending topics across social platforms."""
        return self._request("GET", "/api/v1/social/trending")

    def social_entity(self, entity):
        """Get social sentiment for a specific entity."""
        return self._request("GET", "/api/v1/social/sentiment/{}".format(entity))

    # -- Reports --

    def generate_report(self, ticker, tier='quick'):
        """Generate a report for a ticker."""
        body = {"ticker": ticker, "tier": tier}
        return self._request("POST", "/api/v1/reports/generate", json_body=body)

    def get_report(self, report_id):
        """Get a report by ID."""
        return self._request("GET", "/api/v1/reports/{}".format(report_id))

    def list_reports(self, limit=20):
        """List reports."""
        params = {"limit": limit}
        return self._request("GET", "/api/v1/reports", params=params)

    def upload_report(self, ticker, markdown, tier='cli'):
        """Upload a report."""
        body = {"ticker": ticker, "markdown": markdown, "tier": tier}
        return self._request("POST", "/api/v1/reports/upload", json_body=body)
