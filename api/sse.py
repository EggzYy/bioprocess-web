"""
Server-Sent Events (SSE) implementation for real-time progress updates.
"""

import asyncio
import json
import uuid
from typing import Dict, Optional, Any, AsyncGenerator
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """SSE event types."""

    PROGRESS = "progress"
    RESULT = "result"
    ERROR = "error"
    STATUS = "status"
    LOG = "log"
    HEARTBEAT = "heartbeat"


@dataclass
class SSEMessage:
    """Server-Sent Event message."""

    event: EventType
    data: Dict[str, Any]
    id: Optional[str] = None
    retry: Optional[int] = None

    def format(self) -> str:
        """Format message for SSE protocol."""
        lines = []

        if self.id:
            lines.append(f"id: {self.id}")

        lines.append(f"event: {self.event}")

        if self.retry:
            lines.append(f"retry: {self.retry}")

        # Format data as JSON
        data_str = json.dumps(self.data)
        lines.append(f"data: {data_str}")

        # SSE messages end with double newline
        return "\n".join(lines) + "\n\n"


@dataclass
class ProgressTracker:
    """Track progress for a specific operation."""

    operation_id: str
    operation_type: str
    total_steps: int = 100
    current_step: int = 0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)

    @property
    def progress(self) -> float:
        """Calculate progress percentage."""
        if self.total_steps == 0:
            return 0.0
        return min(100.0, (self.current_step / self.total_steps) * 100)

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

    def increment(self, steps: int = 1, message: Optional[str] = None):
        """Increment progress."""
        self.current_step = min(self.total_steps, self.current_step + steps)
        if message:
            self.message = message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "progress": self.progress,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "message": self.message,
            "details": self.details,
            "elapsed_seconds": self.elapsed_seconds,
        }


class SSEManager:
    """Manage SSE connections and progress tracking."""

    def __init__(self):
        self.connections: Dict[str, asyncio.Queue] = {}
        self.progress_trackers: Dict[str, ProgressTracker] = {}
        self._lock = asyncio.Lock()

    async def connect(self, client_id: str) -> asyncio.Queue:
        """Create a new SSE connection."""
        async with self._lock:
            if client_id in self.connections:
                # Close existing connection
                await self.disconnect(client_id)

            queue = asyncio.Queue()
            self.connections[client_id] = queue

            # Send initial connection message
            await self.send_message(
                client_id,
                SSEMessage(
                    event=EventType.STATUS,
                    data={
                        "status": "connected",
                        "client_id": client_id,
                        "timestamp": datetime.now().isoformat(),
                    },
                ),
            )

            return queue

    async def disconnect(self, client_id: str):
        """Close an SSE connection."""
        async with self._lock:
            if client_id in self.connections:
                queue = self.connections[client_id]
                # Send disconnect signal
                await queue.put(None)
                del self.connections[client_id]

            # Clean up any progress trackers for this client
            to_remove = [
                op_id for op_id in self.progress_trackers if op_id.startswith(client_id)
            ]
            for op_id in to_remove:
                del self.progress_trackers[op_id]

    async def send_message(self, client_id: str, message: SSEMessage):
        """Send a message to a specific client."""
        if client_id in self.connections:
            queue = self.connections[client_id]
            await queue.put(message.format())

    async def broadcast(self, message: SSEMessage):
        """Broadcast a message to all connected clients."""
        for client_id in list(self.connections.keys()):
            await self.send_message(client_id, message)

    def create_progress_tracker(
        self, client_id: str, operation_type: str, total_steps: int = 100
    ) -> ProgressTracker:
        """Create a new progress tracker."""
        operation_id = f"{client_id}_{uuid.uuid4().hex[:8]}"
        tracker = ProgressTracker(
            operation_id=operation_id,
            operation_type=operation_type,
            total_steps=total_steps,
        )
        self.progress_trackers[operation_id] = tracker
        return tracker

    async def update_progress(
        self,
        operation_id: str,
        steps: int = 1,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Update progress and send SSE message."""
        if operation_id not in self.progress_trackers:
            return

        tracker = self.progress_trackers[operation_id]
        tracker.increment(steps, message)

        if details:
            tracker.details.update(details)

        # Extract client_id from operation_id
        client_id = operation_id.split("_")[0]

        # Send progress update
        await self.send_message(
            client_id,
            SSEMessage(
                event=EventType.PROGRESS,
                data=tracker.to_dict(),
                id=str(tracker.current_step),
            ),
        )

    async def complete_operation(
        self,
        operation_id: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """Mark operation as complete and send final message."""
        if operation_id not in self.progress_trackers:
            return

        tracker = self.progress_trackers[operation_id]
        client_id = operation_id.split("_")[0]

        if error:
            # Send error message
            await self.send_message(
                client_id,
                SSEMessage(
                    event=EventType.ERROR,
                    data={
                        "operation_id": operation_id,
                        "error": error,
                        "elapsed_seconds": tracker.elapsed_seconds,
                    },
                ),
            )
        else:
            # Set progress to 100%
            tracker.current_step = tracker.total_steps
            tracker.message = "Completed"

            # Send final progress
            await self.send_message(
                client_id,
                SSEMessage(
                    event=EventType.PROGRESS,
                    data=tracker.to_dict(),
                    id=str(tracker.current_step),
                ),
            )

            # Send result if provided
            if result:
                await self.send_message(
                    client_id,
                    SSEMessage(
                        event=EventType.RESULT,
                        data={
                            "operation_id": operation_id,
                            "result": result,
                            "elapsed_seconds": tracker.elapsed_seconds,
                        },
                    ),
                )

        # Clean up tracker
        del self.progress_trackers[operation_id]

    async def send_log(
        self,
        client_id: str,
        level: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Send a log message to client."""
        await self.send_message(
            client_id,
            SSEMessage(
                event=EventType.LOG,
                data={
                    "level": level,
                    "message": message,
                    "details": details or {},
                    "timestamp": datetime.now().isoformat(),
                },
            ),
        )

    async def heartbeat_generator(self, client_id: str, interval: int = 30):
        """Generate heartbeat messages to keep connection alive."""
        while client_id in self.connections:
            await self.send_message(
                client_id,
                SSEMessage(
                    event=EventType.HEARTBEAT,
                    data={"timestamp": datetime.now().isoformat()},
                ),
            )
            await asyncio.sleep(interval)


# Global SSE manager instance
sse_manager = SSEManager()


async def sse_stream(client_id: str) -> AsyncGenerator[str, None]:
    """
    Generate SSE stream for a client.

    Args:
        client_id: Unique client identifier

    Yields:
        SSE formatted messages
    """
    queue = await sse_manager.connect(client_id)

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(sse_manager.heartbeat_generator(client_id))

    try:
        while True:
            # Wait for messages
            message = await queue.get()

            # None signals disconnect
            if message is None:
                break

            yield message

    except asyncio.CancelledError:
        pass
    finally:
        # Clean up
        heartbeat_task.cancel()
        await sse_manager.disconnect(client_id)


# Progress tracking decorators and utilities
def track_progress(operation_type: str, total_steps: int = 100):
    """
    Decorator to track progress of an async function.

    Args:
        operation_type: Type of operation
        total_steps: Total number of steps
    """

    def decorator(func):
        async def wrapper(client_id: str, *args, **kwargs):
            # Create progress tracker
            tracker = sse_manager.create_progress_tracker(
                client_id, operation_type, total_steps
            )

            # Inject tracker into function
            kwargs["progress_tracker"] = tracker
            kwargs["sse_manager"] = sse_manager

            try:
                # Run function
                result = await func(client_id, *args, **kwargs)

                # Mark as complete
                await sse_manager.complete_operation(
                    tracker.operation_id, result=result
                )

                return result

            except Exception as e:
                # Mark as error
                await sse_manager.complete_operation(tracker.operation_id, error=str(e))
                raise

        return wrapper

    return decorator


# Example usage functions
@track_progress("monte_carlo", total_steps=100)
async def run_monte_carlo_with_progress(
    client_id: str,
    scenario_data: Dict[str, Any],
    n_simulations: int = 1000,
    progress_tracker: Optional[ProgressTracker] = None,
    sse_manager: Optional[SSEManager] = None,
    **kwargs,
):
    """
    Run Monte Carlo simulation with progress tracking.

    Args:
        client_id: Client identifier
        scenario_data: Scenario configuration
        n_simulations: Number of simulations
        progress_tracker: Auto-injected progress tracker
        sse_manager: Auto-injected SSE manager
    """
    if not progress_tracker or not sse_manager:
        raise ValueError("Progress tracking not initialized")

    results = []
    batch_size = max(1, n_simulations // 100)

    for i in range(0, n_simulations, batch_size):
        batch_end = min(i + batch_size, n_simulations)

        # Simulate batch processing
        await asyncio.sleep(0.01)  # Simulate work

        # Update progress
        progress = int((batch_end / n_simulations) * 100)
        await sse_manager.update_progress(
            progress_tracker.operation_id,
            steps=progress - progress_tracker.current_step,
            message=f"Processing simulation {batch_end}/{n_simulations}",
            details={
                "current_simulation": batch_end,
                "total_simulations": n_simulations,
            },
        )

        # Add dummy results
        results.extend([{"simulation": j} for j in range(i, batch_end)])

    return {
        "simulations": n_simulations,
        "results": results[:10],  # Return sample
        "statistics": {
            "mean": 50.0,
            "std": 10.0,
            "p10": 35.0,
            "p50": 50.0,
            "p90": 65.0,
        },
    }


@track_progress("optimization", total_steps=100)
async def run_optimization_with_progress(
    client_id: str,
    scenario_data: Dict[str, Any],
    max_iterations: int = 100,
    progress_tracker: Optional[ProgressTracker] = None,
    sse_manager: Optional[SSEManager] = None,
    **kwargs,
):
    """
    Run optimization with progress tracking.

    Args:
        client_id: Client identifier
        scenario_data: Scenario configuration
        max_iterations: Maximum iterations
        progress_tracker: Auto-injected progress tracker
        sse_manager: Auto-injected SSE manager
    """
    if not progress_tracker or not sse_manager:
        raise ValueError("Progress tracking not initialized")

    best_solution = None
    best_score = float("-inf")

    for iteration in range(max_iterations):
        # Simulate optimization step
        await asyncio.sleep(0.01)

        # Generate dummy solution
        score = iteration * 0.1

        if score > best_score:
            best_score = score
            best_solution = {"configuration": f"solution_{iteration}"}

        # Update progress
        await sse_manager.update_progress(
            progress_tracker.operation_id,
            steps=1,
            message=f"Optimization iteration {iteration + 1}/{max_iterations}",
            details={
                "iteration": iteration + 1,
                "best_score": best_score,
                "current_score": score,
            },
        )

    return {
        "iterations": max_iterations,
        "best_solution": best_solution,
        "best_score": best_score,
    }
