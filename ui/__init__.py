"""Web UI layer for DUNE: Imperium Uprising.

This package wraps the existing engine (src/) with a thin HTTP API and a
single-page web client. The engine is untouched — this layer only adds:
  - GameSession: holds Game + managers + bots, mirrors SimpleCLI.setup_game()
  - serializer: Game → JSON-safe dict for the frontend
  - api: FastAPI endpoints (added in Phase 2)
"""
