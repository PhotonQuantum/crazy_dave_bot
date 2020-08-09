import json
import time
from asyncio import Lock

from asyncoss import Auth, Bucket


class Uploader:
    def __init__(self, auth: tuple, endpoint: str, bucket: str):
        self._auth = Auth(*auth)
        self._endpoint = endpoint
        self._bucket = bucket
        self._ts = int(time.time())
        self._lock = Lock()

    async def upload(self, chat_history: dict):
        async with self._lock:
            async with Bucket(self._auth, self._endpoint, self._bucket) as bucket:
                await bucket.put_object(f"dataset_v2/{self._ts}.json", json.dumps(chat_history))
