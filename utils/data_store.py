"""
Data store module for Amazon FBA Agent System.
Provides MongoDB interface for persistent data storage.
"""
from typing import Any, Dict
try:
    import pymongo
except ModuleNotFoundError:         # allow tests to monkey-patch
    pymongo = None                  # pragma: no cover


class MongoDataStore:
    """Thin wrapper; real implementation will be fleshed out later."""
    def __init__(self, uri: str = "mongodb://localhost:27017", db_name: str = "fba"):
        if pymongo is None:
            raise ImportError("pymongo not installed")
        self.client = pymongo.MongoClient(uri)
        self.db = self.client[db_name]

    # example API used by tests
    def insert_one(self, collection: str, doc: Dict[str, Any]):
        return self.db[collection].insert_one(doc)
