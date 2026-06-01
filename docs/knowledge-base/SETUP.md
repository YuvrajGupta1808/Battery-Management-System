# Tigris Remote Wiki Setup

CANary stores all BMS knowledge wiki pages on [Tigris](https://t3.storage.dev) — **not on your local disk**. Local workspace keeps diagram files only.

Pattern: [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

## 1. Credentials

1. Sign up at [storage.new](https://storage.new)
2. Create keys at [storage.new/accesskey](https://storage.new/accesskey)
3. Add to `.env` (see [`.env.example`](../../.env.example))

## 2. Bootstrap remote wiki

```bash
make tigris-bootstrap
make tigris-ls
make tigris-probe
```

Uploads seed pages to `s3://canary-bms-knowledge/dev/default/wiki/`.

## 3. Cursor MCP

[`.cursor/mcp.json`](../../.cursor/mcp.json) includes `tigris` via [`scripts/tigris-mcp.sh`](../../scripts/tigris-mcp.sh) (loads `.env`).

Enable **tigris** in Cursor Settings → Tools and MCP.

Test: *"List objects in canary-bms-knowledge"*

## 4. Retriever AI (rtrvr.ai)

1. Get API key from [rtrvr.ai](https://www.rtrvr.ai/)
2. Add `RTRVR_API_KEY=rtrvr_...` to `.env`
3. Sync cataloged BMS retrievals to Tigris:

```bash
make rtrvr-sync
make rtrvr-probe
```

See [RTRVR.md](./RTRVR.md) for API details and job catalog.

## 5. CANary workbench agent

Backend loads **Tigris MCP** only (read/write remote wiki). **rtrvr.ai is batch ingest** — run `make rtrvr-sync`, not an agent tool.

## 6. Tigris skills (optional)

```bash
npx skills add tigrisdata/skills
```

## Layout

See [ARCHITECTURE.md](./ARCHITECTURE.md) and [TIGRIS.md](../../TIGRIS.md).
