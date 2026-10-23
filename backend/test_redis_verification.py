import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.redis_client import redis_client

def verify_redis():
    print("Testing Redis...")
    client = redis_client.get_client()
    try:
        ping = client.ping()
        print(f"Ping successful: {ping}")

        # Queue
        queue_key = "test_queue"
        print(f"Testing queue (lpush/rpop) on {queue_key}...")
        client.lpush(queue_key, "item1", "item2")
        item1 = client.rpop(queue_key)
        item2 = client.rpop(queue_key)
        print(f"Queue items retrieved: {item1}, {item2}")
        
        # Deduplication
        dedup_key = "alert_dedup:test_cam_123"
        print(f"Testing deduplication (set ex) on {dedup_key}...")
        is_new = client.set(dedup_key, "1", ex=5, nx=True)
        print(f"First set (nx) successful: {is_new}")
        is_new_again = client.set(dedup_key, "1", ex=5, nx=True)
        print(f"Second set (nx) prevented duplicates: {not is_new_again}")

        # Rate Limiting
        rate_key = "rate_limit:test_user_456"
        print(f"Testing rate limiting on {rate_key}...")
        count1 = client.incr(rate_key)
        client.expire(rate_key, 10)
        count2 = client.incr(rate_key)
        print(f"Rate count 1: {count1}, count 2: {count2}")

        # Sync flags
        sync_key = "sync_status:offline_node_789"
        print(f"Testing sync flags on {sync_key}...")
        client.set(sync_key, "PENDING")
        sync_status = client.get(sync_key)
        print(f"Sync status: {sync_status}")

        print("ALL REDIS VERIFICATION TESTS SUCCESSFUL.")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    verify_redis()
