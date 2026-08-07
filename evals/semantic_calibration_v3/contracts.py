"""Build immutable prompts for the v3 run plan."""

from __future__ import annotations

import hashlib
import json

from schemas import canonical_json, encode_wire_observation, response_schema


SEMANTIC_SYSTEM_PROMPT = """You predict CPython 3.10.11 behavior from complete source code.
Each claim gives a proposition about one function call in a fresh interpreter.
SUPPORTED means the proposition observation exactly matches the actual call.
UNSUPPORTED means it does not. In both cases, observation must contain your
predicted actual result, not a copy of a false proposition. Do not execute code.
The input proposition_observation uses a typed JSON value. In your output,
encode the predicted actual value exactly once as JSON text in value_json.
For example, JSON true becomes the string "true", a list becomes the string
"[1,2]", and the actual string null becomes the string '"null"'. For
return observations exception must be null. For raise observations value_json
must be the four-character string "null". Every reason must be nonempty.
Return only the required JSON object. Every claim must appear exactly once."""


CONTRACT_SYSTEM_PROMPT = """This is a structured-output transcription check.
Copy every supplied id, verdict, kind, value_json meaning, and exception into
the required JSON object and add a short nonempty reason. value_json is JSON
text encoded exactly once; preserve its typed JSON meaning without adding a
wrapper. For return observations exception must be null. For raise observations
value_json must be the four-character string "null". For unknown observations
value_json must be "null" and exception must be null. Return only the JSON
object. Every claim must appear exactly once."""


def opaque_token(namespace, value):
    digest = hashlib.sha256(
        f"semantic-calibration-v3|{namespace}|{value}".encode("utf-8")
    ).hexdigest()[:10]
    return digest


def build_semantic_unit(case, claims, *, mode, ordinal):
    visible_source = "source-" + opaque_token("source", case["case_id"]) + ".py"
    visible_ids = {
        claim["id"]: "Q-" + opaque_token("claim", claim["id"])
        for claim in claims
    }
    source_packet = {
        "path": visible_source,
        "content": case["source_content"],
    }
    claim_packet = [
        {
            "id": visible_ids[claim["id"]],
            "expression": f"{claim['function']}()",
            "description": claim["description"],
            "proposition_observation": claim["proposition"],
        }
        for claim in claims
    ]
    internal_ids = [claim["id"] for claim in claims]
    ids = [visible_ids[claim_id] for claim_id in internal_ids]
    user_prompt = (
        "Evaluate the claims using only the complete source packet below. "
        "Each expression is called in its own fresh interpreter.\n\n"
        "[SOURCE_PACKET]\n"
        + canonical_json(source_packet)
        + "\n\n[CLAIMS]\n"
        + canonical_json(claim_packet)
    )
    return {
        "plan_id": f"semantic-{ordinal:02d}-{mode}-{case['case_id']}-{'_'.join(ids)}",
        "stage": "semantic",
        "mode": mode,
        "case_id": case["case_id"],
        "difficulty": case["difficulty"],
        "expected_ids": ids,
        "internal_claim_ids": internal_ids,
        "allow_unknown": False,
        "system_prompt": SEMANTIC_SYSTEM_PROMPT,
        "user_prompt": user_prompt,
        "response_schema": response_schema(ids, allow_unknown=False),
        "num_predict": 800 if mode == "single" else 2_400,
    }


def build_contract_unit(case, *, ordinal):
    ids = [claim["id"] for claim in case["claims"]]
    supplied = [
        {
            "id": claim["id"],
            "verdict": claim["verdict"],
            "observation": encode_wire_observation(
                claim["observation"],
                allow_unknown=True,
            ),
        }
        for claim in case["claims"]
    ]
    return {
        "plan_id": f"contract-{ordinal:02d}-{case['case_id']}",
        "stage": "contract",
        "mode": "contract",
        "case_id": case["case_id"],
        "difficulty": "contract",
        "expected_ids": ids,
        "internal_claim_ids": ids,
        "allow_unknown": True,
        "system_prompt": CONTRACT_SYSTEM_PROMPT,
        "user_prompt": "Reproduce these supplied fields exactly:\n" + canonical_json(supplied),
        "response_schema": response_schema(ids, allow_unknown=True),
        "num_predict": 800 * len(ids),
    }
