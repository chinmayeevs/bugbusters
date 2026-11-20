"""
backend/graphql/subscriptions.py
Strawberry GraphQL Subscriptions for real-time WebSocket incident and pipeline updates.
"""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
import strawberry
from typing import AsyncGenerator, Optional
from backend.graphql.schema import IncidentType, PipelineStatusUpdateType
from backend.storage.incident_repository import IncidentRepository
from backend.graphql.queries import incident_to_graphql

incident_repo = IncidentRepository()

# Global event queue for in-memory WebSocket event broadcasts
PIPELINE_EVENT_QUEUE: asyncio.Queue = asyncio.Queue()


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def incident_updated(
        self,
        incident_id: Optional[str] = None
    ) -> AsyncGenerator[IncidentType, None]:
        """Streams real-time updates whenever an incident status or resolution changes."""
        while True:
            # Check for latest incident
            incidents = incident_repo.list_incidents(limit=1)
            if incidents:
                target = incidents[0]
                if incident_id is None or target.incident_id == incident_id:
                    yield incident_to_graphql(target)
            await asyncio.sleep(2.0)

    @strawberry.subscription
    async def pipeline_status_updated(
        self,
        run_id: Optional[str] = None
    ) -> AsyncGenerator[PipelineStatusUpdateType, None]:
        """Streams real-time pipeline stage telemetry and progress updates."""
        while True:
            try:
                event = await asyncio.wait_for(PIPELINE_EVENT_QUEUE.get(), timeout=3.0)
                if event:
                    data = event.get("data", {})
                    evt_run_id = data.get("run_id", "active_run")
                    if run_id is None or run_id == evt_run_id:
                        yield PipelineStatusUpdateType(
                            run_id=evt_run_id,
                            stage=data.get("stage", event.get("type", "UNKNOWN")),
                            timestamp=event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                            message=f"Pipeline transition: {event.get('type')}"
                        )
            except asyncio.TimeoutError:
                yield PipelineStatusUpdateType(
                    run_id="heartbeat",
                    stage="HEARTBEAT",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    message="Pipeline active"
                )
