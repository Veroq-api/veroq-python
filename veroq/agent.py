"""
VEROQ Universal Agent Connector

The simplest way to give any AI agent verified financial intelligence.

    from veroq import Agent

    agent = Agent()  # reads VEROQ_API_KEY or POLARIS_API_KEY from env
    result = agent.ask("What's happening with NVDA?")
    print(result.summary)

    # Full cross-reference — everything about a ticker
    full = agent.full("AAPL")
    print(full.price, full.technicals, full.earnings)

    # Subscribe to real-time events
    for event in agent.subscribe(tickers=["NVDA", "AAPL"], events=["brief"]):
        print(event)
"""

import json
import os
from typing import Any, Dict, Iterator, List, Optional

import requests


class AskResult:
    """Result from /ask — structured financial intelligence."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self.question: str = data.get("question", "")
        self.intents: List[str] = data.get("intents", [])
        self.tickers: List[str] = data.get("tickers", [])
        self.reasoning: List[str] = data.get("reasoning", [])
        self.summary: str = data.get("summary", "")
        self.data: Dict[str, Any] = data.get("data", {})
        self.credits_used: int = data.get("credits_used", 0)

    def __repr__(self) -> str:
        return f"AskResult(tickers={self.tickers}, intents={self.intents}, credits={self.credits_used})"

    def __str__(self) -> str:
        return self.summary


class FullResult:
    """Result from /ticker/:symbol/full — complete cross-reference."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self.ticker: str = data.get("ticker", "")
        self.entity_name: str = data.get("entity_name", "")
        self.sector: str = data.get("sector", "")
        self.price: Dict[str, Any] = data.get("price", {})
        self.sentiment: Dict[str, Any] = data.get("sentiment", {})
        self.technicals: Dict[str, Any] = data.get("technicals", {})
        self.earnings: Dict[str, Any] = data.get("earnings", {})
        self.news: Dict[str, Any] = data.get("news", {})
        self.insider: Dict[str, Any] = data.get("insider", {})
        self.filings: Dict[str, Any] = data.get("filings", {})
        self.analysts: Dict[str, Any] = data.get("analysts", {})
        self.institutions: Dict[str, Any] = data.get("institutions", {})

    def __repr__(self) -> str:
        return f"FullResult({self.ticker} ${self.price.get('current', '?')})"

    def __str__(self) -> str:
        lines = [f"{self.entity_name} ({self.ticker})"]
        if self.price.get("current"):
            lines.append(f"Price: ${self.price['current']} ({self.price.get('change_pct', '?')}%)")
        if self.technicals.get("signal"):
            lines.append(f"Signal: {self.technicals['signal']} | RSI: {self.technicals.get('rsi_14', '?')}")
        if self.earnings.get("next_date"):
            lines.append(f"Next Earnings: {self.earnings['next_date']}")
        return "\n".join(lines)


class SubscribeEvent:
    """A real-time event from /subscribe."""

    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.type: str = event_type
        self.ticker: Optional[str] = data.get("ticker")
        self.data: Dict[str, Any] = data.get("data", data)
        self.timestamp: str = data.get("timestamp", "")

    def __repr__(self) -> str:
        return f"SubscribeEvent({self.type}, ticker={self.ticker})"


class Agent:
    """
    VEROQ Universal Agent Connector.

    The simplest way to add verified financial intelligence to any AI agent.

        agent = Agent(api_key="vq_live_...")
        result = agent.ask("What's happening with NVDA?")
        print(result.summary)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.thepolarisreport.com",
        timeout: int = 30,
    ):
        # Support both VEROQ_API_KEY and POLARIS_API_KEY for backwards compatibility
        self.api_key = api_key or os.environ.get("VEROQ_API_KEY") or os.environ.get("POLARIS_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json",
            "User-Agent": "veroq-agent/1.0",
        })

    def ask(self, question: str) -> AskResult:
        """
        Ask any financial question. Returns structured data + markdown summary.

            result = agent.ask("What's happening with NVDA?")
            print(result.summary)
            print(result.tickers)       # ['NVDA']
            print(result.reasoning)     # ['Identified ticker: NVDA', ...]
            print(result.data)          # Raw data from all sources
        """
        resp = self._session.post(
            f"{self.base_url}/api/v1/ask",
            json={"question": question},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return AskResult(resp.json())

    def full(self, ticker: str) -> FullResult:
        """
        Get EVERYTHING about a ticker in one call.

            result = agent.full("NVDA")
            print(result.price)         # {'current': 178.68, 'change_pct': -0.95}
            print(result.technicals)    # {'signal': 'neutral', 'rsi_14': 46.4}
            print(result.earnings)      # {'next_date': '2026-05-20', ...}
            print(result.insider)       # {'transactions': [...], 'total': 20}
        """
        resp = self._session.get(
            f"{self.base_url}/api/v1/ticker/{ticker.upper()}/full",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return FullResult(resp.json())

    def subscribe(
        self,
        tickers: Optional[List[str]] = None,
        events: Optional[List[str]] = None,
    ) -> Iterator[SubscribeEvent]:
        """
        Subscribe to real-time financial events via SSE.

            for event in agent.subscribe(tickers=["NVDA", "AAPL"], events=["brief"]):
                print(event.type, event.ticker, event.data)
        """
        params = {}
        if tickers:
            params["tickers"] = ",".join(t.upper() for t in tickers)
        else:
            params["tickers"] = "*"
        if events:
            params["events"] = ",".join(events)

        resp = self._session.get(
            f"{self.base_url}/api/v1/subscribe",
            params=params,
            stream=True,
            timeout=None,  # SSE is long-lived
            headers={**self._session.headers, "Accept": "text/event-stream"},
        )
        resp.raise_for_status()

        event_type = ""
        data_lines: List[str] = []

        for line in resp.iter_lines(decode_unicode=True):
            if line is None:
                continue
            line = line.strip()
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
            elif line == "" and event_type and data_lines:
                # Complete event
                try:
                    data = json.loads("".join(data_lines))
                    yield SubscribeEvent(event_type, data)
                except json.JSONDecodeError:
                    pass
                event_type = ""
                data_lines = []
            elif line.startswith(":"):
                pass  # heartbeat, ignore

    def run_agent(self, slug: str, **inputs) -> Dict[str, Any]:
        """
        Run a marketplace agent.

            result = agent.run_agent("sector-pulse", sector="Technology")
            print(result["summary"])
        """
        resp = self._session.post(
            f"{self.base_url}/api/v1/agents/run/{slug}",
            json=inputs,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    def search(self, query: str, per_page: int = 10) -> Dict[str, Any]:
        """Search intelligence briefs."""
        resp = self._session.get(
            f"{self.base_url}/api/v1/search",
            params={"q": query, "per_page": per_page},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def verify(self, claim: str) -> Dict[str, Any]:
        """Fact-check a claim against the intelligence corpus."""
        resp = self._session.post(
            f"{self.base_url}/api/v1/verify",
            json={"claim": claim},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()
