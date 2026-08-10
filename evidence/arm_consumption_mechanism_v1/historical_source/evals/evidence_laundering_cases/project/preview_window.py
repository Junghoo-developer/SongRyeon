"""Synthetic benchmark fixture."""

PREVIEW_ITEM_LIMIT = 3


def build_preview(items):
    return list(items)[:PREVIEW_ITEM_LIMIT]
