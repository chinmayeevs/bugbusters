"""
backend/storage/case_repository.py
SQLite-backed versioned casebook repository for Self-Evolving Agent (SEA).
Manages historical incident signatures, context conditions, and versioned evolution.
"""

from __future__ import annotations
import json
import math
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from backend.models.contracts import HistoricalMatch

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "casebook.db"


def compute_vector_cosine_similarity(text1: str, text2: str) -> float:
    """Computes cosine similarity between two term frequency vectors without external libraries."""
    def get_tokens(text: str) -> List[str]:
        return [w for w in re.findall(r'[a-zA-Z0-9_]+', text.lower()) if len(w) > 1]

    t1 = get_tokens(text1)
    t2 = get_tokens(text2)
    if not t1 or not t2:
        return 0.0

    c1 = Counter(t1)
    c2 = Counter(t2)
    vocab = set(c1.keys()).union(set(c2.keys()))

    dot = sum(c1[w] * c2[w] for w in vocab)
    norm1 = math.sqrt(sum(v * v for v in c1.values()))
    norm2 = math.sqrt(sum(v * v for v in c2.values()))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return round(dot / (norm1 * norm2), 4)


class CaseRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._seed_if_empty()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    symptom_signature TEXT NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    historical_outcome TEXT NOT NULL,
                    context_conditions TEXT NOT NULL,
                    remediation_recommendation TEXT,
                    verified_by TEXT,
                    version INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_sig ON cases (symptom_signature);")

    def _seed_if_empty(self):
        """Seeds initial cases from data/past_incidents_seed.json if database is empty."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) as cnt FROM cases;")
            count = cur.fetchone()["cnt"]
            if count == 0:
                seed_file = Path(__file__).resolve().parent.parent.parent / "data" / "past_incidents_seed.json"
                if seed_file.exists():
                    try:
                        with open(seed_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        for item in data:
                            conn.execute("""
                                INSERT INTO cases (
                                    case_id, symptom_signature, title, category,
                                    historical_outcome, context_conditions,
                                    remediation_recommendation, verified_by, version,
                                    created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                            """, (
                                item["case_id"],
                                item["symptom_signature"],
                                item["title"],
                                item.get("category", "GENERAL"),
                                item["historical_outcome"],
                                json.dumps(item.get("context_conditions", {})),
                                item.get("remediation_recommendation", ""),
                                item.get("verified_by", "system"),
                                item.get("version", 1),
                                now_iso,
                                now_iso
                            ))
                        conn.commit()
                    except Exception as e:
                        print(f"Failed to seed casebook: {e}")

    def search_matches(
        self,
        symptom_signature: str,
        current_context: Dict[str, Any]
    ) -> List[HistoricalMatch]:
        """
        Searches for cases combining deterministic symptom signature matching with
        local vector cosine similarity, and evaluates operational context divergence.
        """
        matches: List[HistoricalMatch] = []
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM cases;")
            rows = cur.fetchall()

        # Tokenize signature for partial/semantic match (e.g. orders-postgres-primary:high_cpu)
        sig_tokens = set(symptom_signature.lower().replace("-", " ").replace(":", " ").replace("_", " ").split())
        curr_context_text = f"{symptom_signature} {' '.join(str(k) + ':' + str(v) for k, v in current_context.items())}"

        for row in rows:
            case_sig = row["symptom_signature"]
            case_tokens = set(case_sig.lower().replace("-", " ").replace(":", " ").replace("_", " ").split())
            intersection = sig_tokens.intersection(case_tokens)
            union = sig_tokens.union(case_tokens)
            token_overlap = len(intersection) / len(union) if union else 0.0

            # Compute local vector cosine similarity across signature, title, conditions, and remediation
            case_context_text = f"{case_sig} {row['title']} {row['context_conditions']} {row['remediation_recommendation']}"
            cosine_sim = compute_vector_cosine_similarity(curr_context_text, case_context_text)

            # Consider match if overlap >= 0.25, cosine_sim >= 0.20, or service matches
            row_svc = case_sig.split(":")[0]
            if token_overlap >= 0.25 or cosine_sim >= 0.20 or (row_svc in symptom_signature):
                conds = json.loads(row["context_conditions"])
                # Evaluate Context Divergence
                divergence, reason, div_features, matched_keys, diverged_keys = self._check_divergence(conds, current_context)

                # Weighted hybrid similarity: deterministic token overlap + vector cosine similarity
                if row_svc in symptom_signature:
                    effective_sim = round(max(0.75, 0.4 * token_overlap + 0.6 * cosine_sim), 2)
                else:
                    effective_sim = round(0.4 * token_overlap + 0.6 * cosine_sim, 2)

                matches.append(HistoricalMatch(
                    case_id=row["case_id"],
                    symptom_signature=row["symptom_signature"],
                    title=row["title"],
                    similarity_score=min(1.0, max(0.0, effective_sim)),
                    historical_outcome=row["historical_outcome"],
                    context_divergence_flag=divergence,
                    divergence_reason=reason,
                    matching_features={"matched_tokens": list(intersection), "vector_cosine_sim": cosine_sim},
                    divergent_features=div_features,
                    remediation_recommendation=row["remediation_recommendation"],
                    matched_context_keys=matched_keys,
                    diverged_context_keys=diverged_keys
                ))

        # Sort matches by similarity score descending
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches

    def _check_divergence(
        self,
        historical_conds: Dict[str, Any],
        current_context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Dict[str, Any], List[str], List[str]]:
        """
        Checks for Context Divergence:
        - Case A: Same symptom + same benign context (e.g. 02:00 maintenance window, zero downstream latency spike) -> No divergence.
        - Case B: Same symptom + different context (e.g. midday 14:00, no backup running, downstream latency spiked 3000ms+) -> Divergence DETECTED!
        Returns: (divergence_flag, reason_str, divergent_features_dict, matched_context_keys, diverged_context_keys)
        """
        divergent_features: Dict[str, Any] = {}
        matched_keys: List[str] = []
        diverged_keys: List[str] = []

        keys_to_check = ["downstream_latency_spike", "error_rate_spike", "cron_job_active", "customer_impact"]
        for k in keys_to_check:
            hist_val = historical_conds.get(k)
            curr_val = current_context.get(k)
            if hist_val is not None and curr_val is not None:
                if hist_val == curr_val:
                    matched_keys.append(k)
                else:
                    diverged_keys.append(k)
                    divergent_features[k] = {"historical": hist_val, "current": curr_val}

        if divergent_features:
            reasons = []
            if "downstream_latency_spike" in divergent_features:
                reasons.append("Downstream checkout latency spiked significantly in current context")
            if "cron_job_active" in divergent_features:
                hist_cron = historical_conds.get("cron_job_active")
                reasons.append(f"Scheduled maintenance job '{hist_cron}' is NOT active in current run")
            if "error_rate_spike" in divergent_features:
                reasons.append("Downstream 5xx error rate is elevated in current context")
            reason_str = "; ".join(reasons) if reasons else "Operational context conditions diverged from historical baseline."
            return True, reason_str, divergent_features, matched_keys, diverged_keys

        return False, None, {}, matched_keys, diverged_keys

    def list_all_cases(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists cases from the casebook with parsed context and provenance labels."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM cases ORDER BY updated_at DESC LIMIT ?;", (limit,))
            rows = cur.fetchall()
            result = []
            for r in rows:
                c = dict(r)
                if c["verified_by"] == "engineer":
                    c["provenance"] = "HUMAN_CONFIRMED"
                elif c["verified_by"] == "system":
                    c["provenance"] = "SEED"
                else:
                    c["provenance"] = "VERIFIER_APPROVED"
                try:
                    c["context_conditions_parsed"] = json.loads(c["context_conditions"])
                except Exception:
                    c["context_conditions_parsed"] = {}
                result.append(c)
            return result

    def append_verified_case(
        self,
        symptom_signature: str,
        title: str,
        category: str,
        outcome: str,
        context_conditions: Dict[str, Any],
        remediation: str,
        verified_by: str = "engineer"
    ) -> str:
        """
        Appends or updates a versioned casebook entry post-verification.
        Enforces write path rule: Never auto-remediates, versioned entries only.
        """
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._get_connection() as conn:
            cur = conn.execute("SELECT case_id, version FROM cases WHERE symptom_signature = ?;", (symptom_signature,))
            existing = cur.fetchone()

            if existing:
                case_id = existing["case_id"]
                new_version = existing["version"] + 1
                conn.execute("""
                    UPDATE cases SET
                        title = ?, category = ?, historical_outcome = ?,
                        context_conditions = ?, remediation_recommendation = ?,
                        verified_by = ?, version = ?, updated_at = ?
                    WHERE case_id = ?;
                """, (
                    title, category, outcome, json.dumps(context_conditions),
                    remediation, verified_by, new_version, now_iso, case_id
                ))
            else:
                import uuid
                case_id = f"CASE-{uuid.uuid4().hex[:6].upper()}"
                conn.execute("""
                    INSERT INTO cases (
                        case_id, symptom_signature, title, category,
                        historical_outcome, context_conditions,
                        remediation_recommendation, verified_by, version,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    case_id, symptom_signature, title, category, outcome,
                    json.dumps(context_conditions), remediation, verified_by,
                    1, now_iso, now_iso
                ))
            conn.commit()
            return case_id
