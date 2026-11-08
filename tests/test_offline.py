"""Only offline checks: no AutoCAD or Windows claimed."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'windows'))


def load_module(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = load_module('bridge', 'windows/bridge.py')
verifier = load_module('verify_demo', 'windows/verify_demo.py')


class TestSecurityDefaults(unittest.TestCase):
    def test_readonly_and_sandbox_policy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'work').mkdir()
            for mode in ('readonly', 'sandbox'):
                env = bridge.make_server_env(root, mode)
                self.assertEqual(env['AUTOCAD_MCP_BACKEND'], 'com')
                self.assertEqual(env['CAD_PROGID'], 'AutoCAD.Application.23.0')
                self.assertEqual(env['CAD_LAUNCH'], 'never')
                self.assertEqual(env['ALLOWED_PATHS'], str((root/'work').resolve()))
                self.assertIn('system_run_command', env['TOOL_DENYLIST'])
                self.assertIn('system_run_lisp', env['TOOL_DENYLIST'])
                self.assertEqual(env['READ_ONLY'], 'true' if mode=='readonly' else 'false')
                self.assertEqual(env['MAX_TOOL_COST'], 'read' if mode=='readonly' else 'mutate')
            with self.assertRaises(ValueError):
                bridge.make_server_env(root, 'unlimited')

    def test_mode_invalid_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(RuntimeError):
                bridge.read_mode(root)
            (root/'mode.txt').write_text('destructive\n',encoding='utf8')
            with self.assertRaises(RuntimeError):
                bridge.read_mode(root)
            (root/'mode.txt').write_text('readonly\n',encoding='utf8')
            self.assertEqual(bridge.read_mode(root),'readonly')


class TestGeometryVerifier(unittest.TestCase):
    def entities(self):
        line=lambda layer,a,b: {'kind':'line','layer':layer,'start':a,'end':b}
        circle=lambda layer,c,r: {'kind':'circle','layer':layer,'center':c,'radius':r}
        return [line('AI_BASE',(0,0,0),(100,0,0)),
                line('AI_BASE',(100,0,0),(100,60,0)),
                line('AI_BASE',(100,60,0),(0,60,0)),
                line('AI_BASE',(0,60,0),(0,0,0)),
                circle('AI_BASE',(50,30,0),10),
                line('AI_ADDED',(0,30,0),(100,30,0)),
                circle('AI_ADDED',(50,30,0),15)]

    def test_expected_seven_entities(self):
        self.assertEqual(verifier.validate(self.entities()), [])

    def test_detect_wrong_radius(self):
        es=self.entities()
        es[-1]['radius']=16
        self.assertTrue(any('AI_ADDED circle' in item for item in verifier.validate(es)))

    def test_detect_changed_baseline(self):
        es=self.entities()
        es[0]['start']=(2,0,0)
        self.assertTrue(any('base line' in item for item in verifier.validate(es)))

    def test_detect_extra_entity(self):
        es=self.entities()
        es.append({'kind':'line','layer':'TEST','start':(0,0,0),'end':(1,1,0)})
        self.assertTrue(any('total' in item for item in verifier.validate(es)))


class TestBridgeArtifacts(unittest.TestCase):
    def test_raw_protocol_mock(self):
        result=subprocess.run([sys.executable, str(ROOT/'wsl/probe_mcp.py'), '--mock'],
                              text=True, capture_output=True, timeout=12)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('"ok": true', result.stdout)
        self.assertIn('drawing_info', result.stdout)

    def test_shell_scripts_parse(self):
        for rel in ('wsl/launch_mcp.sh','wsl/configure_codex.sh'):
            p=subprocess.run(['bash','-n',str(ROOT/rel)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,f'{rel}: {p.stderr}')

    def test_toml_example_is_valid(self):
        sample='''[mcp_servers.autocad2019]
command = "/bin/bash"
args = ["/mnt/c/cad-mcp-2019/wsl/launch_mcp.sh"]
startup_timeout_sec = 60
tool_timeout_sec = 120
supports_parallel_tool_calls = false
'''
        parsed=tomllib.loads(sample)
        self.assertEqual(parsed['mcp_servers']['autocad2019']['tool_timeout_sec'],120)


if __name__=='__main__':
    unittest.main()
