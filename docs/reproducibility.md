# Reproducibility record

This document separates the minimum software contract from one tested host.
Hardware figures below are evidence about that host, not a claimed minimum.

## Runtime contract

- Python 3.10 or newer
- Ollama installed locally
- `gemma4:26b` available for the contest-large profile
- `qwen3:14b` available only when reproducing the smaller baseline
- no external API key required
- network access is not required after the model and source are installed

Install the Python package in editable mode:

```powershell
python -m pip install -e .
```

Run deterministic tests without touching the real memory:

```powershell
python -m pytest -q
```

Run a demo with an isolated memory file:

```powershell
songryeon --model gemma4:26b --memory .\tmp\demo-memory.jsonl `
  "runtime/gates.py를 실제로 읽고 역할을 설명해 줘."
```

The contest execution profile is a local or self-hosted Ollama server running
an open-weight model directly. It must never fall back automatically to a
commercial API. The separate API integration-test exception and its data
boundary are defined in
[`contest_model_policy.md`](contest_model_policy.md).

## Tested host record

The following versions were observed on 2026-07-29:

| Component | Observed value |
|---|---|
| Python | 3.10.11 |
| Ollama | 0.32.5 |
| Contest-large model tag | `gemma4:26b` |
| Contest-large Ollama model ID | `5571076f3d70` |
| Parameters | 25.8B |
| Quantization | `Q4_K_M` |
| Model license | Apache License 2.0 |
| Installed model size | approximately 17 GB |
| Physical memory | approximately 64 GB |

The installed `gemma4:26b` model reports a 262,144-token model context. A
smaller context requested by SongRyeon is an explicit runtime choice and must
not be confused with the model's maximum capability. Record the requested
context alongside every raw evaluation result.

The installed baseline observed on the same date was `qwen3:14b`, Ollama model
ID `bdbd181c33f2`, `Q4_K_M`, approximately 9.3 GB. Contest-large and baseline
results are separate groups even when every other setting is identical.

## Record a new evaluation environment

Run these commands and keep their output beside the raw evaluation result:

```powershell
python --version
ollama --version
ollama list
ollama show gemma4:26b
```

An evaluation report should also record:

- operating system
- exact Git commit
- SongRyeon configuration
- model tag and model ID
- model source, license, parameter count, and quantization
- requested context size and model-reported maximum context
- endpoint class: local, self-hosted, or external integration test
- test-case set version
- start and end time
- whether the host had network access

Performance results from different model IDs or configurations must not be
merged into one comparison without labelling the difference.

External API integration tests, if any, use a separate temporary memory file
and public or synthetic input. They are labelled `external_api_integration`
and are excluded from contest-demo and official evaluation aggregates. The raw
record may identify the provider, model, date, and endpoint class, but must
never contain an API key, account credential, private code, or the real
`memory/memory.jsonl`.
