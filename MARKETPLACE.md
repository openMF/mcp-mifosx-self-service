# MCP Marketplace Listings

This document tracks the MCP marketplace registrations for `mcp-mifosx-self-service`. The sister project [mcp-mifosx](https://github.com/openMF/mcp-mifosx) is already listed on [Glama](https://glama.ai/mcp/servers/openMF/mcp-mifosx) — this guide covers how to get the self-service server listed on the same and additional marketplaces.

## Marketplace Overview

| Marketplace | URL | Status | Listing Type |
|---|---|---|---|
| **Glama** | https://glama.ai/mcp/servers | Pending | GitHub-based auto-scan |
| **Smithery** | https://smithery.ai | Pending | URL-based or CLI publish |
| **MCP.so** | https://mcp.so | Pending | Form submission |
| **mcpservers.org** | https://mcpservers.org | Pending | Form submission |

## Submission Details

### 1. Glama (highest priority)

Glama scans GitHub repositories and auto-populates server metadata — no special
config files are required. The sister project `mcp-mifosx` was listed this way
with nothing beyond its standard `README.md`.

- **Submit URL**: https://glama.ai/mcp/servers (click "Add Server")
- **Required**: GitHub repository URL (`https://github.com/openMF/mcp-mifosx-self-service`)
- **Auto-detected**: License (MPL-2.0), tools, categories
- **Reference**: The main mcp-mifosx listing — https://glama.ai/mcp/servers/openMF/mcp-mifosx

### 2. Smithery

Smithery supports URL-based publishing with automatic metadata scanning or a static server card.

- **Submit URL**: https://smithery.ai/new
- **Option A** — Host the server publicly and register the URL
- **Option B** — CLI publish:
  ```bash
  smithery mcp publish "<server-url>" -n @openMF/mcp-mifosx-self-service \
    --config-schema '{"type":"object","properties":{"MIFOS_BASE_URL":{"type":"string"},"MIFOS_TENANT":{"type":"string"}}}'
  ```
- **Server Card**: A static server card is available at `.well-known/mcp/server-card.json` for automated discovery when hosting the server over HTTP.

### 3. MCP.so

Community-driven MCP server directory.

- **Submit URL**: https://mcp.so/submit
- **Required fields**:
  - **Name**: `mcp-mifosx-self-service`
  - **Type**: MCP Server
  - **URL**: `https://github.com/openMF/mcp-mifosx-self-service`
  - **Server Config**:
    ```json
    {
      "mcpServers": {
        "mifos-self-service": {
          "command": "python",
          "args": ["main.py"],
          "env": {
            "MIFOS_BASE_URL": "https://tt.mifos.community",
            "MIFOS_TENANT": "default"
          }
        }
      }
    }
    ```

### 4. mcpservers.org

General MCP server listing directory.

- **Submit URL**: https://mcpservers.org/submit
- **Required fields**:
  - **Server Name**: Mifos X Self-Service MCP Server
  - **Short Description**: MCP server for the Apache Fineract / Mifos X Self-Service API. 57 AI-callable tools for mobile banking workflows — authentication, loans, savings, beneficiaries, transfers, and more.
  - **Link**: `https://github.com/openMF/mcp-mifosx-self-service`
  - **Category**: Finance
  - **Contact Email**: *(maintainer email)*

## Files Added for Marketplace Support

| File | Purpose |
|---|---|
| `.well-known/mcp/server-card.json` | Static MCP server metadata for automated discovery (Smithery, other crawlers) |
| `MARKETPLACE.md` | This document — tracks listing status and submission instructions |

## Server Metadata Summary

Use this information when filling out marketplace submission forms:

- **Name**: Mifos X Self-Service MCP Server
- **Description**: MCP server for the Apache Fineract / Mifos X Self-Service API. Provides 57 AI-callable tools for mobile banking workflows including authentication, client management, loans, savings, beneficiaries, transfers, guarantors, shares, and notifications.
- **Repository**: https://github.com/openMF/mcp-mifosx-self-service
- **License**: Mozilla Public License 2.0
- **Categories**: Finance, Banking, Microfinance
- **Tags**: fineract, mifos, banking, self-service, loans, savings, microfinance
- **Transport**: stdio (Python)
- **Runtime**: Python 3.10+
