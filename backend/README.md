# Backend (legacy path)

The backend has moved to the **`emberforge`** Python package at the project root.

## Use this instead

```bash
pip install -e ".[dev,mac]"
emberforge check
emberforge serve
```

Or:

```bash
python -m emberforge serve
```

## Compatibility

`backend/main.py` still re-exports the app for older commands:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

New development should use `emberforge serve`. See `docs/RELEASE_1.0.md`.