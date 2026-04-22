# Lore

> The living knowledge graph for your software project.

**Lore** captures the business logic of a project — modules, capabilities, flows, events, rules, forms, entities and decisions — as a typed graph backed by SQLite, and exposes it over **MCP** so AI coding assistants (Claude Code, Cursor, Claude Desktop) can query and maintain it as part of normal work.

It answers questions like *"how many ways of registering a payment exist?"*, *"what breaks if I touch `flow-checkout`?"* or *"which rules protect this entity?"* in a single tool call, with provenance, without re-exploring the codebase each time.

## Why

- **Persistent memory** across sessions — the graph survives context resets.
- **Zero documentation overhead** — the assistant writes as concepts get decided, not as a separate chore.
- **Auditable** — every node carries `source`, `confidence`, `source_context`. Every MCP call is logged.
- **Token-efficient** — summary-only listings, batch ops, cheap sub-agents for exploration, WAL-mode SQLite.

## Install (Claude Code plugin — recommended)

```
/plugin marketplace add YACB2/lore
/plugin install lore@lore
```

Reload, then from the project you want to model run `lore init` (or `/lore:bootstrap` for a guided onboarding that scans the code with Haiku). "Project" can be a single repo *or* a workspace that contains several repos — Lore has no opinion, `.lore/lore.db` is created relative to whatever directory you launched Claude Code from.

The plugin bundles:

- **MCP server** exposing `lore_add_node`, `lore_add_nodes`, `lore_update_node`, `lore_delete_node`, `lore_get_node`, `lore_add_edge`, `lore_add_edges`, `lore_remove_edge`, `lore_query`, `lore_traverse`, `lore_list`, `lore_find_variants`, `lore_audit`, `lore_history`, `lore_stats`, `lore_export_markdown`.
- **Auto-invoked skill** (`lore-usage`) that tells Claude to read before acting and write on decision, with provenance rules and lifecycle conventions.
- **Sub-agent `lore-explorer`** (Haiku, read-only) for broad exploration without burning expensive tokens.
- **Slash commands**: `/lore:init`, `/lore:bootstrap`, `/lore:audit`, `/lore:show <id>`, `/lore:recent`, `/lore:impact <id>`, `/lore:probe <path>` (audit another project's graph without switching directory).

## Install (standalone CLI / other MCP hosts)

```bash
pipx install projectlore   # or: uv tool install projectlore
lore init
```

For Cursor / Claude Desktop:

```json
{
  "mcpServers": {
    "lore": {
      "command": "lore",
      "args": ["mcp", "--db", ".lore/lore.db"]
    }
  }
}
```

## CLI reference

```bash
lore init                      # create .lore/lore.db
lore list [--type flow]        # summary listing (id, type, title, status)
lore show <id>                 # full detail + edges
lore query "payment"           # exact id → title substring → tag fallback
lore variants <capability-id>  # flows implementing a capability
lore audit                     # orphans, cycles, id hygiene
lore stats [--since ISO]       # token/usage analytics from the audit log
lore export --out .lore/export # one markdown file per node
```

## Schema

**Eight node types** (stack-agnostic): `module`, `capability`, `flow`, `event`, `rule`, `form`, `entity`, `decision`.

**Nine relations**: `part_of`, `implements`, `depends_on`, `triggers`, `validates`, `enforces`, `supersedes`, `references`, `conflicts_with`. Type pairs are restricted (see `schema.py`).

**Statuses**: `active | draft | deprecated | superseded | archived`. Soft-delete is the default; `lore_delete_node` is reserved for typos and warns about edge loss.

The central abstraction is **`capability`** — a thing the system knows how to do, independent of how. Multiple `flow` nodes can `implements` the same capability, surfacing UX/logic divergences.

## Model routing

Operations are split by cost:

- **Reads** (broad scans, traversals, audits): delegated to Haiku via the `lore-explorer` sub-agent or `model: haiku` frontmatter on slash commands.
- **Writes & modeling decisions**: caller's model (Sonnet/Opus). A sub-agent proposes JSON; the caller reviews and persists.

Override per-project in `.lore/config.json`:

```json
{
  "language": "es",
  "app_name": "my-app",
  "models": { "exploration": "haiku", "write": "sonnet" }
}
```

## Provenance & history

Every node carries `metadata.{source, confidence, source_context}` and, when relevant, `source_ref` (`path:line`), `last_verified_at`, `deprecated_at`, `deprecated_reason`, `replaced_by`.

`lore_update_node(metadata_patch=…)` merges without destroying provenance; `metadata` still exists for rare full replacements.

`lore_history(id)` returns every MCP event for a node (newest first) from the append-only audit log. `lore_stats` aggregates by tool/op and reports input/output bytes.

## Status

Pre-MVP, alpha. Schema and MCP tool surface may change before 0.1.0.

## Development

```bash
uv sync --all-groups
uv run pytest -q
uv run ruff check src tests
```

Tests live in `tests/`. The plugin layout is validated by `test_plugin_structure.py`.

## License

MIT.
