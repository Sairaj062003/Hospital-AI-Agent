"""MCP server exposing scheduling tools backed by Postgres.

Run this module directly to start the server listening on stdio. A client
(see client.py) launches this as a subprocess and talks to it over
stdin/stdout - no network, no auth, the simplest possible transport.
"""

import asyncio
import json

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from src.mcp_server.db import fetch_available_doctor_slots, mark_slot_booked

server = Server("scheduling-server")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_available_doctors_and_slots",
            description="Return every doctor with at least one open appointment slot, "
            "including the doctor's name, specialization, and slot time.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="book_slot",
            description="Book a specific appointment slot by its slot_id.",
            inputSchema={
                "type": "object",
                "properties": {"slot_id": {"type": "integer"}},
                "required": ["slot_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "list_available_doctors_and_slots":
        slots = fetch_available_doctor_slots()
        return [types.TextContent(type="text", text=json.dumps(slots))]

    if name == "book_slot":
        booked = mark_slot_booked(arguments["slot_id"])
        return [types.TextContent(type="text", text=json.dumps({"booked": booked}))]

    raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
