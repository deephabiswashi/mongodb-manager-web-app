# utils/mongo_utils.py
from pymongo import MongoClient
from bson.objectid import ObjectId
from typing import List, Tuple, Dict, Any, Optional

# single client per process
def get_mongo_client(uri: str = "mongodb://localhost:27017/") -> MongoClient:
    """
    Returns a pymongo MongoClient. Keep a single client object per process.
    """
    client = MongoClient(uri)
    return client


# -------------------------
# Database helpers
# -------------------------
def list_databases(client: MongoClient) -> List[str]:
    """
    Returns a list of database names from the client, excluding internal ones.
    """
    raw = client.list_database_names()
    # filter out local DB that you usually don't want to show
    filtered = [name for name in raw if name not in ("local",)]
    return filtered


def create_database(client: MongoClient, name: str) -> bool:
    """
    Ensures a database exists by creating a small placeholder collection/document.
    Returns True on success.
    """
    db = client[name]
    # Insert a tiny document into a sentinel collection to force creation,
    # then leave it (so user can see DB in Compass). If you prefer removing it,
    # uncomment the drop_collection line.
    coll = db["_init_collection"]
    res = coll.insert_one({"_init": True})
    # Optionally remove the placeholder collection to keep DB empty:
    # coll.delete_one({"_id": res.inserted_id})
    # db.drop_collection("_init_collection")
    return True


# -------------------------
# Collection helpers
# -------------------------
def list_collections(client: MongoClient, db_name: str) -> List[str]:
    """Return collections for a database"""
    return client[db_name].list_collection_names()


def create_collection(client: MongoClient, db_name: str, collection_name: str) -> bool:
    """Create a new collection if it doesn't exist"""
    db = client[db_name]
    if collection_name in db.list_collection_names():
        return False
    db.create_collection(collection_name)
    return True


def drop_collection(client: MongoClient, db_name: str, collection_name: str) -> bool:
    """Drop a collection"""
    db = client[db_name]
    if collection_name in db.list_collection_names():
        db.drop_collection(collection_name)
        return True
    return False


# -------------------------
# Document helpers (CRUD)
# -------------------------
def _maybe_convert_id_in_query(query: Dict[str, Any]) -> Dict[str, Any]:
    """
    If query contains '_id' as a string, convert it to ObjectId for pymongo.
    Works in place but returns the converted dict.
    """
    if not query:
        return query
    q = dict(query)  # shallow copy
    _id = q.get("_id")
    if isinstance(_id, str):
        try:
            q["_id"] = ObjectId(_id)
        except Exception:
            # leave as-is if not a valid ObjectId
            pass
    return q


def insert_documents(client: MongoClient, db_name: str, collection_name: str, records: List[Dict[str, Any]]) -> int:
    """Insert multiple documents into the specified collection. Returns number inserted."""
    if not records:
        return 0
    db = client[db_name]
    coll = db[collection_name]
    res = coll.insert_many(records)
    return len(res.inserted_ids)


def insert_document(client: MongoClient, db_name: str, collection_name: str, record: Dict[str, Any]) -> str:
    """Insert single document and return its inserted_id as string."""
    db = client[db_name]
    coll = db[collection_name]
    res = coll.insert_one(record)
    return str(res.inserted_id)


def get_documents(client: MongoClient, db_name: str, collection_name: str, limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch documents for display. By default excludes nothing; converts _id to string.
    Accepts skip and limit for simple pagination.
    """
    cursor = client[db_name][collection_name].find().skip(skip).limit(limit)
    docs = []
    for d in cursor:
        # convert _id to string for safe JSON rendering
        d["_id"] = str(d.get("_id"))
        docs.append(d)
    return docs


def get_documents_with_count(client: MongoClient, db_name: str, collection_name: str, limit: int = 50, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]:
    """
    Returns (docs, total_count) to support pagination in UI.
    """
    coll = client[db_name][collection_name]
    total = coll.count_documents({})
    docs = get_documents(client, db_name, collection_name, limit=limit, skip=skip)
    return docs, total


def get_documents_no_id_excluded(client: MongoClient, db_name: str, collection_name: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Backwards-compatible variant to match your earlier API that excluded _id.
    (Returns documents without the _id field.)
    """
    docs = list(client[db_name][collection_name].find({}, {"_id": 0}).limit(limit))
    return docs


def update_document(client: MongoClient, db_name: str, collection_name: str, query: Dict[str, Any], new_values: Dict[str, Any]) -> int:
    """
    Update a single document matching query. Query may contain string '_id' which will be converted.
    Returns number of modified documents.
    """
    q = _maybe_convert_id_in_query(query)
    res = client[db_name][collection_name].update_one(q, {"$set": new_values})
    return res.modified_count


def update_document_by_id(client: MongoClient, db_name: str, collection_name: str, doc_id: str, new_values: Dict[str, Any]) -> int:
    """
    Update by document id (string). Returns modified_count.
    """
    try:
        oid = ObjectId(doc_id)
    except Exception:
        return 0
    res = client[db_name][collection_name].update_one({"_id": oid}, {"$set": new_values})
    return res.modified_count


def delete_document(client: MongoClient, db_name: str, collection_name: str, query: Dict[str, Any]) -> int:
    """
    Delete a single document matching query. If query contains string '_id', it will be converted.
    Returns number of deleted documents.
    """
    q = _maybe_convert_id_in_query(query)
    res = client[db_name][collection_name].delete_one(q)
    return res.deleted_count


def delete_document_by_id(client: MongoClient, db_name: str, collection_name: str, doc_id: str) -> int:
    """Delete by document id (string). Returns deleted_count."""
    try:
        oid = ObjectId(doc_id)
    except Exception:
        return 0
    res = client[db_name][collection_name].delete_one({"_id": oid})
    return res.deleted_count


# -------------------------
# Counting & utilities
# -------------------------
def count_documents(client: MongoClient, db_name: str, collection_name: str) -> int:
    """Return number of documents in a collection."""
    return client[db_name][collection_name].count_documents({})


# -------------------------
# Backwards-compat / aliases
# -------------------------
# Keep the old function names working (your app imports these names).
# - list_collections already exists above.
# - get_documents (older signature) is preserved but now supports skip/limit.
# - insert_documents replaced with improved variant above but same name.
# - update_document, delete_document preserved.
# - create_database preserved.
# If you prefer different names in your routes, you can call these helpers accordingly.
