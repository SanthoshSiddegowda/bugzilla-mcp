"""MCP package for Bugzilla server"""

from .tools.bugzilla import (
    bug_info,
    bug_comments,
    add_comment,
    bugs_quicksearch,
    learn_quicksearch_syntax,
    server_url,
    bug_url,
)

__all__ = [
    "bug_info",
    "bug_comments",
    "add_comment",
    "bugs_quicksearch",
    "learn_quicksearch_syntax",
    "server_url",
    "bug_url",
]

