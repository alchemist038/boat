from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RealExecutionMode(StrEnum):
    ASSIST_REAL = "assist_real"
    ARMED_REAL = "armed_real"


class SessionStrategy(StrEnum):
    FRESH_PER_EXECUTION = "fresh_per_execution"
    BURST_REUSE = "burst_reuse"


class FlowStepType(StrEnum):
    START_BROWSER = "start_browser"
    OPEN_LOGIN_PAGE = "open_login_page"
    SUBMIT_LOGIN = "submit_login"
    WAIT_TOP_STABLE = "wait_top_stable"
    CLOSE_LOGIN_TABS = "close_login_tabs"
    CAPTURE_TOP_PAGE = "capture_top_page"
    SELECT_RACE = "select_race"
    BUILD_BET_LIST = "build_bet_list"
    OPEN_CONFIRMATION = "open_confirmation"
    PREFILL_CONFIRMATION = "prefill_confirmation"
    WAIT_MANUAL_SUBMIT = "wait_manual_submit"
    AUTO_SUBMIT = "auto_submit"
    WAIT_RESULT = "wait_result"
    LOGOUT = "logout"
    CLOSE_BROWSER = "close_browser"
    KEEP_SESSION = "keep_session"


@dataclass(frozen=True)
class FlowStep:
    step: FlowStepType
    description: str
    blocking: bool = True


@dataclass(frozen=True)
class FreshExecutorPolicy:
    session_strategy: SessionStrategy = SessionStrategy.FRESH_PER_EXECUTION
    reuse_when_next_real_within_seconds: int = 180
    post_login_settle_seconds: int = 10
    top_stable_confirm_seconds: int = 3
    logout_after_execution: bool = True
    close_browser_after_execution: bool = True


def should_keep_session(*, next_real_target_in_seconds: int | None, policy: FreshExecutorPolicy) -> bool:
    if policy.session_strategy != SessionStrategy.BURST_REUSE:
        return False
    if next_real_target_in_seconds is None:
        return False
    return 0 <= next_real_target_in_seconds < policy.reuse_when_next_real_within_seconds


def build_real_execution_steps(
    mode: RealExecutionMode,
    *,
    next_real_target_in_seconds: int | None = None,
    policy: FreshExecutorPolicy | None = None,
) -> list[FlowStep]:
    policy = policy or FreshExecutorPolicy()
    keep_session = should_keep_session(
        next_real_target_in_seconds=next_real_target_in_seconds,
        policy=policy,
    )

    steps = [
        FlowStep(FlowStepType.START_BROWSER, "Fresh executor browser を起動する"),
        FlowStep(FlowStepType.OPEN_LOGIN_PAGE, "Teleboat ログイン画面を開く"),
        FlowStep(FlowStepType.SUBMIT_LOGIN, "資格情報を入力してログインする"),
        FlowStep(
            FlowStepType.WAIT_TOP_STABLE,
            f"トップページが {policy.top_stable_confirm_seconds} 秒以上安定するのを待つ",
        ),
        FlowStep(FlowStepType.CLOSE_LOGIN_TABS, "ログイン画面や不要タブを閉じる"),
        FlowStep(FlowStepType.CAPTURE_TOP_PAGE, "トップ 1 枚を正として掴む"),
        FlowStep(FlowStepType.SELECT_RACE, "対象場と対象レースへ進む"),
        FlowStep(FlowStepType.BUILD_BET_LIST, "bet list を作る"),
        FlowStep(FlowStepType.OPEN_CONFIRMATION, "確認画面へ進む"),
        FlowStep(FlowStepType.PREFILL_CONFIRMATION, "購入金額と投票パスを入力する"),
    ]

    if mode == RealExecutionMode.ASSIST_REAL:
        steps.append(FlowStep(FlowStepType.WAIT_MANUAL_SUBMIT, "人の投票完了を待つ"))
    else:
        steps.append(FlowStep(FlowStepType.AUTO_SUBMIT, "自動で投票する"))

    steps.append(FlowStep(FlowStepType.WAIT_RESULT, "完了画面または契約番号を確認する"))

    if keep_session:
        steps.append(
            FlowStep(
                FlowStepType.KEEP_SESSION,
                f"次の real target が {policy.reuse_when_next_real_within_seconds} 秒未満なので短時間再利用する",
            )
        )
        return steps

    if policy.logout_after_execution:
        steps.append(FlowStep(FlowStepType.LOGOUT, "Teleboat からログアウトする"))
    if policy.close_browser_after_execution:
        steps.append(FlowStep(FlowStepType.CLOSE_BROWSER, "browser を閉じる"))
    return steps
