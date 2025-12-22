# GraphQL Voyager (Textual)

Console GraphQL client written in Python + [Textual](https://github.com/Textualize/textual). Allows sending GraphQL queries directly from the terminal. Packaged as a module with CLI.

## Installation
1. Create and activate a virtual environment (optional).
2. Install the module (it will pull dependencies):
   ```bash
   pip install .
   # or for dev mode
   pip install -e .
   ```
httpx is used if available; otherwise, the request goes through the standard library urllib.
**Launch**:
    ```bash
    http-voyager
    # or
    python -m voyager
    ```

**Controls**
- Ctrl+S or F5 — send request.
- Ctrl+Enter — send request from any field.
- Ctrl+L — go to endpoint field.
- Ctrl+Shift+C, Command+C (macOS) or Copy button — copy the entire response to clipboard.
- Clear Response button — clear the response panel.
- Verify TLS certificates (recommended) checkbox — disable if you need to accept a self-signed certificate (risky).
- When switching to the Docs tab, current Endpoint/Headers/Verify TLS from the Query tab are pulled automatically.
- The Docs tab shows the tree of types/fields and details of the selected node; the tree expands automatically after loading.

**Tabs**
- Query — sending a query/mutation.
- Docs — schema inspection via introspection: enter Endpoint/Headers/Verify TLS, press Load Schema, see the tree of types/fields and description of the active node.
- Fields (Query)
- Endpoint — URL of the GraphQL server.
- Headers — JSON object or list of strings in Key: Value format.
- Variables — JSON object with variables.
- Query — the GraphQL query/mutation itself.

**Tips**
- If the server returns non-JSON, the response will be shown as is.
- The right panel displays status, execution time, and response body.
- The last sent query/mutation and settings (endpoint, headers, variables, TLS flag) are saved in ~/.config/http_voyager/state.json (or XDG_CONFIG_HOME), loaded on the next launch.

**Extension / Customization**
The module is built around GraphQLTabSpec and GraphQLVoyager. Change default values in voyager/config.py or create an application with your own GraphQLTabSpec:
    ```
    from voyager import GraphQLVoyager, GraphQLTabSpec
    
    spec = GraphQLTabSpec(
        id="main",
        title="Voyager",
        endpoint="https://...",
        query="...",
        variables="{}",
        headers="Authorization: Bearer ...",
    )
    
    GraphQLVoyager(tab_specs=spec).run()
    ```

You can inherit from GraphQLTab/GraphQLVoyager to change the layout or add additional panels in another way.