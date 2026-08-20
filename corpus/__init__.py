"""Firecrawl-backed Annual Report corpus builder.

Discovery is intentionally separate from the extraction pipeline. A corpus is
downloaded, screened, and pinned in a manifest before it becomes benchmark
input.
"""

from .service import build_corpus

__all__ = ["build_corpus"]
