"""Vercel Python runtime entrypoint."""
# Vercel's serverless Python runtime calls asyncio.run with a `loop_factory`
# kwarg (Python 3.12+). FinMind imports `nest_asyncio` and calls
# `nest_asyncio.apply()` at module load, which monkey-patches `asyncio.run`
# to a signature that does NOT accept `loop_factory`, causing
# FUNCTION_INVOCATION_FAILED on cold start. Setting this sentinel makes
# `nest_asyncio.apply()` a no-op — it checks `hasattr(asyncio, '_nest_patched')`
# and returns early — so the original `asyncio.run` is preserved.
import asyncio as _asyncio
_asyncio._nest_patched = True

from main import app

