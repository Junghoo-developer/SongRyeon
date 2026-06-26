# TMP ORDER 036: Document Snapshot And Hash Index

## 목표

내부 문서의 변경 여부를 감지하는 snapshot/hash index를 만든다.

## 배경

임베딩 캐시와 장기기억 신뢰도를 위해 문서가 언제 바뀌었는지 알아야 한다.

## 범위

1. Markdown 문서별 doc_id, path, size, modified_at, content_hash를 기록한다.
2. snapshot_id를 만든다.
3. search_docs 결과에 snapshot_id를 포함한다.
4. 문서 삭제/추가/변경을 구분한다.

## 완료 기준

- 같은 문서 상태에서는 snapshot_id가 유지된다.
- 문서 하나를 바꾸면 snapshot_id가 달라진다.

## 제외

- 실시간 파일 감시.
- 충돌 해결.
