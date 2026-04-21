# CLAUDE.md

Working guide for Claude Code. See @README.md for repository structure, ID naming conventions, and commit message format.

## Workflows

### Adding equipment

1. Confirm model number and purchase info
2. Fetch specs via web search (prefer manufacturer's official source)
3. Append to the appropriate `inventory/*.yaml` (assign next ID from existing sequence)
4. Update connections in `topology/system_diagram.mmd`
5. Update `topology/physical_layout.mmd` if needed

### Changing connections

1. Update `connection` in `inventory/cables.yaml`
2. Update edges in `topology/system_diagram.mmd`
3. If adding a new cable, add an entry to `cables.yaml`

### Changing insulators

1. Update the entry in `inventory/accessories.yaml`
2. Update the stack structure in `topology/physical_layout.mmd`
3. `placement.layer` counts from the top (`1` = directly under the equipment)

## Regenerating Mermaid diagrams

After editing `.mmd`, regenerate the png:

```bash
mmdc -i topology/system_diagram.mmd -o topology/system_diagram.png -s 3 -b transparent
mmdc -i topology/physical_layout.mmd -o topology/physical_layout.png -s 3 -b transparent
```

## YAML conventions

- Prices in JPY
- Use `null` for unknown values
- Used purchases: set `purchased_date` to null or the purchase date, and note "中古購入" in `notes`
