"""선택 본문을 만들기 전에 숨김 도구 원문의 무결성을 다시 확인한다."""

import json
from pathlib import Path


def _load_saved_tool_source(
    memory_path,
    source_information_id,
    turn_id,
):
    """공통 원문과 같은 도구 실행 묶음의 기록을 모두 검증해 읽는다."""

    path = Path(memory_path)

    if not path.exists():
        raise ValueError("도구 원문이 저장된 기억 로그를 찾을 수 없습니다.")

    records_by_type = {}
    turn_records = []
    source_record = None
    source_record_in_other_turn = None

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            record = json.loads(line)

            if record.get("information_id") == source_information_id:
                if record.get("turn_id") == turn_id:
                    source_record = record
                else:
                    source_record_in_other_turn = record

            if record.get("turn_id") != turn_id:
                continue

            turn_records.append(record)
            information_type = record.get("information_type")

            if (
                not isinstance(information_type, str)
                or not information_type.startswith("tool_raw_")
            ):
                continue

            if information_type in records_by_type:
                raise ValueError(
                    f"같은 종류의 도구 원문이 중복됐습니다: {information_type}"
                )

            records_by_type[information_type] = record

    if source_record is None:
        if source_record_in_other_turn is not None:
            raise ValueError("도구 원문 ID와 turn_id가 서로 일치하지 않습니다.")
        raise ValueError("선택 근거가 될 도구 원문 ID를 찾을 수 없습니다.")

    required_types = {
        "tool_raw_arguments",
        "tool_raw_content",
        "tool_raw_error",
        "tool_raw_name",
        "tool_raw_success",
    }
    missing_types = required_types - records_by_type.keys()

    if missing_types:
        raise ValueError(
            "도구 원본 기록이 완전하지 않습니다: "
            + ", ".join(sorted(missing_types))
        )

    for information_type in required_types:
        record = records_by_type[information_type]

        if (
            record.get("information_class") != "absolute"
            or record.get("code_verifiable") is not True
        ):
            raise ValueError(
                f"도구 원본은 절대정보여야 합니다: {information_type}"
            )

    success = records_by_type["tool_raw_success"]["information"]

    if not isinstance(success, bool):
        raise ValueError("tool_raw_success는 bool이어야 합니다.")

    expected_source_type = (
        "tool_raw_content"
        if success
        else "tool_raw_error"
    )

    if source_record["information_type"] != expected_source_type:
        raise ValueError(
            "도구 성공 여부와 선택 근거 원문의 종류가 일치하지 않습니다."
        )

    raw_text = source_record["information"]

    if not isinstance(raw_text, str):
        raise ValueError("선택 근거가 될 도구 원문은 문자열이어야 합니다.")

    try:
        arguments = json.loads(
            records_by_type["tool_raw_arguments"]["information"]
        )
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("저장된 도구 arguments가 올바른 JSON이 아닙니다.") from error

    if not isinstance(arguments, dict):
        raise ValueError("저장된 도구 arguments는 JSON 객체여야 합니다.")

    tool_name = records_by_type["tool_raw_name"]["information"]

    if not isinstance(tool_name, str):
        raise ValueError("저장된 도구 이름은 문자열이어야 합니다.")

    return (
        tool_name,
        arguments,
        raw_text,
        success,
        records_by_type,
        turn_records,
    )


def verify_saved_tool_source(
    memory_path,
    source_information_id,
    turn_id,
):
    """아직 보존 결정을 받지 않은 도구 원문만 반환한다."""

    (
        tool_name,
        arguments,
        raw_text,
        _,
        _,
        turn_records,
    ) = _load_saved_tool_source(
        memory_path,
        source_information_id,
        turn_id,
    )

    if any(
        record.get("information_type") == "tool_retention_applied"
        for record in turn_records
    ):
        raise ValueError(
            "이 도구 결과에는 이미 본문 보존 결정이 적용됐습니다."
        )

    return tool_name, arguments, raw_text


def _records_of_type(records, information_type):
    """한 도구 실행 묶음에서 정확한 정보 종류만 고른다."""

    return [
        record
        for record in records
        if record.get("information_type") == information_type
    ]


def _one_record(records, information_type):
    """복구 감사 사슬에 필요한 기록이 정확히 하나인지 확인한다."""

    matching = _records_of_type(records, information_type)

    if len(matching) != 1:
        raise ValueError(
            f"{information_type} 기록은 정확히 하나여야 합니다."
        )

    return matching[0]


def _load_json_object(record, information_type):
    """감사 기록에 저장된 canonical JSON 객체를 다시 읽는다."""

    try:
        value = json.loads(record.get("information"))
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError(
            f"{information_type} 기록이 올바른 JSON이 아닙니다."
        ) from error

    if not isinstance(value, dict):
        raise ValueError(f"{information_type} 기록은 JSON 객체여야 합니다.")

    return value


def verify_omitted_tool_source(
    memory_path,
    source_information_id,
    turn_id,
):
    """성공 후 한 번 omit된 원문만 최종 보존 대상으로 허용한다."""

    (
        tool_name,
        arguments,
        raw_text,
        success,
        records_by_type,
        turn_records,
    ) = _load_saved_tool_source(
        memory_path,
        source_information_id,
        turn_id,
    )

    if success is not True:
        raise ValueError("성공한 도구 원문만 최종 보존할 수 있습니다.")

    selection_source = _one_record(
        turn_records,
        "tool_raw_selection_source_id",
    )

    if (
        selection_source.get("information_class") != "absolute"
        or selection_source.get("code_verifiable") is not True
        or selection_source.get("information") != source_information_id
    ):
        raise ValueError("최초 보존 결정의 원문 연결이 올바르지 않습니다.")

    request_record = _one_record(
        turn_records,
        "node1_retention_request",
    )
    applied_record = _one_record(
        turn_records,
        "tool_retention_applied",
    )
    request = _load_json_object(
        request_record,
        "node1_retention_request",
    )
    applied = _load_json_object(
        applied_record,
        "tool_retention_applied",
    )

    if (
        request != {"end": None, "mode": "omit", "start": None}
        or applied.get("mode") != "omit"
        or applied.get("start") is not None
        or applied.get("end") is not None
        or applied.get("tool_name") != tool_name
        or applied.get("arguments") != arguments
    ):
        raise ValueError("최초 보존 결정이 정확한 omit 기록이 아닙니다.")

    _one_record(turn_records, "node1_tool_review_omit")

    if (
        applied_record.get("information_class") != "absolute"
        or applied_record.get("code_verifiable") is not True
    ):
        raise ValueError("최초 적용된 보존 결정은 절대정보여야 합니다.")

    recovery_types = {
        "tool_omit_recovery_applied",
        "tool_raw_omit_recovery_source_id",
    }

    if any(
        _records_of_type(turn_records, information_type)
        for information_type in recovery_types
    ):
        raise ValueError("이 도구 결과에는 이미 omit 복구가 적용됐습니다.")

    if _records_of_type(turn_records, "tool_result_content"):
        raise ValueError("이미 공개된 도구 원문은 omit 복구 대상이 아닙니다.")

    # 반환 직전에도 선택 근거 원문이 성공 content인지 명시적으로 고정한다.
    if (
        records_by_type["tool_raw_content"]["information_id"]
        != source_information_id
    ):
        raise ValueError("복구 원문 ID가 저장된 성공 결과와 다릅니다.")

    return tool_name, arguments, raw_text
