"""Scraper adapters: site-specific implementations of the ``Scraper`` interface.

Scrapers only fetch metadata + image bytes from upstream sites; the
ingestion/materialization orchestration lives in ``app/services/scrape.py``
so adapters stay free of DB and FastAPI concerns.
"""
from app.scrapers.base import Scraper, ScrapedPost, ScrapedTag

__all__ = ["Scraper", "ScrapedPost", "ScrapedTag"]
