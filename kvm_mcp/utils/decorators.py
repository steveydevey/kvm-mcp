import time
import logging
from functools import wraps

logger = logging.getLogger('kvm_mcp')

def timing_decorator(func):
    """Decorator for timing async methods"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            return await func(*args, **kwargs)
        finally:
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} took {elapsed:.4f} seconds")
    return wrapper 