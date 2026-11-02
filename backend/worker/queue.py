"""
Redis-backed job queue (via RQ) used to hand a transaction off for
asynchronous multi-hop settlement, instead of blocking the API request
on the whole bank -> PSP -> aggregator chain.
"""

from redis import Redis
from rq import Queue

from config import REDIS_URL, SETTLEMENT_QUEUE_NAME

redis_conn = Redis.from_url(REDIS_URL)
settlement_queue = Queue(SETTLEMENT_QUEUE_NAME, connection=redis_conn)
