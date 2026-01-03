# AI Product Analytics using Model Context Protocol

This is an AI agent that answers natural-language queries on product analytics, where LLM handles the reasoning and MCP tools handle the data.

## Features
Using SaaS telemetry data (signups, logins, upgrades, feature events)
- Computes actual product metrics:
  - Activation rate `(e.g. "What was activation last week?")`
  - Weekly active users by plan `(e.g. "Show WAU by plan tier")`
  - Feature usage trends `(e.g. "How is export_report trending?")`
  - Channel conversion `(e.g. "Which channel converts best?")`
  - Usage segmentation
  - Country week-over-week changes `(e.g. "Any big week-over-week drops by country?")`
- Exposes metrics as MCP tools

## Process
1. The [init_db.py](init_db.py) script creates a synthetic SaaS analytics database in SQLite and populates with realistic user + event data.
2. The [analytics.py](analytics.py) module defines core product metrics (activation, WAU, conversion, feature usage, segmentation, etc.).
3. The [mcp_server.py](mcp_server.py) module exposes the functions as MCP tools so AI clients can call them deterministically.
4. The [mcp_client.py](mcp_client.py) script invokes those tools directly.
5. The [agent_cli.py](agent_cli.py) script adds a natural-language interface using an LLM, which plans what tool to call and formats results but does not invent numbers.

Build:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.init_db
python -m app.mcp_server
export XAI_API_KEY="your_key_here"
python agent_cli.py "activation rate last week"
```

## Tech stack
- Python 3.12
- SQLite + SQLAlchemy
- Model Context Protocol (MCP)
- Grok (xAI API) for natural language planning

## Guardrails and Edge cases 
- ask "summarize my resume" and the agent says "This agent only answers analytics questions." `:P`
- empty cohorts and invalid dates return 0.0
- irrelevant questions are rejected
- results and calculations stay repeatable

## References
- [MCP Python documentation](https://github.com/modelcontextprotocol/python-sdk) 
- [GPT](https://chatgpt.com/) for conceptual understanding and build
