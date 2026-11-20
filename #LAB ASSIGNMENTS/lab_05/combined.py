# SRN 02FE23BCI038 | Lab 5: MCP-Style Connector | combined
# Original definitions retained below; extensions follow.
"""
Lab 5: MCP-Style Connector -- Mini Integration Server
A server exposes a file reader (resource), a SQLite query (tool), and
a mock API call (tool) via a structured manifest, with a permission
boundary on the database tool.
"""
import sqlite3

# ---- Set up an in-memory SQLite DB for the demo ----------------------
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE signups (event TEXT, count INTEGER)")
conn.executemany("INSERT INTO signups VALUES (?, ?)", [
    ("AI Club Talk", 12), ("Hackathon Kickoff", 9), ("Robotics Demo", 15),
])
conn.commit()

MOCK_FILES = {"README.md": "Agentic AI Systems - mini MCP server demo."}
MOCK_API = {"events_today": ["AI Club Talk", "Robotics Demo"]}

CAPABILITIES = [
    {"name": "read_file", "kind": "resource",
     "input": {"path": "str"}, "output": {"content": "str"}},
    {"name": "query_db", "kind": "tool",
     "input": {"sql": "str"}, "output": {"rows": "list"}},
    {"name": "call_api", "kind": "tool",
     "input": {"endpoint": "str"}, "output": {"data": "any"}},
]

ALLOWED_CALLERS = {"planning_agent"}


class MCPServer:
    def list_capabilities(self):
        return CAPABILITIES

    def read_file(self, path):
        if path not in MOCK_FILES:
            return {"error": f"file not found: {path}"}
        return {"content": MOCK_FILES[path]}

    def query_db(self, sql, caller):
        if caller not in ALLOWED_CALLERS:
            return {"error": f"caller '{caller}' is not permitted to use query_db"}
        if not sql.strip().upper().startswith("SELECT"):
            return {"error": "only SELECT statements are permitted through this tool"}
        cur = conn.execute(sql)
        return {"rows": cur.fetchall()}

    def call_api(self, endpoint):
        if endpoint not in MOCK_API:
            return {"error": f"unknown endpoint: {endpoint}"}
        return {"data": MOCK_API[endpoint]}


class MCPClient:
    def __init__(self, server, caller_name):
        self.server = server
        self.caller_name = caller_name

    def discover(self):
        return self.server.list_capabilities()

    def call(self, capability_name, **kwargs):
        manifest = {c["name"]: c for c in self.discover()}
        if capability_name not in manifest:
            raise ValueError(f"unknown capability: {capability_name}")
        method = getattr(self.server, capability_name)
        if capability_name == "query_db":
            return method(caller=self.caller_name, **kwargs)
        return method(**kwargs)



A1=True
A2=True

from pathlib import PurePosixPath
class ExtendedMCPServer(MCPServer):
    def list_capabilities(self):
        return CAPABILITIES
    def list_files(self):
        return {'files': sorted(MOCK_FILES)}
    def read_file(self,path):
        p=PurePosixPath(path)
        if A2 and (not p.is_absolute() or '..' in p.parts or p.parts[:2] != ('/','safe')):
            return {'error':'outside safe directory /safe/', 'path':path}
        return super().read_file(path)
if A1:
    CAPABILITIES.append({'name':'list_files','kind':'resource','input':{},'output':{'files':'list'}})
if A2: MOCK_FILES={'/safe/README.md':'Safe classroom resource', '/private.txt':'Must not be exposed'}
def demo():
    server=ExtendedMCPServer();client=MCPClient(server,'planning_agent')
    for c in client.discover():
        print('Discovered:',c)
        # Generic zero-argument discovery: no special-case client dispatch.
        if not c['input']:
            r=client.call(c['name']);print('Discovered call output:',r);assert 'files' in r
    good='/safe/README.md' if A2 else 'README.md'
    print('Read:',client.call('read_file',path=good))
    if A2:
        for path in ['/private.txt','/safe/../private.txt','/safeevil/file','README.md']:
            r=client.call('read_file',path=path);print('Adversarial path:',path,r);assert 'error' in r and 'content' not in r
    print('PASS: manifest discovery and structured path rejection')

if __name__ == "__main__":
    demo()
