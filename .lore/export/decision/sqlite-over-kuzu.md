---
id: sqlite-over-kuzu
type: decision
title: "Use SQLite instead of an embedded graph DB"
status: active
---

# Use SQLite instead of an embedded graph DB

Kùzu was archived Oct 2025. Oxigraph is RDF (wrong shape). SQLite is stdlib, inspectable, and sufficient at <5k nodes. Migration path stays mechanical if the schema ever outgrows CTEs.
