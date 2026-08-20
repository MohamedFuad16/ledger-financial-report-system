# Conventions

- Python modules stay at the project root until a package extraction is justified; use `snake_case` and standard-library → third-party → local imports.
- React source belongs in `frontend/src`; reusable UI in `frontend/src/components`, API/state utilities in `frontend/src/lib`, and route-level views in `frontend/src/pages`.
- Component files use `PascalCase.tsx`; TypeScript utilities use `camelCase` exports.
- Static production output is generated, never hand-edited.
- Tests live beside React source as `*.test.tsx` and in root `test_*.py` for Python.
- Keep provider secrets out of source, logs, run artifacts, and agent docs.
- Preserve the fixed schema order; mapping/repair belongs in `normalize.py`, validation in `models.py`, and scoring in `pipeline.py`.
- Never silently repair model output: report every normalization.
