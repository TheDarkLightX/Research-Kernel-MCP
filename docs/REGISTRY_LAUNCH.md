# Registry Launch Checklist

Research Kernel MCP is source-installable now. The remaining registry steps are release/account actions, not code changes.

## Identity

- GitHub repository: `TheDarkLightX/Research-Kernel-MCP`
- MCP Registry name: `io.github.TheDarkLightX/research-kernel-mcp`
- Python distribution: `research-kernel-mcp`
- Initial version: `0.1.0`
- Transport: stdio
- Persistent state: `RESEARCH_HOME`

The exact GitHub-owner casing is intentional. The official registry has had case-sensitive GitHub namespace authorization behavior, so the server name preserves `TheDarkLightX`.

## 1. Verify the source package

```bash
uvx --from git+https://github.com/TheDarkLightX/Research-Kernel-MCP.git \
  research-kernel-mcp --self-test
```

For a local checkout:

```bash
python -m pip install .
research-kernel-mcp --self-test
pytest -q
```

## 2. Publish the Python package

The official MCP Registry stores metadata, not the executable package. Publish version `0.1.0` to PyPI first.

The repository includes `.github/workflows/publish-release.yml`. It uses GitHub OIDC for both PyPI Trusted Publishing and the official MCP Registry.

One-time PyPI setup before the first release:

1. Create/claim the PyPI project `research-kernel-mcp`.
2. Add a Trusted Publisher for:
   - owner: `TheDarkLightX`
   - repository: `Research-Kernel-MCP`
   - workflow: `publish-release.yml`
   - environment: leave blank unless you intentionally add a protected GitHub environment.
3. Publish a GitHub release whose tag exactly matches `pyproject.toml` and `server.json`, e.g. `v0.1.0`.

The workflow refuses to publish if the release tag, Python package version, server version, and registry package version disagree. It then runs the self-test/tests, builds and publishes PyPI, validates `server.json`, authenticates to the official MCP Registry with GitHub OIDC, and publishes the registry entry.

The PyPI project must trust this repository/workflow before the first publish.

The README contains the required package-ownership marker:

```text
mcp-name: io.github.TheDarkLightX/research-kernel-mcp
```

After publication, verify:

```bash
uvx research-kernel-mcp@0.1.0 --self-test
```

## 3. Official MCP Registry

Install the publisher and validate the checked-in metadata:

```bash
brew install mcp-publisher
mcp-publisher validate server.json
mcp-publisher login github
mcp-publisher publish server.json
```

Then verify discovery:

```bash
curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.TheDarkLightX/research-kernel-mcp"
```

## 4. Glama

The root `glama.json` declares `TheDarkLightX` as maintainer.

Submit the GitHub repository through Glama's **Add MCP Server** flow:

```text
https://github.com/TheDarkLightX/Research-Kernel-MCP
```

Glama clones and evaluates open-source servers, including license, health, and tool-definition quality. After the listing exists, authenticate with GitHub and claim it.

## 5. Smithery

Use Smithery's **Publish MCP Server** flow and connect:

```text
https://github.com/TheDarkLightX/Research-Kernel-MCP
```

The repository now exposes a deterministic source install:

```bash
uvx --from git+https://github.com/TheDarkLightX/Research-Kernel-MCP.git research-kernel-mcp
```

Set persistent storage with:

```text
RESEARCH_HOME=/persistent/path
```

## 6. Community discovery

After the package/registry listing is live, submit to active curated indexes. Prefer lists that still accept pull requests and require working install instructions rather than scraped catalogs.

Do not claim a hosted/remote MCP endpoint until one actually exists. The current supported public distribution is a local stdio server.
