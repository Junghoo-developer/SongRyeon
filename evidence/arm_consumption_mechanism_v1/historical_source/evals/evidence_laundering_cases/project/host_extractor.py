"""Synthetic benchmark fixture."""

from urllib.parse import urlsplit as split_address


def extract_host(address):
    return split_address(address).hostname
