import os
import time
import json
import redis
from pymongo import MongoClient, InsertOne
from pymongo.write_concern import WriteConcern

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/assessmentdb")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

WRITE_QUEUE_KEY = "write_queue"
BATCH_MAX = int(os.getenv("BATCH_MAX", "100"))
BATCH_FLUSH_MS = int(os.getenv("BATCH_FLUSH_MS", "75"))

def run_worker():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    client = MongoClient(
        MONGO_URI,
        maxPoolSize=20,
        serverSelectionTimeoutMS=300,
        connectTimeoutMS=300,
        socketTimeoutMS=500,
        waitQueueTimeoutMS=300,
        retryWrites=False,
    )

    col = client["assessmentdb"].get_collection(
        "records",
        write_concern=WriteConcern(w=1, j=False),
    )

    print("Worker started")

    batch = []
    last_flush = time.time()

    while True:
        item = r.brpop(WRITE_QUEUE_KEY, timeout=1)
        now = time.time()

        if item:
            _, payload = item
            try:
                doc = json.loads(payload)
                batch.append(InsertOne(doc))
            except:
                pass

        time_due = (now - last_flush) * 1000 >= BATCH_FLUSH_MS
        size_due = len(batch) >= BATCH_MAX

        if batch and (time_due or size_due):
            try:
                col.bulk_write(batch, ordered=False)
                print(f"Flushed {len(batch)} writes")
            except Exception as e:
                print("Bulk error:", e)
                time.sleep(0.05)

            batch = []
            last_flush = time.time()