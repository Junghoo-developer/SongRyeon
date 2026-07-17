# Third-Party Components And License Notes

Audit date: 2026-07-17

This is a practical disclosure for contest review and public repository readers. It is not
legal advice and is not a generated software bill of materials.

## Project Code

- SongRyeon Core source code: MIT License
- Repository license file: [`LICENSE`](LICENSE)

## Distribution Boundary

- This repository does not include model weights.
- The deterministic `competition-demo` needs no external model, API, or Neo4j service.
- Ollama, Qwen, Neo4j DBMS, OpenAI API access, and Codex CLI are optional external runtimes.
- Local audit versions below describe the maintainer's 2026-07-17 environment. They are not
  all repository pins.

## Direct And Optional Components

| Component | Project relation | Version contract / local audit | Bundled here | License status checked | Upstream |
| --- | --- | --- | --- | --- | --- |
| pytest | Development tests via `requirements-dev.txt` | Unpinned / 9.0.3 observed | No | MIT | [pytest-dev/pytest](https://github.com/pytest-dev/pytest) |
| Ollama Python client | Optional local Qwen adapter | Unpinned / 0.6.1 observed | No | MIT | [ollama/ollama-python](https://github.com/ollama/ollama-python) |
| Ollama runtime | Optional local model server | User-installed | No | MIT for the upstream repository; bundled third-party notices remain the runtime distributor's responsibility | [ollama/ollama](https://github.com/ollama/ollama) |
| Qwen3-14B | Optional default live model through Ollama or a compatible endpoint | User-selected artifact | No weights | Official model repository states Apache-2.0; verify the exact artifact installed | [Qwen/Qwen3-14B](https://huggingface.co/Qwen/Qwen3-14B) |
| Neo4j Python driver | Optional Vessel adapter import | Unpinned / 6.1.0 observed | No | Upstream `LICENSE.txt` says generally Apache-2.0, with marked portions under Python Software Foundation License v2 | [neo4j-python-driver license](https://github.com/neo4j/neo4j-python-driver/blob/6.x/LICENSE.txt) |
| Neo4j DBMS | Optional local graph database service | User-installed | No | Separate product/distribution terms; do not infer them from the Python driver license | [Neo4j licensing](https://neo4j.com/licensing/) |
| OpenAI Python SDK | Optional Responses API path via `requirements-openai.txt` | `>=2.14.0,<3` / 2.14.0 observed | No | Apache-2.0 | [openai/openai-python](https://github.com/openai/openai-python) |
| `openai-codex` Python SDK | Optional Codex comparison adapter via `requirements-codex-sdk.txt` | `0.1.0b3` pinned | No | The installed wheel metadata reviewed locally did not declare a license. Re-verify the exact distribution before redistribution. | Python package installed from the configured package index |
| Codex CLI / `openai-codex-cli-bin` | Optional runtime used by the Codex SDK | 0.137.0a4 dependency observed; a newer external binary may be selected by env | No | Installed CLI-bin metadata states Apache-2.0; official Codex CLI upstream is Apache-2.0. This does not by itself resolve the separate Python SDK row above. | [openai/codex](https://github.com/openai/codex) |

## Contest Submission Boundary

SongRyeon Core is submitted as an open-source local investigation-agent and audit-runtime
prototype. The reproducible reviewer command is:

```powershell
python main.py competition-demo
```

The command uses deterministic test doubles and performs zero external API calls and zero
Neo4j connections. Optional live paths and their setup are documented in [`DEMO.md`](DEMO.md).

## Before Redistributing Optional Runtimes

1. Verify the exact model artifact and model license.
2. Verify the exact `openai-codex` Python distribution license; do not substitute the Codex
   CLI repository license without evidence.
3. Follow the Neo4j DBMS terms separately from the Python driver terms.
4. Generate a machine-readable dependency inventory or SBOM if optional runtimes are ever
   bundled into a release artifact.
