---
id: add-edge-flow
type: flow
title: "Add an edge with schema validation"
status: active
depends_on: [add-node-flow]
implements: [store-knowledge-graph]
part_of: [graph-engine]
triggers: [edge-created]
---

# Add an edge with schema validation

Verify both nodes exist and the (relation, from_type, to_type) triple is allowed.
