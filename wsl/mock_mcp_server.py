"""Offline tiny, safe MCP mock; to test the probe only, not a CAD implementation."""
from __future__ import annotations
import json, sys
for line in sys.stdin:
    if not line.strip():
        continue
    obj=json.loads(line)
    if 'id' not in obj:
        continue
    name=obj.get('method')
    if name=='initialize':
        result={'protocolVersion':'2025-06-18','capabilities':{'tools':{}},
                'serverInfo':{'name':'offline-mock','version':'0.1'}}
    elif name=='tools/list':
        result={'tools':[{'name':'drawing_info','description':'fake read-only',
                          'inputSchema':{'type':'object','properties':{}}}]}
    elif name=='tools/call' and obj.get('params',{}).get('name')=='drawing_info':
        result={'content':[{'type':'text','text':'{"mock":true,"drawing":"mock.dwg"}'}],
                'isError':False}
    else:
        response={'jsonrpc':'2.0','id':obj['id'],
                  'error':{'code':-32601,'message':'Method not found'}}
        print(json.dumps(response),flush=True)
        continue
    print(json.dumps({'jsonrpc':'2.0','id':obj['id'],'result':result}),flush=True)
