"""대회 제출용 A/R 근거 권한 holdout 비교실험."""

__all__ = [
    "build_blind_packet",
    "freeze_experiment",
    "load_study",
    "lock_blind_scores",
    "unblind_summary",
    "verify_freeze",
    "verify_public_result",
    "verify_unblinded_summary",
]


def __getattr__(name):
    """CLI 모듈을 미리 import하지 않으면서 작은 공개 API를 유지한다."""

    if name in {"freeze_experiment", "load_study", "verify_freeze"}:
        from . import protocol

        return getattr(protocol, name)
    if name in {
        "build_blind_packet", "lock_blind_scores", "unblind_summary",
        "verify_public_result", "verify_unblinded_summary",
    }:
        from . import scorer

        return getattr(scorer, name)
    raise AttributeError(name)
