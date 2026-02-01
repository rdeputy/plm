# PLM - Product Lifecycle Management

Construction-focused PLM system serving as the single source of truth for design data, versioning, and change management.

## Features

- **Parts Management**: Track materials, components, assemblies, and products
- **BOMs**: Hierarchical bills of materials with effectivity
- **Change Orders (ECO)**: Engineering change management with approval workflows
- **Configuration Management**: Product variants and options
- **Inventory**: Stock tracking with demand planning
- **Procurement**: Purchase orders and vendor management
- **MRP**: Material Requirements Planning engine

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
```

## Database Setup

```bash
# Run migrations
alembic upgrade head
```

## Running the API

```bash
uvicorn plm.api.app:app --reload
```

## Integration

PLM integrates with the orchestrator ecosystem:
- **Rhino.Compute**: 3D model sync and BOM extraction
- **ARC-Review**: Compliance checking for change orders
- **Trades-Agents**: Cost roll-ups and estimating
- **HCT**: Schedule impact analysis
