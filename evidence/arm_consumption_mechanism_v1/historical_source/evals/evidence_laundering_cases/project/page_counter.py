"""Synthetic benchmark fixture."""

from math import ceil as round_up


def count_pages(item_count, page_size):
    return round_up(item_count / page_size)
