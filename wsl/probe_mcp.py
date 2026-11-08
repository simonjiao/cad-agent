"""A small stdlib-only MCP stdio handshake tester for WSL2 (or mock on Linux).

Sends initialize -> notifications/initialized -> tools/list -> tools/call drawing_info.
Never requests a write tool. Requires running AutoCAD for --real.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from queue import Empty, Queue
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent.parent


def command_for(real: bool) -> list[str]:
    if not real:
        return [sys.executable, str(Path(__file__).parent / 'mock_mcp_server.py')]
    launcher = ROOT / 'wsl' / 'launch_mcp.sh'
    exe = ROOT / '.venv' / 'Scripts' / 'python.exe'
    if not exe.exists():
        raise RuntimeError(f'Missing Windows Python: {exe}; first run install.ps1')
    if not launcher.exists():
        raise RuntimeError(f'Missing launcher: {launcher}')
    return ['bash', str(launcher)]


def read_lines(stream, queue):
    try:
        for line in iter(stream.readline, b''):
            queue.put(line)
    finally:
        queue.put(None)


def run(real: bool, timeout: float) -> dict:
    command = command_for(real)
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, bufsize=0)
    q = Queue()
    threading.Thread(target=read_lines, args=(proc.stdout, q), daemon=True).start()
    log_lines = []
    threading.Thread(target=read_lines, args=(proc.stderr, _ListQueue(log_lines)), daemon=True).start()
    seq = 0

    def send(method, params=None, notify=False):
        nonlocal seq
        msg = {'jsonrpc': '2.0', 'method': method}
        if params is not None:
            msg['params'] = params
        if not notify:
            seq += 1
            msg['id'] = seq
        data = json.dumps(msg, ensure_ascii=False).encode('utf-8') + b'\n'
        proc.stdin.write(data)
        proc.stdin.flush()
        return None if notify else seq

    def await_id(wanted):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                line = q.get(timeout=max(0.05, deadline - time.monotonic()))
            except Empty:
                break
            if line is None:
                break
            try:
                item = json.loads(line.decode('utf-8-sig').strip())
            except (UnicodeError, ValueError) as exc:
                raise RuntimeError(f'Non-JSON data on MCP stdout: {line[:200]!r}') from exc
            if item.get('id') == wanted:
                if 'error' in item:
                    raise RuntimeError(f'MCP request {wanted} error: {item["error"]}')
                return item.get('result', {})
        raise RuntimeError('MCP response timeout/EOF for id=' + str(wanted)
                        + '; stderr=' + b''.join(log_lines)[-2500:].decode('utf-8','replace'))

    try:
        init = await_id(send('initialize', {
            'protocolVersion': '2025-06-18',
            'capabilities': {},
            'clientInfo': {'name': 'cad2019-bundle-probe', 'version': '1.0'}
        }))
        send('notifications/initialized', notify=True)
        listed = await_id(send('tools/list'))
        names = {x.get('name') for x in listed.get('tools', [])}
        if 'drawing_info' not in names:
            raise RuntimeError('drawing_info not listed. Got: ' + ','.join(sorted(n for n in names if n)))
        drawing = await_id(send('tools/call', {'name': 'drawing_info', 'arguments': {}}))
        if drawing.get('isError'):
            raise RuntimeError(f'drawing_info MCP error: {drawing}')
        return {'ok': True, 'real_autocad': real,
                'protocol': init.get('protocolVersion'), 'tool_count': len(names),
                'tools': sorted(n for n in names if n),
                'drawing_info': drawing}
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


class _ListQueue:
    """Adapter for read_lines that collects stderr lines without blocking."""
    def __init__(self, items): self.items = items
    def put(self, data):
        if isinstance(data, bytes): self.items.append(data)


def main():
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--mock', action='store_true', help='Offline protocol self-test; no AutoCAD')
    mode.add_argument('--real', action='store_true', help='Real WSL2 -> Windows MCP -> AutoCAD')
    ap.add_argument('--timeout', type=float, default=45.0)
    args = ap.parse_args()
    result = run(real=args.real, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'MCP PROBE FAILED: {type(exc).__name__}: {exc}', file=sys.stderr)
        sys.exit(1)
