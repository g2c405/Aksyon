import os
import time
import logging
import threading
import psutil

logger = logging.getLogger("memory_monitor")

_active_requests = 0
_max_active_requests = 0
_request_lock = threading.Lock()


class MemoryUsageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.process = psutil.Process(os.getpid())

    def __call__(self, request):
        global _active_requests, _max_active_requests

        start_time = time.time()

        with _request_lock:
            _active_requests += 1
            concurrent_start = _active_requests

            _max_active_requests = max(
                _max_active_requests,
                _active_requests,
            )

            max_concurrent = _max_active_requests

        memory_before = self.process.memory_info().rss / (1024 * 1024)
        peak_memory = memory_before

        stop_sampling = threading.Event()

        def sample_memory():
            nonlocal peak_memory

            while not stop_sampling.wait(0.1):
                try:
                    current = (
                        self.process.memory_info().rss / (1024 * 1024)
                    )
                    peak_memory = max(peak_memory, current)
                except Exception:
                    break

        sampler = threading.Thread(
            target=sample_memory,
            daemon=True,
        )
        sampler.start()

        response = None

        try:
            response = self.get_response(request)
            return response

        finally:
            stop_sampling.set()
            sampler.join(timeout=1)

            try:
                memory_after = (
                    self.process.memory_info().rss / (1024 * 1024)
                )
                peak_memory = max(peak_memory, memory_after)
            except Exception:
                memory_after = memory_before

            duration = time.time() - start_time

            with _request_lock:
                concurrent_end = _active_requests
                _active_requests -= 1

            logger.warning(
                "[MEMORY] PID=%s | %s %s | Status=%s | "
                "Before=%.2fMB | After=%.2fMB | "
                "Peak=%.2fMB | Delta=%.2fMB | "
                "Duration=%.2fs | ConcurrentStart=%s | "
                "ConcurrentEnd=%s | MaxConcurrent=%s",
                os.getpid(),
                request.method,
                request.path,
                response.status_code if response else "ERROR",
                memory_before,
                memory_after,
                peak_memory,
                memory_after - memory_before,
                duration,
                concurrent_start,
                concurrent_end,
                max_concurrent,
            )