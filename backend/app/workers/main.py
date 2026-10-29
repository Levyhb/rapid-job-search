import sys

from redis import Redis
from rq import Queue, SimpleWorker, Worker

from app.core.config import get_settings


def main():
    with Redis.from_url(get_settings().redis_url) as connection:
        queue = Queue("searches", connection=connection, default_timeout=600)
        worker_class = SimpleWorker if sys.platform == "win32" else Worker
        worker_class([queue], connection=connection).work()


if __name__ == "__main__":
    main()
