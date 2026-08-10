"""Synthetic benchmark fixture."""

from base64 import b64decode as decode_bytes


def unpack_token(encoded_token):
    return decode_bytes(encoded_token)
