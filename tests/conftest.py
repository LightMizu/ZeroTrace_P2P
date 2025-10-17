import pytest

# Tests run with 'src' on sys.path, import modules the same way tests do.
from src.zerotrace.kademlia import server as kad_server
from src.zerotrace.kademlia import logging as zlogging


@pytest.fixture(autouse=True)
def isolate_global_state():
    """Ensure global state doesn't leak between tests.

    - Clear the in-process `_app_cache` registry which `create_app` populates.
    - Reset the package-level default_logger so printed_groups / thread-local
      state doesn't persist across tests.
    """
    # clear before test
    try:
        kad_server._app_cache.clear()
    except Exception:
        pass
    try:
        zlogging.default_logger = None
    except Exception:
        pass

    yield

    # clear after test as well
    try:
        kad_server._app_cache.clear()
    except Exception:
        pass
    try:
        zlogging.default_logger = None
    except Exception:
        pass
