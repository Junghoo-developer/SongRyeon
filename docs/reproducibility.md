# Reproducibility record

This document separates the minimum software contract from one tested host.
Hardware figures below are evidence about that host, not a claimed minimum.

## Runtime contract

- Python 3.10 or newer
- Ollama installed locally
- `qwen3:14b` available in Ollama
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
songryeon --memory .\tmp\demo-memory.jsonl `
  "runtime/gates.py를 실제로 읽고 역할을 설명해 줘."
```

## Tested host record

The following versions were observed on 2026-07-29:

| Component | Observed value |
|---|---|
| Python | 3.10.11 |
| Ollama | 0.32.5 |
| Model tag | `qwen3:14b` |
| Ollama model ID | `bdbd181c33f2` |
| Quantization | `Q4_K_M` |
| Installed model size | approximately 9.3 GB |
| Physical memory | approximately 64 GB |

SongRyeon currently requests a 16,384-token context even though this local
model reports a 40,960-token model context. That smaller request is an explicit
runtime choice and must not be confused with the model's maximum capability.

## Record a new evaluation environment

Run these commands and keep their output beside the raw evaluation result:

```powershell
python --version
ollama --version
ollama list
ollama show qwen3:14b
```

An evaluation report should also record:

- operating system
- exact Git commit
- SongRyeon configuration
- model tag and model ID
- test-case set version
- start and end time
- whether the host had network access

Performance results from different model IDs or configurations must not be
merged into one comparison without labelling the difference.
