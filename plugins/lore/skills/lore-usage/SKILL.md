---
name: lore-usage
description: Keep the Lore knowledge graph in sync with ongoing work. Invoke automatically whenever the conversation touches the project's business knowledge — how flows work, which capabilities exist, what rules protect an entity, architectural decisions, module dependencies, or contradictions between the graph and the code being discussed.
user-invocable: false
---

# Lore — read-first, write-on-decision

This project ships with the **Lore MCP server** (`lore_*` tools) that stores
business knowledge as a typed graph: modules, capabilities, flows, events,
rules, forms, entities and decisions. Treat Lore as the project's **living
memory**.

## Read before acting

Before answering "how does X work?" or writing non-trivial code that touches
a known concept, consult the graph:

1. `lore_query(text_or_id, depth=1)` — **`text_or_id` is required**. Exact id / title substring / tag.
2. `lore_list(type=..., include_body=False)` — cheap summary scan; follow up with `lore_get_node` for detail.
3. `lore_get_node(id, include_edges=true)` — full detail of a hit.
4. `lore_find_variants(capability_id)` — "how many ways of doing X?"
5. `lore_traverse(from_id, relations, max_depth)` — blast radius.

If the graph has the answer, cite the node id(s). If it's silent, say so —
don't fabricate.

## Detect contradictions

If the user or the code says one thing and the graph says another, **stop
and surface the mismatch** before acting. Ask which is authoritative. Do
not silently reconcile.

## Write on decision

When the conversation produces one of these, persist it:

| Trigger | Action |
|---|---|
| New module / capability / flow named and agreed on | `lore_add_node(...)` |
| Many related nodes at once (bootstrap, discovery) | `lore_add_nodes([...])` — one transaction |
| Flow A now supersedes flow B | `lore_add_edge(from=A, to=B, relation="supersedes")`, mark `B.status="superseded"` |
| New event emitted by a flow | `lore_add_node(type="event")` + `triggers` edge |
| New rule or validation | `lore_add_node(type="rule")` + `enforces` edge to the entity |
| Architectural decision | `lore_add_node(type="decision")` + `references` edge from the flow/rule it motivated |

Batch related edits; after substantive writes, call `lore_audit()` and
surface new warnings.

## Provenance — always set metadata

Every node you create must carry provenance in `metadata` so the user can
later audit what was inferred vs. stated. Standard keys:

| Key | Values / format | When |
|---|---|---|
| `source` | `user_stated` \| `user_confirmed` \| `inferred_from_code` \| `inferred_from_conversation` | Always |
| `confidence` | `high` \| `medium` \| `low` | Always |
| `source_context` | one-line free text, e.g. `"conversation 2026-04-22"` or `"read src/foo/bar.py:42"` | Always |
| `source_ref` | `path:line` of the code it represents | When tracking a concrete code artifact |
| `last_verified_at` | ISO date, e.g. `"2026-04-22"` | After a human "yes, still correct" |
| `deprecated_at` | ISO date | When marking a node deprecated |
| `deprecated_reason` | one-line free text | When marking a node deprecated |
| `replaced_by` | id of the successor node | When superseded |

`inferred_from_conversation` is allowed but **prefer asking first** before
persisting inferences.

## Updating metadata without losing provenance

`lore_update_node(metadata=…)` **replaces** the whole dict (destroys
provenance). **Prefer `metadata_patch`**: it merges at the top level, and
passing `null` as a value removes a key.

```
lore_update_node(id="flow-x", metadata_patch={"confidence": "low",
                                              "last_verified_at": "2026-04-22"})
```

## Lifecycle & soft-delete

Valid statuses: `active | draft | deprecated | superseded | archived`.

| Situation | Do |
|---|---|
| In-progress, not yet real | `status="draft"` |
| Still exists in code, still correct | `status="active"` |
| No longer used, historical record kept | `status="deprecated"` + `metadata_patch.deprecated_at` + `deprecated_reason` |
| Replaced by another node | `status="superseded"` + `supersedes` edge from successor + `metadata_patch.replaced_by` |
| Frozen but worth remembering (old version, prior product) | `status="archived"` |
| Typo / mistake only | `lore_delete_node` — the only legitimate hard delete |

**Never call `lore_delete_node` for a concept that existed.** Hard delete
cascades and destroys edges; the MCP reply includes an `edges_lost`
warning. Soft-delete preserves the graph's history.

## Renaming / moving a node

The graph treats ids as permanent. To "rename" `flow-checkout` →
`flow-order-placement`:

1. `lore_add_node(id="flow-order-placement", ...)` with full provenance.
2. `lore_add_edge(from="flow-order-placement", to="flow-checkout", relation="supersedes")`.
3. `lore_update_node("flow-checkout", status="superseded",
                     metadata_patch={"deprecated_at": "<today>",
                                     "replaced_by": "flow-order-placement"})`.
4. Re-attach any `part_of` / `implements` edges from the old id to the new one.

## Inspecting history

`lore_history(id)` returns the append-only MCP event log for a node
(newest first). Use it to answer "when was this deprecated?" or "what
changed and when?".

## Language of the content

Infrastructure (tool descriptions, error messages) is English. Node
**titles and bodies** must be written in **the natural language the user
uses in this conversation** (Spanish, English, etc.). IDs remain in
English kebab-case regardless.

If `.lore/config.json` exists and has a `language` key, follow it.
Otherwise follow the conversation language.

## Model routing — delegate reads to Haiku

Use the caller's model for decisions and writes. Delegate broad read-only
exploration to the cheaper `lore-explorer` sub-agent (Haiku):

| Situation | How |
|---|---|
| Single node lookup, 1-2 tool calls | Stay in caller's model |
| Scanning >20 nodes, deep traversal, multi-hop audit | `Agent(subagent_type: "lore-explorer", prompt: "<question>")` |
| Bootstrap / repo scan | Already handled by `/lore:bootstrap` (Haiku) |
| Detecting contradictions, choosing relations, modelling new nodes | Caller's model — requires reasoning |
| Any write (`lore_add_*`, `lore_update_*`, `lore_delete_*`) | **Caller's model only.** Never let a Haiku sub-agent write |

If `.lore/config.json` has `models.exploration`, honor it when picking the
sub-agent model; otherwise default to `haiku`. Example config:

```json
{ "language": "es", "models": { "exploration": "haiku", "write": "sonnet" } }
```

Rule of thumb: **Haiku reads, Sonnet/Opus decides what to write.** When a
sub-agent's finding must become a node/edge, have it return JSON and
persist from the caller after review.

## Id conventions

- Kebab-case only: lowercase letters, digits, single hyphens (e.g. `payment-by-transfer`).
- No colons, underscores, or uppercase. No leading/trailing hyphens, no `--`.
- Prefix generic words: `overview` → `billing-overview`.
- Convention by type: `module-<name>`, `capability-<slug>`, `flow-<slug>`, etc.

## Valid relations (shortlist)

The schema rejects invalid type pairs. Most common:

- `part_of`: flow/capability/form/event → **module**
- `implements`: flow → capability
- `depends_on`: module/flow → module/flow (**not** capability → capability)
- `triggers`: flow/event → event/flow
- `validates`: form → rule
- `enforces`: rule → entity
- `supersedes`: flow → flow or rule → rule
- `references`: any → decision
- `conflicts_with`: rule↔rule or flow↔flow

If an edge is rejected, re-model: capabilities don't depend on each other —
their implementing **modules** or **flows** do.

## When NOT to write

Skip persistence for:

- Exploratory talk ("what if we tried X").
- Pure code refactors that don't change business behavior.
- Details already captured — prefer `lore_update_node` over re-adding.
