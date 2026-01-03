import asyncio
import json
from datetime import date
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from .db import SessionLocal
from .analytics import (
    get_activation_rate,
    get_wau_by_plan,
    get_feature_timeseries,
    get_conversion_by_channel,
    get_feature_usage_by_segment,
    get_country_wow_change,
)


server = Server("analytics-mcp")


def get_db():
    return SessionLocal()


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="activation_rate",
            description="Compute 7-day activation rate for a signup cohort.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cohort_start": {"type": "string", "format": "date"},
                    "cohort_end": {"type": "string", "format": "date"},
                },
                "required": ["cohort_start", "cohort_end"],
            },
        ),
        types.Tool(
            name="wau_by_plan",
            description="Get weekly active users by plan tier over a date range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                },
                "required": ["start_date", "end_date"],
            },
        ),
        types.Tool(
            name="feature_timeseries",
            description="Get daily counts for a feature event over a date range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_name": {"type": "string"},
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                },
                "required": ["event_name", "start_date", "end_date"],
            },
        ),
        types.Tool(
            name="conversion_by_channel",
            description="Get 30-day conversion rate by acquisition channel for a signup cohort.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cohort_start": {"type": "string", "format": "date"},
                    "cohort_end": {"type": "string", "format": "date"},
                },
                "required": ["cohort_start", "cohort_end"],
            },
        ),
        types.Tool(
            name="feature_usage_by_segment",
            description="Rank features by usage for a given plan tier over a date range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "plan_tier": {"type": "string"},
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                },
                "required": ["plan_tier", "start_date", "end_date"],
            },
        ),
        types.Tool(
            name="country_wow_change",
            description="Detect week-over-week usage drops by country.",
            inputSchema={
                "type": "object",
                "properties": {
                    "week0_start": {"type": "string", "format": "date"},
                    "week1_start": {"type": "string", "format": "date"},
                    "drop_threshold": {"type": "number"},
                },
                "required": ["week0_start", "week1_start"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent]:
    db = get_db()
    try:
        if name == "activation_rate":
            cs = date.fromisoformat(arguments["cohort_start"])
            ce = date.fromisoformat(arguments["cohort_end"])
            payload = {"activation_rate_7d": get_activation_rate(db, cs, ce)}

        elif name == "wau_by_plan":
            sd = date.fromisoformat(arguments["start_date"])
            ed = date.fromisoformat(arguments["end_date"])
            payload = get_wau_by_plan(db, sd, ed)

        elif name == "feature_timeseries":
            event_name = arguments["event_name"]
            sd = date.fromisoformat(arguments["start_date"])
            ed = date.fromisoformat(arguments["end_date"])
            payload = get_feature_timeseries(db, event_name, sd, ed)

        elif name == "conversion_by_channel":
            cs = date.fromisoformat(arguments["cohort_start"])
            ce = date.fromisoformat(arguments["cohort_end"])
            payload = get_conversion_by_channel(db, cs, ce)

        elif name == "feature_usage_by_segment":
            plan_tier = arguments["plan_tier"]
            sd = date.fromisoformat(arguments["start_date"])
            ed = date.fromisoformat(arguments["end_date"])
            payload = get_feature_usage_by_segment(db, plan_tier, sd, ed)

        elif name == "country_wow_change":
            w0 = date.fromisoformat(arguments["week0_start"])
            w1 = date.fromisoformat(arguments["week1_start"])
            drop = float(arguments.get("drop_threshold", 0.2))
            payload = get_country_wow_change(db, w0, w1, drop_threshold=drop)

        else:
            payload = {"error": f"Unknown tool: {name}"}

        return [
            types.TextContent(
                type="text",
                text=json.dumps(payload),
            )
        ]
    finally:
        db.close()


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())