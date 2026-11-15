import time
import logging

logger = logging.getLogger(__name__)

def execute_with_retry(rag_func, *args, max_retries=3, delay=2, **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            return rag_func(*args, **kwargs)
        except Exception as e:
            err_msg = str(e)
            is_transient = any(c in err_msg for c in ["502", "503", "500", "timeout", "RateLimit", "inference failed"])
            if is_transient and attempt < max_retries:
                logger.warning(f"Temporary failure retray again in seconds...{attempt}/{max_retries}: {err_msg}{delay}")
                time.sleep(delay)
                delay *= 2
                continue
            raise e