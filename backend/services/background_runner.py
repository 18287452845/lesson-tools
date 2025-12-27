"""
Background task runner for executing async tasks in separate threads.
"""
import asyncio
import threading
import logging
import atexit
import signal
from typing import Coroutine, Optional, Dict, Set
from functools import wraps
from weakref import WeakSet

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manages background tasks with graceful shutdown support.

    Tracks all running tasks and ensures they complete before program exit.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._active_threads: Set[threading.Thread] = set()
        self._threads_lock = threading.Lock()
        self._shutdown_requested = False

        # Register cleanup on exit
        atexit.register(self.shutdown)

    def register_thread(self, thread: threading.Thread) -> None:
        """Register a thread for tracking."""
        with self._threads_lock:
            self._active_threads.add(thread)

    def unregister_thread(self, thread: threading.Thread) -> None:
        """Unregister a thread after completion."""
        with self._threads_lock:
            self._active_threads.discard(thread)

    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested

    def shutdown(self, timeout: float = 30.0) -> None:
        """
        Wait for all background tasks to complete.

        Args:
            timeout: Maximum time to wait for each thread (in seconds)
        """
        self._shutdown_requested = True

        with self._threads_lock:
            threads_to_wait = list(self._active_threads)

        if not threads_to_wait:
            return

        logger.info(f"Waiting for {len(threads_to_wait)} background tasks to complete...")

        for thread in threads_to_wait:
            if thread.is_alive():
                logger.debug(f"Waiting for thread '{thread.name}' to complete...")
                thread.join(timeout=timeout)
                if thread.is_alive():
                    logger.warning(f"Thread '{thread.name}' did not complete within {timeout}s timeout")

        logger.info("All background tasks completed or timed out")


# Global task manager instance
_task_manager = BackgroundTaskManager()


class BackgroundTaskRunner:
    """
    Run async tasks in background threads without blocking the main application.

    This is a simple alternative to Celery/Redis for background processing.
    Each task runs in its own thread with its own event loop.

    Features:
    - Graceful shutdown support
    - Task tracking
    - Error handling with callbacks
    """

    @staticmethod
    def run_async_task(
        coro: Coroutine,
        name: Optional[str] = None,
        on_error: Optional[callable] = None,
    ) -> threading.Thread:
        """
        Run a coroutine in a new background thread with its own event loop.

        Args:
            coro: The coroutine to run
            name: Optional name for the thread (for debugging)
            on_error: Optional error handler function(exception)

        Returns:
            The thread object (already started)

        Example:
            ```python
            async def my_task(param1, param2):
                # Do async work
                await some_async_function()

            # Start the task in background
            thread = BackgroundTaskRunner.run_async_task(
                my_task("value1", "value2"),
                name="my-background-task"
            )
            ```
        """
        def run_in_thread():
            """Inner function that runs in the background thread."""
            current_thread = threading.current_thread()

            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Run the coroutine until completion
                loop.run_until_complete(coro)
                if name:
                    logger.info(f"Background task '{name}' completed successfully")
            except Exception as e:
                logger.error(
                    f"Background task '{name or 'unnamed'}' failed: {str(e)}",
                    exc_info=True
                )
                if on_error:
                    try:
                        on_error(e)
                    except Exception as handler_error:
                        logger.error(
                            f"Error handler for task '{name}' failed: {str(handler_error)}",
                            exc_info=True
                        )
            finally:
                # Clean up the event loop
                loop.close()
                if name:
                    logger.debug(f"Background task '{name}' event loop closed")
                # Unregister thread
                _task_manager.unregister_thread(current_thread)

        # Create the thread (non-daemon for graceful shutdown)
        thread = threading.Thread(
            target=run_in_thread,
            name=name or "BackgroundTask",
            daemon=False  # Allow graceful shutdown
        )

        # Register thread for tracking
        _task_manager.register_thread(thread)

        # Start the thread
        thread.start()

        if name:
            logger.info(f"Started background task '{name}' in thread {thread.name}")

        return thread

    @staticmethod
    def run_async_function(name: Optional[str] = None):
        """
        Decorator to easily run an async function in background.

        Example:
            ```python
            @BackgroundTaskRunner.run_async_function(name="process-batch")
            async def process_batch_task(task_id):
                # This will automatically run in background
                await do_processing(task_id)

            # Usage (returns thread immediately):
            thread = process_batch_task(task_id="123")
            ```
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                coro = func(*args, **kwargs)
                return BackgroundTaskRunner.run_async_task(coro, name=name)
            return wrapper
        return decorator

    @staticmethod
    def is_shutdown_requested() -> bool:
        """Check if shutdown has been requested."""
        return _task_manager.is_shutdown_requested()


# Convenience aliases
run_in_background = BackgroundTaskRunner.run_async_task
get_task_manager = lambda: _task_manager
