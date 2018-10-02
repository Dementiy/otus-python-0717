import redis
import functools
import time


def retry(exceptions, tries=3, backoff_factor=0.3):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            for attempt in range(tries):
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    delay = backoff_factor * (2 ** attempt)
                    time.sleep(delay)
        return wrapper
    return decorator


class RedisStorage:

    def __init__(self, host="localhost", port=6379, timeout=3):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.db = None
        self.reconnect()

    def reconnect(self):
        self.db = redis.StrictRedis(
            host=self.host,
            port=self.port,
            db=0,
            socket_timeout=self.timeout,
            socket_connect_timeout=self.timeout,
            decode_responses=True
        )
    
    def get(self, key):
        try:
            return self.db.get(key)
        except redis.exceptions.TimeoutError:
            raise TimeoutError
        except redis.exceptions.ConnectionError:
            raise ConnectionError
    
    def set(self, key, value, expires=None):
        try:
            return self.db.set(key, value, ex=expires)
        except redis.exceptions.TimeoutError:
            raise TimeoutError
        except redis.exceptions.ConnectionError:
            raise ConnectionError


class Storage:
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 0.3

    def __init__(self, storage):
        self.storage = storage
    
    def get(self, key):
        return self.storage.get(key)

    @retry((TimeoutError, ConnectionError), MAX_RETRIES, BACKOFF_FACTOR)
    def cache_get(self, key):
        return self.storage.get(key)

    @retry((TimeoutError, ConnectionError), MAX_RETRIES, BACKOFF_FACTOR)
    def cache_set(self, key, value, expires=None):
        return self.storage.set(key, value, expires=expires)