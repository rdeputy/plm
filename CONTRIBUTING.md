# Contributing to PLM

Thank you for your interest in contributing!

## Development Setup

### Backend

```bash
# Clone the repository
git clone https://github.com/rdeputy/plm.git
cd plm

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Start the API
uvicorn src.plm.api.app:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Code Style

### Python
- Use `ruff` for linting: `ruff check src/ tests/`
- Use `mypy` for type checking: `mypy src/plm`
- Follow PEP 8 conventions
- Use type hints for function signatures

### TypeScript/React
- Use ESLint: `npm run lint`
- Use TypeScript strict mode
- Follow React best practices (hooks, functional components)

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `pytest tests/` and `npm run build`
5. Commit with descriptive messages
6. Push and open a Pull Request

## Commit Messages

Use clear, descriptive commit messages:
- `feat: Add new requirement type validation`
- `fix: Correct BOM item quantity calculation`
- `docs: Update API documentation`
- `refactor: Simplify part release workflow`

## Testing

- Write tests for new features
- Maintain or improve test coverage
- Use pytest fixtures for database tests
- Test both success and error paths

## Questions?

Open an issue for questions or discussion.
