# Third-party notices

SongRyeon Core does not redistribute an AI model or the Ollama executable.
They are installed separately by the user.

## Gemma 4 26B

- Project: Gemma 4 26B
- Provider: Google
- Source: https://ollama.com/library/gemma4:26b
- Ollama tag and model ID: `gemma4:26b` / `5571076f3d70`
- Parameters and quantization: 25.8B / `Q4_K_M`
- License: Apache License 2.0
- Use in SongRyeon: contest-large model executed locally or on a self-hosted
  Ollama server

## Qwen3-14B

- Project: Qwen3-14B
- Provider: Qwen / Alibaba Cloud
- Source: https://huggingface.co/Qwen/Qwen3-14B
- License: Apache License 2.0
- Use in SongRyeon: smaller locally executed comparison baseline

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

## Optional commercial AI APIs

No commercial AI API is redistributed, required, or used as an automatic
fallback by the contest execution path. A provider may be connected only for a
separately labelled agent-framework integration test under the contest rule
exception. Such a test does not make that provider or model part of the
submitted local runtime, and its result is excluded from official evaluation
aggregates.

Provider name, exact model, access date, and applicable terms must be recorded
beside that integration-test result. Credentials remain in an environment
variable and are never stored in the repository, command line, memory log, or
evaluation artifact.
