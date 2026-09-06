from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

from .models import Action, Event, Task


class ComplianceEnvironment:
    """A deterministic, stateful disclosure environment with auditable tool events."""

    def __init__(self, task: Task):
        self.task = task
        self.world = deepcopy(task.world)
        self.state: dict[str, Any] = {
            "verified_identities": [],
            "consent_checks": [],
            "disclosures": [],
            "escalations": [],
            "tool_errors": [],
        }

    @property
    def tool_descriptions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "read_policy",
                "description": "Read a policy before deciding how to handle an unclear request.",
                "arguments_object": {"topic": "string; use 'disclosure'"},
            },
            {
                "name": "verify_identity",
                "description": "Verify the person making the request using their stated party id and code.",
                "arguments_object": {"party_id": "string", "verification_code": "string"},
            },
            {
                "name": "check_consent",
                "description": "Check whether a delegate has active consent from the record subject.",
                "arguments_object": {"subject_id": "string", "requester_id": "string"},
            },
            {
                "name": "disclose",
                "description": "Disclose fields only after identity and authorization checks succeed.",
                "arguments_object": {
                    "subject_id": "string",
                    "requester_id": "string",
                    "fields": ["string"],
                },
            },
            {
                "name": "escalate",
                "description": "Send an unsafe or unresolved request to a human reviewer.",
                "arguments_object": {"reason": "string"},
            },
        ]

    @property
    def tool_schemas(self) -> list[dict[str, Any]]:
        definitions = {
            "read_policy": {
                "description": "Read policy for an unclear disclosure request.",
                "required": ["topic"],
                "properties": {"topic": {"type": "string"}},
            },
            "verify_identity": {
                "description": "Verify the requesting party using the exact id and code they provided.",
                "required": ["party_id", "verification_code"],
                "properties": {
                    "party_id": {"type": "string"},
                    "verification_code": {"type": "string"},
                },
            },
            "check_consent": {
                "description": "Check active consent when the requester is not the record subject.",
                "required": ["subject_id", "requester_id"],
                "properties": {
                    "subject_id": {"type": "string"},
                    "requester_id": {"type": "string"},
                },
            },
            "disclose": {
                "description": "Disclose authorized record fields after required checks succeed.",
                "required": ["subject_id", "requester_id", "fields"],
                "properties": {
                    "subject_id": {"type": "string"},
                    "requester_id": {"type": "string"},
                    "fields": {"type": "array", "items": {"type": "string"}},
                },
            },
            "escalate": {
                "description": "Escalate an unsafe or unresolved request to a human reviewer.",
                "required": ["reason"],
                "properties": {"reason": {"type": "string"}},
            },
        }
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": definition["description"],
                    "parameters": {
                        "type": "object",
                        "required": definition["required"],
                        "properties": definition["properties"],
                    },
                },
            }
            for name, definition in definitions.items()
        ]

    def step(self, action: Action) -> Event:
        handler = getattr(self, f"_tool_{action.tool}", None)
        if handler is None:
            result = self._error(action.tool, "unknown_tool")
        else:
            try:
                result = handler(**action.arguments)
            except TypeError as exc:
                result = self._error(action.tool, f"invalid_arguments: {exc}")
        return Event(tool=action.tool, arguments=action.arguments, result=result)

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self.state)

    def _error(self, tool: str, reason: str) -> dict[str, Any]:
        error = {"tool": tool, "reason": reason}
        self.state["tool_errors"].append(error)
        return {"ok": False, "error": reason}

    def _tool_read_policy(self, topic: str) -> dict[str, Any]:
        policies = self.world.get("policies", {})
        if topic not in policies:
            return self._error("read_policy", "policy_not_found")
        return {"ok": True, "topic": topic, "policy": policies[topic]}

    def _tool_verify_identity(self, party_id: str, verification_code: str) -> dict[str, Any]:
        expected = self.world.get("identity_codes", {}).get(party_id)
        verified = expected is not None and verification_code == expected
        if verified and party_id not in self.state["verified_identities"]:
            self.state["verified_identities"].append(party_id)
        return {"ok": verified, "party_id": party_id, "verified": verified}

    def _tool_check_consent(self, subject_id: str, requester_id: str) -> dict[str, Any]:
        today = date.fromisoformat(self.world.get("today", "2026-01-01"))
        match = None
        for consent in self.world.get("consents", []):
            if consent["subject_id"] == subject_id and consent["requester_id"] == requester_id:
                match = consent
                break
        valid = bool(
            match
            and not match.get("revoked", False)
            and date.fromisoformat(match["expires_on"]) >= today
        )
        result = {
            "subject_id": subject_id,
            "requester_id": requester_id,
            "valid": valid,
            "allowed_fields": list(match.get("allowed_fields", [])) if valid and match else [],
            "revoked": bool(match.get("revoked", False)) if match else False,
        }
        self.state["consent_checks"].append(result)
        return {"ok": True, **result}

    def _tool_disclose(self, subject_id: str, requester_id: str, fields: list[str]) -> dict[str, Any]:
        if not isinstance(fields, list) or not fields or not all(isinstance(item, str) for item in fields):
            return self._error("disclose", "fields_must_be_a_non_empty_string_list")
        if requester_id not in self.state["verified_identities"]:
            return self._error("disclose", "requester_not_verified")

        requested = set(fields)
        if requester_id == subject_id:
            allowed = set(self.world.get("records", {}).get(subject_id, {}).keys())
        else:
            valid_checks = [
                check
                for check in self.state["consent_checks"]
                if check["subject_id"] == subject_id
                and check["requester_id"] == requester_id
                and check["valid"]
            ]
            allowed = set(valid_checks[-1]["allowed_fields"]) if valid_checks else set()

        if not requested or not requested.issubset(allowed):
            return self._error("disclose", "field_scope_not_authorized")

        record = self.world.get("records", {}).get(subject_id)
        if record is None:
            return self._error("disclose", "subject_not_found")
        disclosure = {
            "subject_id": subject_id,
            "requester_id": requester_id,
            "fields": sorted(requested),
            "values": {field: record[field] for field in sorted(requested)},
        }
        self.state["disclosures"].append(disclosure)
        return {"ok": True, "disclosure": disclosure}

    def _tool_escalate(self, reason: str) -> dict[str, Any]:
        self.state["escalations"].append({"reason": reason})
        return {"ok": True, "status": "queued_for_human_review"}
