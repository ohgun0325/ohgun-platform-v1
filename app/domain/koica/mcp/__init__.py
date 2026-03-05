"""KOICA MCP (Model Context Protocol) 모듈.

KoElectra와 Exaone을 FastMCP로 연결하는 MCP 서버 및 툴 정의.
"""

from app.domain.koica.mcp.server import create_mcp_server

__all__ = ["create_mcp_server"]
