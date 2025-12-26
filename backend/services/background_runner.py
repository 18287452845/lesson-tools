"""
Background task runner for executing async tasks in separate threads.
"""
import asyncio
import threading
import logging
from typing import Coroutine, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class BackgroundTaskRunner:
    """
    Run async tasks in background threads without blocking the main application.

    This is a simple alternative to Celery/Redis for background processing.
    Each task runs in its own thread with its own event loop.
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

        # Create and start the thread
        thread = threading.Thread(
            target=run_in_thread,
            name=name or "BackgroundTask",
            daemon=True  # Thread will not prevent program exit
        )
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


# Convenience alias
run_in_background = BackgroundTaskRunner.run_async_task
