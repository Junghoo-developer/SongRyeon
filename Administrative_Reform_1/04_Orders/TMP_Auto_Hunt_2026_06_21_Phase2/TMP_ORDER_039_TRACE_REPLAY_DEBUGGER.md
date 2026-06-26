# TMP ORDER 039: Trace Replay Debugger

## 목표

저장된 trace/data 산출물을 사람이 읽기 좋게 재생하는 디버거를 만든다.

## 배경

trace와 DataStore가 늘어나면 콘솔 출력만으로 흐름을 파악하기 어렵다.

## 범위

1. `python main.py replay <run_id>` 명령 후보를 만든다.
2. trace 순서대로 actor, event_type, input_ref, output_ref를 출력한다.
3. DataStore record가 있으면 schema_name과 핵심 필드를 함께 보여준다.
4. Markdown 보고서 형태로도 출력할 수 있게 한다.

## 완료 기준

- dry_run 산출물을 재생해서 L루프 흐름을 확인할 수 있다.
- 누락된 data_id가 있으면 경고한다.

## 제외

- GUI.
- 그래프 시각화.
