# Third-Party Components And License Notes

This document is a practical disclosure note for contest review and public repository readers.
It is not legal advice.

## Project Code

- SongRyeon Core source code: MIT License
- License file: `LICENSE`

## Included Model Weights

- No model weights are included in this repository.
- The default no-model demo path uses `fake-turn`.
- Live LLM paths are optional and depend on the user's local model setup.

## Optional Runtime Components

| Component | Role | License / note |
| --- | --- | --- |
| pytest | Development and regression tests | MIT License |
| Ollama Python library | Optional local LLM adapter path | MIT License |
| Qwen model configured through Ollama or compatible local endpoint | Optional local live LLM | Model weights are not included. Users must follow the exact model artifact license they configure. |
| Neo4j Python driver | Optional local Vessel graph DB adapter | Apache License 2.0 unless stated otherwise by the upstream package |
| Neo4j DBMS | Optional local graph database service | Not bundled in this repository. Users must follow Neo4j's own distribution and usage terms. |

## Contest Submission Note

SongRyeon Core is submitted as an agent runtime and audit architecture prototype.
It is not submitted as a hosted closed-API wrapper and does not include proprietary model weights.

The repository's deterministic demo path can run without Qwen, Ollama, Neo4j, or external API calls:

```powershell
python main.py fake-turn "송련이 뭔지 짧게 설명해줘" --pretty
```

Optional live paths are documented separately in `DEMO.md`.
