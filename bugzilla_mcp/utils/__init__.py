"""Utilities for Bugzilla MCP server"""

from .bugzilla import Bugzilla

# Global Bugzilla instance, set by middleware
bz = None

__all__ = ["Bugzilla", "bz"]
