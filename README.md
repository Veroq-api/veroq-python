# veroq

VEROQ Python SDK -- verified intelligence for AI agents. The truth protocol for agentic AI.

> **Migrating from `polaris-news`?** This is the official successor. All class names and env vars are backwards compatible. Just change your import from `polaris_news` to `veroq`.

## Installation

```bash
pip install veroq
```

## Quick Start

```python
from veroq import VeroqClient

client = VeroqClient()  # uses VEROQ_API_KEY env var

# Ask anything
answer = client.ask("How is NVDA doing?")
print(answer["summary"])
print(answer["trade_signal"])

# Verify anything
result = client.verify("NVIDIA beat Q4 earnings")
print(result["verdict"], result["confidence"])
print(result["evidence_chain"])

# Stream in real-time
for event in client.ask_stream("AAPL price and technicals"):
    if event["type"] == "data":
        print(f"[{event['data']['key']}] loaded")
    elif event["type"] == "summary_token":
        print(event["data"]["token"], end="", flush=True)
```

## Enterprise Safety & Permissions

```python
from veroq import VeroqClient

client = VeroqClient()

# Configure enterprise safety
client.configure_enterprise({
    "enterprise_id": "acme-capital",
    "escalation_threshold": 60,
    "escalation_tools": ["ask", "verify"],
    "escalation_pauses": True,
    "session_id": "trading-session-001",
})

# High-level analysis with verification
result = client.ask("Full analysis of NVDA")
print(result["trade_signal"])  # { action: "hold", score: 55 }

# Verify a claim with evidence chain
verified = client.verify("NVIDIA beat Q4 earnings")
print(verified["verdict"])              # "supported"
print(verified["evidence_chain"])       # [{ source: "Reuters", ... }]
print(verified["confidence_breakdown"]) # { source_agreement: 0.92, ... }

# Get decision lineage
lineage = client.get_decision_lineage("ask", {"question": "Should I buy NVDA?"})
print(lineage["decision"])     # "review" (high-stakes detected)
print(lineage["high_stakes"])  # True

# Get audit trail
trail = client.get_audit_trail(session_id="trading-session-001")
```

### Universal Agent Connector

```python
from veroq import Agent

agent = Agent()  # reads VEROQ_API_KEY (or POLARIS_API_KEY) from env
result = agent.ask("What's happening with NVDA?")
print(result.summary)

# Full cross-reference -- everything about a ticker in one call
full = agent.full("AAPL")
print(full.price, full.technicals, full.earnings)

# Subscribe to real-time events
for event in agent.subscribe(tickers=["NVDA", "AAPL"], events=["brief"]):
    print(event.type, event.ticker, event.data)
```

### Authenticate via CLI

```bash
veroq login    # opens GitHub in your browser -- API key saved automatically
veroq whoami   # check your auth status
veroq logout   # remove saved credentials
```

You can also pass a key explicitly or set the `VEROQ_API_KEY` environment variable. For backwards compatibility, `POLARIS_API_KEY` is also supported.

## Backwards Compatibility

If you are migrating from `polaris-news`, the following aliases are available:

```python
from veroq import PolarisClient  # alias for VeroqClient
from veroq import PolarisError   # alias for VeroqError
```

Both `VEROQ_API_KEY` and `POLARIS_API_KEY` environment variables are supported. Credentials from both `~/.veroq/credentials` and `~/.polaris/credentials` are read.

## Methods

| Method | Description |
|--------|-------------|
| `ask(question, context?)` | Ask any financial question (routes to 40+ endpoints) |
| `ask_stream(question)` | Stream financial intelligence via SSE (generator) |
| `verify(claim, context?)` | Fact-check a claim against briefs |
| `feed(category?, limit?, page?, per_page?, min_confidence?)` | Get the news feed |
| `brief(brief_id, include_full_text?)` | Get a single brief by ID |
| `search(query, category?, page?, per_page?, sort?, min_confidence?, from_date?, to_date?, entity?, sentiment?)` | Search briefs |
| `generate(topic, category?)` | Generate a brief on a topic |
| `entities(q?, type?, limit?)` | List entities |
| `entity_briefs(name, role?, limit?, offset?)` | Get briefs for an entity |
| `trending_entities(limit?)` | Get trending entities |
| `similar(brief_id, limit?)` | Get similar briefs |
| `clusters(period?, limit?)` | Get brief clusters |
| `data(entity?, type?, limit?)` | Get structured data points |
| `agent_feed(category?, tags?, limit?, min_confidence?)` | Get agent-optimized feed |
| `compare_sources(brief_id)` | Compare sources for a brief |
| `trending(period?, limit?)` | Get trending briefs |
| `verify(claim, context?)` | Fact-check a claim against briefs |
| `research(query, max_sources?, depth?, category?)` | Deep research on a topic |
| `stream(categories?)` | Stream briefs via SSE (generator) |
| `ticker(symbol)` | Get ticker overview |
| `ticker_prices(symbols)` | Get live prices |
| `ticker_sentiment(symbol, period?)` | Sentiment breakdown |
| `ticker_signals(symbol, days?, threshold?)` | Trading signals |
| `candles(symbol, interval?, range?)` | OHLCV candle data |
| `technicals(symbol, range?)` | Full technical analysis |
| `screener(filters)` | Screen stocks by filters |
| `screener_natural(query)` | Natural language stock screen |
| `crypto(symbol?)` | Crypto data |
| `forex(pair?)` | Forex data |
| `generate_report(ticker, tier?)` | Generate a report |

## Error Handling

```python
from veroq import VeroqClient, AuthenticationError, RateLimitError, NotFoundError

client = VeroqClient()

try:
    brief = client.brief("abc123")
except AuthenticationError:
    print("Invalid API key")
except NotFoundError:
    print("Brief not found")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}s")
```

## Streaming

```python
client = VeroqClient()

for brief in client.stream(categories="technology,science"):
    print(f"[{brief.category}] {brief.headline}")
```

## Documentation

Full API documentation: https://veroq.ai/docs
