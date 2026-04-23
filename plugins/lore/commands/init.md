---
description: Bootstrap the Lore graph for this project. Creates .lore/lore.db and seeds the top-level modules by asking the user.
allowed-tools: [Bash, Read]
---

Bootstrap Lore in the current directory. The "project" may be a single
repo *or* a workspace containing several repos/packages — Lore has no
opinion, it captures whatever unit of knowledge the user wants to audit.
The graph lives in `.lore/lore.db` relative to wherever Claude Code was
launched.

## Steps

1. **Create DB.** Run `lore init` to create `.lore/lore.db` if it does
   not exist.

2. **Gather modules.** Ask the user for the top-level **modules** of this
   project (3–10 short kebab-case names — e.g. `auth`, `billing`,
   `notifications`). In a multi-repo workspace, each repo or major
   package is usually a module. Once the user approves the list,
   **remember the exact count** — call it N.

3. **Persist in one batch.** Call `lore_add_nodes(nodes=[...])` with all
   modules in a single call. Each node must include full provenance in
   `metadata`:
   - `source`: `"user_stated"`
   - `confidence`: `"high"`
   - `source_context`: `"init <today ISO date>"`
   - `last_verified_at`: `"<today ISO date>"`

4. **Mandatory verification — do NOT skip this.** Do not report success
   before completing this step. Hallucinating a success message without
   verifying is the most common failure mode of this command.

   a. Call `lore_list(type="module")`.
   b. Count the returned nodes — call it M.
   c. Compare M to N (the count from step 2).
   d. Report exactly one of two outcomes:

      - **If M == N**: "Sembrados N módulos. Verificado con `lore_list`:
        M nodos tipo module presentes en la DB."
      - **If M != N**: "FAILURE: pedí sembrar N módulos pero
        `lore_list(type='module')` solo encuentra M. Las escrituras no
        persistieron." Stop. Do not retry silently.

5. **Audit.** Call `lore_audit()` and report orphans/cycles/hygiene. A
   clean seed will show the N modules as orphans (no edges yet); that is
   expected — say so explicitly.

## What to do if verification fails

Do not retry add_nodes silently. Surface the failure, let the user
investigate. Common causes: MCP server pointing at the wrong DB
(check stderr), tool call error that was not propagated, schema
mismatch.
