from src.kademlia.kademlia.storage import ForgetfulStorage
import time


def test_forgetful_storage_set_get_cull():
    s = ForgetfulStorage(ttl=1)
    key = b'a'
    s[key] = b'1'
    assert s.get(key) == b'1'
    # wait for TTL
    time.sleep(1.1)
    assert s.get(key) is None


def test_iter_older_than():
    s = ForgetfulStorage(ttl=1000)
    s[b'k1'] = b'v1'
    s[b'k2'] = b'v2'
    # nothing older than huge age
    assert list(s.iter_older_than(0)) == []
