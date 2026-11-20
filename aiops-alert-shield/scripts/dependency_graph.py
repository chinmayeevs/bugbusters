"""
scripts/dependency_graph.py
Deterministic Service Dependency Graph and Blast Radius Traversal.
Models topological call graph of the e-commerce checkout architecture.
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Literal
from backend.models.contracts import BlastRadiusReport, BlastRadiusNode

# Directed call graph: caller -> callee
CALL_GRAPH: Dict[str, List[str]] = {
    "api-gateway": ["checkout-api", "redis-cache"],
    "checkout-api": ["payment-service", "inventory-service", "orders-postgres-primary", "redis-cache"],
    "payment-service": ["orders-postgres-primary"],
    "inventory-service": ["orders-postgres-primary"],
    "orders-postgres-primary": [],
    "redis-cache": [],
}

# Reverse dependency graph: callee -> callers (who depends on this callee)
REVERSE_GRAPH: Dict[str, List[str]] = {
    "orders-postgres-primary": ["checkout-api", "payment-service", "inventory-service"],
    "redis-cache": ["checkout-api", "api-gateway"],
    "payment-service": ["checkout-api"],
    "inventory-service": ["checkout-api"],
    "checkout-api": ["api-gateway"],
    "api-gateway": [],
}

CRITICAL_PATH = ["api-gateway", "checkout-api", "orders-postgres-primary", "payment-service"]


def get_upstream_impact(root_service: str) -> Dict[str, int]:
    """Finds all upstream services that depend directly or indirectly on root_service, with hop distance."""
    visited: Dict[str, int] = {root_service: 0}
    queue = [(root_service, 0)]

    while queue:
        curr, dist = queue.pop(0)
        callers = REVERSE_GRAPH.get(curr, [])
        for caller in callers:
            if caller not in visited:
                visited[caller] = dist + 1
                queue.append((caller, dist + 1))

    return visited


def compute_blast_radius(
    anomalous_services: List[str],
    root_candidate: str,
    evidence_idx: int = 1
) -> BlastRadiusReport:
    """
    Computes deterministic blast radius topology traversal starting from candidate root cause.
    """
    upstream_hops = get_upstream_impact(root_candidate)
    compromised: Set[str] = set(anomalous_services).union(set(upstream_hops.keys()))

    nodes: List[BlastRadiusNode] = []
    all_services = list(CALL_GRAPH.keys())

    for svc in all_services:
        if svc == root_candidate:
            role = "ROOT_SUSPECT"
            level = "CRITICAL"
            loss = 100.0 if svc in anomalous_services else 20.0
            dist = 0
        elif svc in upstream_hops:
            role = "AFFECTED_UPSTREAM"
            dist = upstream_hops[svc]
            level = "CRITICAL" if dist == 1 else "DEGRADED"
            loss = max(0.0, 90.0 - (dist * 20.0))
        elif svc in CALL_GRAPH.get(root_candidate, []):
            role = "AFFECTED_DOWNSTREAM"
            dist = 1
            level = "DEGRADED"
            loss = 30.0
        else:
            role = "UNAFFECTED"
            dist = -1
            level = "NORMAL"
            loss = 0.0

        nodes.append(BlastRadiusNode(
            service=svc,
            role=role,  # type: ignore
            hop_distance=dist,
            impact_level=level,  # type: ignore
            traffic_loss_pct=round(loss, 1)
        ))

    # Critical path check: if both checkout-api and api-gateway are compromised
    crit_affected = any(svc in compromised for svc in ["api-gateway", "checkout-api"])
    customer_impact = "api-gateway" in compromised or "checkout-api" in compromised

    # Score: weighted compromised services / total
    score = round(min(1.0, len(compromised) / len(all_services)), 2)

    return BlastRadiusReport(
        evidence_id=f"EVID-BLAST-{evidence_idx:03d}",
        root_suspect=root_candidate,
        compromised_services=sorted(list(compromised)),
        critical_path_affected=crit_affected,
        blast_radius_score=score,
        nodes=nodes,
        customer_facing_impact=customer_impact
    )
