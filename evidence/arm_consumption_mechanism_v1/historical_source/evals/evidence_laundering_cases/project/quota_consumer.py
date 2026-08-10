"""Synthetic benchmark fixture."""

from quota_origin import REQUEST_QUOTA as ORIGIN_REQUEST_QUOTA


def effective_quota():
    return ORIGIN_REQUEST_QUOTA
