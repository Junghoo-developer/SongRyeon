# Third-party notices

SongRyeon Core does not redistribute an AI model or the Ollama executable.
They are installed separately by the user.

## Qwen3-14B

- Project: Qwen3-14B
- Provider: Qwen / Alibaba Cloud
- Source: https://huggingface.co/Qwen/Qwen3-14B
- License: Apache License 2.0
- Use in SongRyeon: default locally executed language model

The exact model tag and digest used for an evaluation should be recorded with
the corresponding raw evaluation result.

## Ollama

- Project: Ollama
- Source: https://github.com/ollama/ollama
- License: MIT License
- Use in SongRyeon: local model runtime accessed through its HTTP interface

## Python standard library

The current SongRyeon runtime has no mandatory third-party Python package.
`pytest` is an optional development dependency used only for tests.
