"""Middleware for Bugzilla MCP server"""

from .validate_headers import ValidateHeaders

__all__ = ["ValidateHeaders"]

