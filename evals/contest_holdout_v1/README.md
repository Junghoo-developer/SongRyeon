# Contest holdout v1

현재 상태는 **동결 후보, live 출력 0개**다. 최종 코드와 package-data 정리가 끝나기 전에
동결하거나 모델을 실행하지 않는다.

최종 준비 순서:

```powershell
python -m evals.contest_holdout_v1.protocol freeze `
  --output-root .tmp/evals/contest_holdout_v1 `
  --public-proof-dir evals/contest_holdout_v1/frozen/<final-experiment-id>

# freeze 명령이 출력한 정확한 hash를 각 block의 live_capture 인자에 사용한다.
# 세 block이 끝난 뒤:
python -m evals.contest_holdout_v1.scorer packet `
  --experiment-root .tmp/evals/contest_holdout_v1
python -m evals.contest_holdout_v1.scorer score `
  --experiment-root .tmp/evals/contest_holdout_v1
python -m evals.contest_holdout_v1.scorer unblind `
  --experiment-root .tmp/evals/contest_holdout_v1 `
  --public-proof-dir evals/contest_holdout_v1/frozen/<final-experiment-id>
```

trusted packetizer만 packet 생성 때 private key를 사용한다. 채점자는 `score` 동안 key를
읽지 않고, `unblind` 전에는 `SCORE_LOCK.json`이 있어야 한다. 공개 proof 폴더는 처음에는
secret이 없는 `FREEZE.json`과 `BLINDING_COMMITMENT.json`만 가진다. 점수 lock 뒤
`unblind`는 private/public commitment가 정확히 같은지 먼저 확인한 뒤 packet, 잠긴 점수,
lock, `REVEAL.json`, `SUMMARY.json`을 추가한다. `REVEAL.json`은 live 전이나 score lock
전에 만들어지지 않는다. `SUMMARY.json`은 사람 감사 전까지 항상 `publishable=false`다.
실제 제출용 공개 판정은 원시 JSONL부터 summary까지 다시 계산하는
`publication.py`의 gate와 사람 감사 파일을 사용한다.

심사위원은 private key 없이 공개 proof를 다시 검증할 수 있다.

```powershell
python -m evals.contest_holdout_v1.protocol verify `
  --output-root evals/contest_holdout_v1/frozen/<final-experiment-id> `
  --without-key

# unblind 뒤 공개 결과 체인 검증
python -m evals.contest_holdout_v1.scorer verify-public `
  --public-proof-dir evals/contest_holdout_v1/frozen/<final-experiment-id>
```
