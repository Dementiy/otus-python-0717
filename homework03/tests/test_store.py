import unittest
from unittest.mock import patch, MagicMock
import fakeredis

import store


class TestStore(unittest.TestCase):

    @patch("redis.StrictRedis", fakeredis.FakeStrictRedis)
    def test_get_raises_on_connection_error(self):
        redis_storage = store.RedisStorage()
        redis_storage.db.connected = False
        storage = store.Storage(redis_storage)
        with self.assertRaises(ConnectionError):
            storage.get("key")
    
    @patch("redis.StrictRedis", fakeredis.FakeStrictRedis)
    def test_not_raises_on_connection_error(self):
        redis_storage = store.RedisStorage()
        redis_storage.db.connected = False
        storage = store.Storage(redis_storage)
        self.assertEqual(storage.cache_get("key"), None)
        self.assertEqual(storage.cache_set("key", "value"), None)

    @patch("redis.StrictRedis", fakeredis.FakeStrictRedis)
    def test_retry_on_connection_error(self):
        redis_storage = store.RedisStorage()
        redis_storage.db.connected = False
        redis_storage.db.get = MagicMock(side_effect=ConnectionError())
        redis_storage.db.set = MagicMock(side_effect=ConnectionError())
        
        storage = store.Storage(redis_storage)
        self.assertEqual(storage.cache_get("key"), None)
        self.assertEqual(storage.cache_set("key", "value"), None)
        self.assertEqual(redis_storage.db.get.call_count, store.Storage.MAX_RETRIES)
        self.assertEqual(redis_storage.db.set.call_count, store.Storage.MAX_RETRIES)


if __name__ == "__main__":
    unittest.main()