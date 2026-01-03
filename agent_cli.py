# import asyncio
# import json
# import re
# from datetime import date, timedelta

# from mcp import ClientSession
# from mcp.client.stdio import stdio_client
# from mcp import StdioServerParameters


# SERVER = StdioServerParameters(
#     command="/Users/sanya/Downloads/llm_feature_analytics/venv/bin/python",
#     args=["-m", "app.mcp_server"],
#     cwd="/Users/sanya/Downloads/llm_feature_analytics",
# )


# async def ask(question: str):
#     async with stdio_client(SERVER) as (read, write):
#         async with ClientSession(read, write) as session:
#             await session.initialize()

#             today = date.today()

#             if "activation" in question.lower():
#                 res = await session.call_tool(
#                     "activation_rate",
#                     {
#                         "cohort_start": str(today - timedelta(days=14)),
#                         "cohort_end": str(today - timedelta(days=7)),
#                     },
#                 )
#                 data = json.loads(res.content[0].text)
#                 print(f"7-day activation rate: {data['activation_rate_7d']:.2%}")
#                 return

#             if "wau" in question.lower() or "active" in question.lower():
#                 res = await session.call_tool(
#                     "wau_by_plan",
#                     {
#                         "start_date": str(today - timedelta(days=28)),
#                         "end_date": str(today),
#                     },
#                 )
#                 data = json.loads(res.content[0].text)
#                 print(json.dumps(data[:10], indent=2))
#                 return

#             if "feature" in question.lower() and "time" in question.lower():
#                 res = await session.call_tool(
#                     "feature_timeseries",
#                     {
#                         "event_name": "export_report",
#                         "start_date": str(today - timedelta(days=30)),
#                         "end_date": str(today),
#                     },
#                 )
#                 data = json.loads(res.content[0].text)
#                 print(json.dumps(data[:10], indent=2))
#                 return

#             print("Sorry — I don't recognize that question yet.")


# if __name__ == "__main__":
#     import sys

#     q = " ".join(sys.argv[1:]) or "activation rate"
#     asyncio.run(ask(q))

import asyncio
import json
import sys
from datetime import date
from typing import Any, Dict
import os
import requests

from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# client = OpenAI()

SERVER = StdioServerParameters(
    command="/Users/sanya/Downloads/llm_feature_analytics/venv/bin/python",
    args=["-m", "app.mcp_server"],
    cwd="/Users/sanya/Downloads/llm_feature_analytics",
)


def select_model(question: str) -> str:
    if len(question) > 200:
        return "gpt-4.1"
    return "gpt-4.1-mini"


def plan_tool(question: str):
    today = date.today().isoformat()

    system = (
        "You are a router that maps user analytics questions to exactly one MCP tool "
        "and a JSON arguments object.\n\n"
        "TOOLS:\n"
        "1) activation_rate\n"
        "   args: cohort_start (YYYY-MM-DD), cohort_end (YYYY-MM-DD)\n"
        "2) wau_by_plan\n"
        "   args: start_date, end_date\n"
        "3) feature_timeseries\n"
        "   args: event_name, start_date, end_date\n"
        "4) conversion_by_channel\n"
        "   args: cohort_start, cohort_end\n"
        "5) feature_usage_by_segment\n"
        '   args: plan_tier (\"free\"|\"pro\"|\"enterprise\"), start_date, end_date\n'
        "6) country_wow_change\n"
        "   args: week0_start, week1_start, drop_threshold (e.g. 0.2)\n\n"
        f"Rules:\n"
        f"- Today is {today}.\n"
        "- Use ISO dates only.\n"
        "- Choose exactly ONE tool_name from the list.\n"
        "- Always return ONLY valid JSON of the form:\n"
        "{\"tool_name\": \"...\", \"arguments\": { ... }}\n"
    )

    prompt = system + "\nUser question:\n" + question + "\nJSON output only:\n"

    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        raise RuntimeError("XAI_API_KEY is not set")

    resp = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "grok-3-mini",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
            "temperature": 0,
        },
        timeout=60,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    return json.loads(text)

async def run_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if result.structuredContent is not None:
                return result.structuredContent
            if result.content and hasattr(result.content[0], "text"):
                try:
                    return json.loads(result.content[0].text)
                except Exception:
                    return {"raw": result.content[0].text}
            return {}


def format_answer(
    question: str, tool_name: str, arguments: Dict[str, Any], data: Dict[str, Any]
) -> str:
    q = question.strip()
    if tool_name == "activation_rate":
        rate = data.get("activation_rate_7d")
        if isinstance(rate, (int, float)):
            return (
                f"7-day activation rate for cohort "
                f"{arguments.get('cohort_start')} → {arguments.get('cohort_end')}: "
                f"{rate:.2%}"
            )
        return json.dumps(data, indent=2)

    if tool_name == "wau_by_plan":
        items = data if isinstance(data, list) else data.get("items", [])
        return json.dumps(items[:10], indent=2)

    if tool_name == "feature_timeseries":
        items = data if isinstance(data, list) else data.get("items", [])
        return json.dumps(items[:10], indent=2)

    if tool_name == "conversion_by_channel":
        items = data if isinstance(data, list) else data.get("items", [])
        q_lower = q.lower()
        channel = None
        for ch in ["paid", "organic", "referral"]:
            if ch in q_lower:
                channel = ch
                break

        if channel:
            row = next(
                (r for r in items if r.get("acquisition_channel") == channel), None
            )
            if row:
                rate = row.get("conversion_rate_30d")
                if isinstance(rate, (int, float)):
                    return (
                        f"30-day conversion rate for {channel} channel "
                        f"({arguments.get('cohort_start')} → {arguments.get('cohort_end')}): "
                        f"{rate:.2%} "
                        f"({row.get('converted')}/{row.get('cohort_size')})"
                    )
        # fallback: full list
        return json.dumps(items, indent=2)


    if tool_name == "feature_usage_by_segment":
        items = data if isinstance(data, list) else data.get("items", [])
        return json.dumps(items, indent=2)

    if tool_name == "country_wow_change":
        items = data if isinstance(data, list) else data.get("items", [])
        return json.dumps(items, indent=2)

    return json.dumps(data, indent=2)


async def main():
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = "What is the activation rate for recent signups?"

    q_lower = question.lower()
    analytics_keywords = [
        "activation",
        "signup",
        "signups",
        "wau",
        "week",
        "month",
        "day",
        "year",
        "weekly active",
        "active users",
        "feature",
        "conversion",
        "channel",
        "plan",
        "tier",
        "country",
        "week over week",
        "wow",
        "trend",
        "time series",
        "usage",
        "cohort",
    ]

    if not any(k in q_lower for k in analytics_keywords):
        print("This agent only answers analytics questions about product usage, activation, WAU, features, conversion, and country-level trends.")
        return

    plan = plan_tool(question)
    tool_name = plan.get("tool_name")
    arguments = plan.get("arguments", {})

    if tool_name not in {
        "activation_rate",
        "wau_by_plan",
        "feature_timeseries",
        "conversion_by_channel",
        "feature_usage_by_segment",
        "country_wow_change",
    }:
        print("Planner could not map this question to a supported analytics tool.")
        print(plan)
        return

    data = await run_tool(tool_name, arguments)
    text = format_answer(question, tool_name, arguments, data)
    print(text)


if __name__ == "__main__":
    asyncio.run(main())