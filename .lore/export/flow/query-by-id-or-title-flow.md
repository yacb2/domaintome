---
id: query-by-id-or-title-flow
type: flow
title: "Query by id, title substring or tag"
status: active
implements: [query-graph]
part_of: [graph-engine]
supersedes: [query-by-id-only-flow-v0]
---

# Query by id, title substring or tag

Resolve text → exact id match, fuzzy title match, then tag match. Expand neighborhood up to `depth` and return nodes + edges.
