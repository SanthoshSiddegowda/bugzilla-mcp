"""Utilities for Bugzilla MCP server"""

from contextvars import ContextVar
from .bugzilla import Bugzilla

# Per-request Bugzilla client, set by middleware.
# A ContextVar (not a module global) keeps concurrent requests from
# different users on a shared server from seeing each other's credentials.
current_bz: ContextVar[Bugzilla | None] = ContextVar("current_bz", default=None)

__all__ = ["Bugzilla", "current_bz"]
