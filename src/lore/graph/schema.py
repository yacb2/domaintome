"""Schema definitions for the Lore graph.

Node types and relations are hardcoded in v1 (per PRD §3 non-goals) to validate
the schema before considering configurability.
"""

from __future__ import annotations

NODE_TYPES: frozenset[str] = frozenset(
    {
        "module",
        "capability",
        "flow",
        "event",
        "rule",
        "form",
        "entity",
        "decision",
    }
)

RELATIONS: frozenset[str] = frozenset(
    {
        "part_of",
        "implements",
        "depends_on",
        "triggers",
        "validates",
        "enforces",
        "supersedes",
        "references",
        "conflicts_with",
    }
)

# Allowed (relation, from_type, to_type) triples per PRD §4.4.
# A relation may appear multiple times with different type pairs.
ALLOWED_RELATIONS: frozenset[tuple[str, str, str]] = frozenset(
    {
        # part_of: flow/capability/form/event → module
        ("part_of", "flow", "module"),
        ("part_of", "capability", "module"),
        ("part_of", "form", "module"),
        ("part_of", "event", "module"),
        # implements: flow → capability
        ("implements", "flow", "capability"),
        # depends_on: module/flow → module/flow
        ("depends_on", "module", "module"),
        ("depends_on", "module", "flow"),
        ("depends_on", "flow", "module"),
        ("depends_on", "flow", "flow"),
        # triggers: flow/event → event/flow
        ("triggers", "flow", "event"),
        ("triggers", "flow", "flow"),
        ("triggers", "event", "event"),
        ("triggers", "event", "flow"),
        # validates: form → rule
        ("validates", "form", "rule"),
        # enforces: rule → entity
        ("enforces", "rule", "entity"),
        # supersedes: flow/rule → flow/rule (same type only — semantic)
        ("supersedes", "flow", "flow"),
        ("supersedes", "rule", "rule"),
        # references: any → decision
        *(("references", t, "decision") for t in NODE_TYPES if t != "decision"),
        # conflicts_with: rule ↔ rule, flow ↔ flow (declared manually in v1)
        ("conflicts_with", "rule", "rule"),
        ("conflicts_with", "flow", "flow"),
    }
)

# IDs too generic to live unprefixed (audit warning only, not enforced).
GENERIC_ID_WORDS: frozenset[str] = frozenset(
    {
        "overview",
        "create",
        "update",
        "delete",
        "list",
        "show",
        "index",
        "detail",
        "form",
        "main",
        "default",
    }
)

NODE_STATUSES: frozenset[str] = frozenset(
    {"active", "draft", "deprecated", "superseded", "archived"}
)


class SchemaError(ValueError):
    """Raised when a node or edge violates the schema."""


def validate_node_type(node_type: str) -> None:
    if node_type not in NODE_TYPES:
        raise SchemaError(
            f"Unknown node type {node_type!r}. Allowed: {sorted(NODE_TYPES)}"
        )


def validate_status(status: str) -> None:
    if status not in NODE_STATUSES:
        raise SchemaError(
            f"Unknown status {status!r}. Allowed: {sorted(NODE_STATUSES)}"
        )


def validate_relation(relation: str) -> None:
    if relation not in RELATIONS:
        raise SchemaError(
            f"Unknown relation {relation!r}. Allowed: {sorted(RELATIONS)}"
        )


def is_relation_allowed(relation: str, from_type: str, to_type: str) -> bool:
    """Return True if this relation is allowed between these node types."""
    return (relation, from_type, to_type) in ALLOWED_RELATIONS


def validate_edge_types(relation: str, from_type: str, to_type: str) -> None:
    validate_relation(relation)
    validate_node_type(from_type)
    validate_node_type(to_type)
    if not is_relation_allowed(relation, from_type, to_type):
        raise SchemaError(
            f"Relation {relation!r} is not allowed from {from_type!r} to {to_type!r}"
        )


def is_valid_id(node_id: str) -> bool:
    """Lore IDs are kebab-case: lowercase letters, digits, and hyphens; no
    leading/trailing hyphen; no double hyphens."""
    if not node_id:
        return False
    if node_id.startswith("-") or node_id.endswith("-"):
        return False
    if "--" in node_id:
        return False
    return all(c.islower() or c.isdigit() or c == "-" for c in node_id)


def validate_id(node_id: str) -> None:
    if not is_valid_id(node_id):
        raise SchemaError(
            f"Invalid id {node_id!r}. Use kebab-case: lowercase letters, digits, "
            f"and single hyphens."
        )
