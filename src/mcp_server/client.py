"""MCP client helpers for talking to the scheduling server.

Each function here is short-lived: it starts the server (server.py) as a
fresh subprocess, calls exactly one tool, and tears the connection down.
Callers (scheduling.py) use these instead of talking to the MCP SDK or the
database directly.
"""

import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_SERVER_MODULE = "src.mcp_server.server"


def _server_params() -> StdioServerParameters:
    # Pass a full copy of the parent's environment, not a replacement -
    # an incomplete env (e.g. missing SystemRoot) breaks Windows' socket
    # initialization in the child process. See server.py's notes.
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", _SERVER_MODULE],
        env=dict(os.environ),
    )


async def list_available_doctors_and_slots() -> list[dict]:
    async with stdio_client(_server_params()) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("list_available_doctors_and_slots", {})
            return json.loads(result.content[0].text)


async def list_specializations() -> list[str]:
    async with stdio_client(_server_params()) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("list_specializations", {})
            return json.loads(result.content[0].text)


async def book_slot(slot_id: int) -> bool:
    async with stdio_client(_server_params()) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("book_slot", {"slot_id": slot_id})
            return json.loads(result.content[0].text)["booked"]


async def get_hospital_info() -> dict:
    async with stdio_client(_server_params()) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("get_hospital_info", {})
            return json.loads(result.content[0].text)
