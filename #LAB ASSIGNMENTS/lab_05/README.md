# Lab 5: MCP-Style Connector

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — Add a Fourth, Discoverable Capability
Add a `list_files` resource capability to the manifest and server. The client must discover and call it without any hard-coded reference to its name anywhere in `MCPClient` — only `CAPABILITIES` should need to change. Submit the updated server/client code and a transcript demonstrating the new capability being discovered and called.
Assignment 2 — Scope read_file to a Safe Directory
Add a second permission boundary: `read_file` may only read paths inside a declared safe directory (e.g. paths starting with `/safe/`). Write an adversarial test that attempts to read a path outside that directory and confirm the server rejects it with a structured error rather than reading it. Submit the updated code and the adversarial test's result.

## Implementation notes

The additional resource is found through the manifest and a generic zero-argument invocation. The unchanged client contains no special case for list_files. Mock path checks reject traversal and prefix lookalikes; no real filesystem reads occur.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_05/reference.py`.

### Full source

```python
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


if __name__ == "__main__":
    server = MCPServer()
    client = MCPClient(server, caller_name="planning_agent")

    print("=== Capability discovery ===")
    for c in client.discover():
        print(f"  {c['name']} ({c['kind']})  input={c['input']}  output={c['output']}")

    print("\n=== Call 1: read_file (resource) ===")
    print(client.call("read_file", path="README.md"))

    print("\n=== Call 2: query_db (tool, permitted caller, SELECT only) ===")
    print(client.call("query_db", sql="SELECT event, count FROM signups"))

    print("\n=== Call 3: call_api (tool) ===")
    print(client.call("call_api", endpoint="events_today"))

    print("\n=== Rejection path: disallowed statement ===")
    print(client.call("query_db", sql="DELETE FROM signups"))

    print("\n=== Rejection path: disallowed caller ===")
    other_client = MCPClient(server, caller_name="unregistered_agent")
    print(other_client.call("query_db", sql="SELECT * FROM signups"))
```

### Captured output

```text
=== Capability discovery ===
  read_file (resource)  input={'path': 'str'}  output={'content': 'str'}
  query_db (tool)  input={'sql': 'str'}  output={'rows': 'list'}
  call_api (tool)  input={'endpoint': 'str'}  output={'data': 'any'}

=== Call 1: read_file (resource) ===
{'content': 'Agentic AI Systems - mini MCP server demo.'}

=== Call 2: query_db (tool, permitted caller, SELECT only) ===
{'rows': [('AI Club Talk', 12), ('Hackathon Kickoff', 9), ('Robotics Demo', 15)]}

=== Call 3: call_api (tool) ===
{'data': ['AI Club Talk', 'Robotics Demo']}

=== Rejection path: disallowed statement ===
{'error': 'only SELECT statements are permitted through this tool'}

=== Rejection path: disallowed caller ===
{'error': "caller 'unregistered_agent' is not permitted to use query_db"}
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_05/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 5: MCP-Style Connector | assignment_1
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
A2=False

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
```

### Captured output

```text
Discovered: {'name': 'read_file', 'kind': 'resource', 'input': {'path': 'str'}, 'output': {'content': 'str'}}
Discovered: {'name': 'query_db', 'kind': 'tool', 'input': {'sql': 'str'}, 'output': {'rows': 'list'}}
Discovered: {'name': 'call_api', 'kind': 'tool', 'input': {'endpoint': 'str'}, 'output': {'data': 'any'}}
Discovered: {'name': 'list_files', 'kind': 'resource', 'input': {}, 'output': {'files': 'list'}}
Discovered call output: {'files': ['README.md']}
Read: {'content': 'Agentic AI Systems - mini MCP server demo.'}
PASS: manifest discovery and structured path rejection
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_05/assignment_2.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 5: MCP-Style Connector | assignment_2
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



A1=False
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
```

### Captured output

```text
Discovered: {'name': 'read_file', 'kind': 'resource', 'input': {'path': 'str'}, 'output': {'content': 'str'}}
Discovered: {'name': 'query_db', 'kind': 'tool', 'input': {'sql': 'str'}, 'output': {'rows': 'list'}}
Discovered: {'name': 'call_api', 'kind': 'tool', 'input': {'endpoint': 'str'}, 'output': {'data': 'any'}}
Read: {'content': 'Safe classroom resource'}
Adversarial path: /private.txt {'error': 'outside safe directory /safe/', 'path': '/private.txt'}
Adversarial path: /safe/../private.txt {'error': 'outside safe directory /safe/', 'path': '/safe/../private.txt'}
Adversarial path: /safeevil/file {'error': 'outside safe directory /safe/', 'path': '/safeevil/file'}
Adversarial path: README.md {'error': 'outside safe directory /safe/', 'path': 'README.md'}
PASS: manifest discovery and structured path rejection
```

## Combined source and captured output

Run from the repository root with `python labs/lab_05/combined.py`.

### Full source

```python
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
```

### Captured output

```text
Discovered: {'name': 'read_file', 'kind': 'resource', 'input': {'path': 'str'}, 'output': {'content': 'str'}}
Discovered: {'name': 'query_db', 'kind': 'tool', 'input': {'sql': 'str'}, 'output': {'rows': 'list'}}
Discovered: {'name': 'call_api', 'kind': 'tool', 'input': {'endpoint': 'str'}, 'output': {'data': 'any'}}
Discovered: {'name': 'list_files', 'kind': 'resource', 'input': {}, 'output': {'files': 'list'}}
Discovered call output: {'files': ['/private.txt', '/safe/README.md']}
Read: {'content': 'Safe classroom resource'}
Adversarial path: /private.txt {'error': 'outside safe directory /safe/', 'path': '/private.txt'}
Adversarial path: /safe/../private.txt {'error': 'outside safe directory /safe/', 'path': '/safe/../private.txt'}
Adversarial path: /safeevil/file {'error': 'outside safe directory /safe/', 'path': '/safeevil/file'}
Adversarial path: README.md {'error': 'outside safe directory /safe/', 'path': 'README.md'}
PASS: manifest discovery and structured path rejection
```

