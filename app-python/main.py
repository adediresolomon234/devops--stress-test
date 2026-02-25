import os
import random
import string
import json
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import redis

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/assessmentdb")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379").split(":")[-1])

CACHE_KEY = "cache:records"
WRITE_QUEUE_KEY = "write_queue"
CACHE_TTL = 30  # seconds

app = FastAPI(title="DevOps Assessment API", version="1.0.0")

# --- Mongo (bounded pool) ---
client = MongoClient(
    MONGO_URI,
    maxPoolSize=20,
    minPoolSize=5,
    serverSelectionTimeoutMS=500,
    connectTimeoutMS=500,
    socketTimeoutMS=1500,
)

db = client["assessmentdb"]
collection = db["records"]

# --- Redis ---
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def random_payload(size: int = 512) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=size))


@app.get("/healthz")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/readyz")
def readiness_check():
    try:
        r.ping()
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

# --- Cache refill (max ONE Mongo query) ---
def refill_cache():
    try:
        docs = collection.find({}, {"_id": 1}).sort("_id", -1).limit(50)
        ids = [str(d["_id"]) for d in docs]
        r.setex(CACHE_KEY, CACHE_TTL, json.dumps(ids))
        return ids
    except PyMongoError:
        return []

@app.get("/api/data")
def process_data():
    reads = []
    writes = []

    # ---- READS (Redis-backed) ----
    try:
        cached = r.get(CACHE_KEY)
        if cached:
            ids = json.loads(cached)
        else:
            ids = refill_cache()
    except Exception:
        ids = []

    # 5 reads (must keep loop)
    for i in range(5):
        if ids:
            reads.append(ids[i % len(ids)])
        else:
            reads.append(None)

    # ---- WRITES (enqueue only) ----
    for i in range(5):
        new_doc = {
            "type": "write",
            "index": i,
            "payload": random_payload(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            r.lpush(WRITE_QUEUE_KEY, json.dumps(new_doc))
        except Exception:
            pass

        writes.append("queued")

    return JSONResponse(content={
        "status": "success",
        "reads": reads,
        "writes": writes,
        "timestamp": datetime.utcnow().isoformat(),
    })


@app.get("/api/stats")
def get_stats():
    try:
        return {
            "total_documents": collection.estimated_document_count(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail=str(exc))