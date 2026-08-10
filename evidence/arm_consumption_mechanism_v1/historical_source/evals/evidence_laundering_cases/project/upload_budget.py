"""Synthetic benchmark fixture."""

MAX_UPLOAD_BYTES = 4_096


def store_blob(blob):
    return {"stored": blob, "observed_bytes": len(blob)}
