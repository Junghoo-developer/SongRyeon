# Reproducibility record

This document separates the minimum software contract from one tested host.
Hardware figures below are evidence about that host, not a claimed minimum.

## Runtime contract

- Python 3.10 or newer
- Ollama installed locally, or an explicitly selected self-hosted Ollama endpoint
- `gemma4:26b` available for the contest-large profile
- `qwen3:14b` available only when reproducing the historical model-scale exploration
- no external API key required
- network access is not required after the model and source are installed

## Clean installation

Install Ollama from its [official download page](https://ollama.com/download).
On Windows, start the installed app or run the server in PowerShell:

```powershell
ollama serve
# Keep that window open, then use a new PowerShell window:
ollama pull gemma4:26b
```

On Linux, the equivalent Bash setup is:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
# Keep that process running, then use a new terminal:
ollama pull gemma4:26b
```

If the Ollama app or service is already running, do not start a second server.

Create a clean clone and virtual environment in PowerShell:

```powershell
git clone --branch contest-2026-final --single-branch https://github.com/Junghoo-developer/SongRyeon.git SongRyeon_Core_v1
Set-Location SongRyeon_Core_v1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest -q
```

The Bash equivalent is:

```bash
git clone --branch contest-2026-final --single-branch https://github.com/Junghoo-developer/SongRyeon.git SongRyeon_Core_v1
cd SongRyeon_Core_v1
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest -q
```

Deterministic tests use temporary paths and do not touch the real memory file.

## Demo command

The default model is `gemma4:26b`, so the explicit `--model` below is optional.
Use a separate memory file when reproducing a run:

```powershell
python -m demo --memory .\tmp\demo-memory.jsonl `
  "runtime/gates.py를 실제로 읽고 역할을 설명해 줘."
```

Editable installation also provides the equivalent console command:

```powershell
songryeon --model gemma4:26b --memory .\tmp\demo-memory.jsonl `
  "runtime/gates.py를 실제로 읽고 역할을 설명해 줘."
```

If `songryeon` is not on `PATH`, activate the virtual environment or use
`python -m demo`. In Bash, use `./tmp/demo-memory.jsonl` and `\` for line
continuation.

Relevant local/self-hosted CLI options are:

| Option | Default | Purpose |
|---|---|---|
| `--model` | `gemma4:26b` | Ollama model tag |
| `--base-url` | `http://127.0.0.1:11434` | local or self-hosted Ollama endpoint |
| `--num-ctx` | `16384` | requested model context |
| `--timeout-seconds` | `180` | timeout for each Ollama HTTP request |
| `--keep-alive` | `10m` | how long Ollama keeps the model loaded |
| `--memory` | `memory/memory.jsonl` | raw audit log path |
| `--project-root` | repository root | root visible to Node1 file tools |

Run `python -m demo --help` for the source-of-truth CLI help.

If Node2 or Node4 rejects again after its three applied rejections, the runtime
continues only to terminate the bounded loop. It does not convert that reject
into a permit. The CLI explicitly warns that evidence verification (Node2) or
answer-audit permission (Node4) was not completed. Treat such a run as
validation-incomplete and preserve that status with any reproduced result.

The contest execution profile is a local or self-hosted Ollama server running
an open-weight model directly. It must never fall back automatically to a
commercial API. The separate API integration-test exception and its data
boundary are defined in
[`contest_model_policy.md`](contest_model_policy.md).

## Tested host record

The following versions were observed on 2026-07-30:

| Component | Observed value |
|---|---|
| Operating system | Windows 11 Pro 64-bit, build 10.0.26200 |
| CPU | Intel Core i9-14900K |
| GPU | NVIDIA GeForce RTX 5080, 16,303 MiB |
| Python | 3.10.11 |
| Ollama | 0.32.5 |
| Contest-large model tag | `gemma4:26b` |
| Contest-large Ollama model ID | `5571076f3d70` |
| Contest-large full digest | `5571076f3d70050487b26b341705799e0ab29b808164f90d20d4cf84f699d251` |
| Parameters | 25.8B |
| Quantization | `Q4_K_M` |
| Model license | Apache License 2.0 |
| Installed model size | 17,987,581,215 bytes |
| Physical memory | 63.69 GiB |

The byte count is the installed model artifact size, and 63.69 GiB is only the
physical memory of the host used for verification. Neither figure is a claimed
minimum requirement. Actual ability to load the model and its performance
depend on the operating system, CPU, GPU, available memory, and offloading
configuration.

The installed `gemma4:26b` model reports a 262,144-token model context. A
smaller context requested by SongRyeon is an explicit runtime choice and must
not be confused with the model's maximum capability. Record the requested
context alongside every raw evaluation result.

The historical exploration model observed on the same date was `qwen3:14b`, Ollama model
ID `bdbd181c33f2`, full digest
`bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`,
`Q4_K_M`, 9,276,198,565 bytes. It is not part of the official v2 structural
comparison, the default, or an automatic fallback. Pull it only when
reproducing the historical model-scale exploration:

```powershell
ollama pull qwen3:14b
python -m demo --model qwen3:14b --memory .\.tmp\baseline-memory.jsonl `
  "runtime/gates.py를 실제로 읽고 역할을 설명해 줘."
```

Official `gemma4:26b` results and the historical `qwen3:14b` exploration are
separate groups even when every other setting is identical.

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
