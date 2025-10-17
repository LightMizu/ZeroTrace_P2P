import time
from collections import OrderedDict
from typing import Iterator, Tuple


class ForgetfulStorage:
    def __init__(self, ttl: int = 604800):
        self.data = OrderedDict()
        self.ttl = ttl

    def __setitem__(self, key: bytes, value):
        if key in self.data:
            del self.data[key]
        self.data[key] = (time.monotonic(), value)
        self.cull()

    def __getitem__(self, key: bytes):
        self.cull()
        return self.data[key][1]

    def get(self, key: bytes, default=None):
        self.cull()
        return self.data.get(key, (None, default))[1]

    def cull(self):
        min_time = time.monotonic() - self.ttl
        keys_to_delete = [k for k, (t, _) in self.data.items() if t < min_time]
        for k in keys_to_delete:
            del self.data[k]

    def iter_older_than(self, seconds_old: int) -> Iterator[Tuple[bytes, object]]:
        min_birthday = time.monotonic() - seconds_old
        return ((k, v[1]) for k, (t, v) in list(self.data.items()) if t < min_birthday)

    def __iter__(self):
        self.cull()
        return ((k, v[1]) for k, (t, v) in self.data.items())
