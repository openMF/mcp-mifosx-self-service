"""The README and the workflow guide must name the tools that really exist (US-E13-08)."""

import asyncio
import re
from pathlib import Path

import main  # noqa: F401  (registers every tool)
from mcp_app import mcp
from resources.workflows import get_workflows

ROOT = Path(__file__).resolve().parent.parent
# A tool name in the first or second column of a README table row: | GET | `tool_name` | ... |
README_TOOL = re.compile(r"^\|[^|\n]*\|\s*`(\w+)`\s*\|", re.MULTILINE)
WORKFLOW_CALL = re.compile(r"\b(?:Call|call)\s+(\w+)")


def registered_tools():
    return {tool.name for tool in asyncio.run(mcp.list_tools())}


def readme_tools():
    readme = (ROOT / "README.md").read_text()
    tools_section = readme.split("## Available MCP Tools", 1)[1]
    return set(README_TOOL.findall(tools_section))


def test_every_tool_is_listed_in_the_readme():
    assert sorted(registered_tools() - readme_tools()) == []


def test_the_readme_lists_only_tools_that_exist():
    assert sorted(readme_tools() - registered_tools()) == []


def test_the_workflow_guide_only_calls_tools_that_exist():
    called = set(WORKFLOW_CALL.findall(asyncio.run(get_workflows())))
    assert called, "the guide should name tools"
    assert sorted(called - registered_tools()) == []
