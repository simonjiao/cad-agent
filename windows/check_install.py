"""Validate exact installed MCP version and Windows Python without shell quoting."""
from __future__ import annotations

from importlib.metadata import version
import struct
import sys

if sys.platform != 'win32':
    raise SystemExit('ERROR: use native Windows Python')
if sys.version_info[:2] != (3, 11):
    raise SystemExit(f'ERROR: Python 3.11 required; got {sys.version}')
if struct.calcsize('P') != 8:
    raise SystemExit('ERROR: 64-bit Python required')
import win32com.client  # noqa: F401
from server import main  # noqa: F401  # U-C4N v1.8.0 entry point
if version('autocad-mcp-pro') != '1.8.0':
    raise SystemExit('ERROR: autocad-mcp-pro version mismatch')
print('OK: Windows Python 3.11 x64; autocad-mcp-pro 1.8.0; server.main; pywin32')
