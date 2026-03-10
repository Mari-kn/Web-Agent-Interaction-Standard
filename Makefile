.PHONY: install test platform store mcp lint

install:
	pip install -e ".[dev,platform,store,mcp]"

test:
	python -m pytest tests/ -v

platform:
	uvicorn pod_platform.app:app --port 8000 --reload

store:
	uvicorn demo_store.app:app --port 8001 --reload

mcp:
	python -m mcp_server.server

lint:
	ruff check .
