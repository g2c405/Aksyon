import os
import time
import logging
import psutil

logger = logging.getLogger("memory_monitor")


class MemoryUsageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.process = psutil.Process(os.getpid())

    def __call__(self, request):
        start_time = time.time()

        try:
            memory_before = self.process.memory_info().rss / (1024 * 1024)

            response = self.get_response(request)

            memory_after = self.process.memory_info().rss / (1024 * 1024)

            duration = time.time() - start_time

            logger.warning(
                "[MEMORY] PID=%s | %s %s | Status=%s | "
                "Before=%.2fMB | After=%.2fMB | Delta=%.2fMB | "
                "Duration=%.2fs",
                os.getpid(),
                request.method,
                request.path,
                response.status_code,
                memory_before,
                memory_after,
                memory_after - memory_before,
                duration,
            )

            return response

        except Exception:
            logger.exception("[MEMORY] Monitoring middleware encountered an error")
            raise