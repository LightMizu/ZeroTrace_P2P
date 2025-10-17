from zerotrace.kademlia.logging import init_logger, default_logger

# Initialize a default logger without node id; individual modules may re-init with the real id
init_logger(None)

__all__ = ["init_logger", "default_logger"]

