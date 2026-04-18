from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.rule import Rule

console = Console()
GREEN_EVENTS = {"subscription.created", "subscription.renewed", "subscription.activated"}
RED_EVENTS = {"subscription.deactivated", "subscription.deleted", "order.refunded", "order.suspended"}


def event_style(event: str) -> tuple[str, str]:
    if event.startswith("member_"):
        return event, "cyan"
    if event in GREEN_EVENTS:
        return event, "green"
    if event == "subscription.updated":
        return event, "yellow"
    if event in RED_EVENTS:
        return event, "red"
    if event == "order.purchased":
        return event, "magenta"
    if event.startswith(("download.", "plan.")):
        return event, "blue"
    return f"[?] {event or 'unknown event'}", "white"


def nested(payload: dict[str, Any], *keys: str) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def member_line(member: dict[str, Any] | None) -> str | None:
    if not member:
        return None
    name = member.get("full_name") or " ".join(part for part in [member.get("first_name"), member.get("last_name")] if part)
    email = member.get("email")
    return f"{name} <{email}>" if name and email else name or email


def money(amount: Any) -> str | None:
    if amount is None:
        return None
    try:
        return f"${float(amount) / 100:.2f}"
    except (TypeError, ValueError):
        return str(amount)


def plan_line(plan: dict[str, Any] | None) -> str | None:
    if not plan:
        return None
    detail = "/".join(part for part in [money(plan.get("price_cents") or plan.get("amount_cents") or plan.get("price")), plan.get("interval") or plan.get("period")] if part)
    return f"{plan.get('name')} ({detail})" if plan.get("name") and detail else plan.get("name") or detail


def top_level_fields(payload: dict[str, Any]) -> list[tuple[str, Any]]:
    return [(key.replace("_", " ").title(), value) for key, value in payload.items() if key != "event"]


def collect_fields(event: str, payload: dict[str, Any]) -> list[tuple[str, Any]]:
    member = payload.get("member") if isinstance(payload.get("member"), dict) else {}
    subscription = payload.get("subscription") if isinstance(payload.get("subscription"), dict) else {}
    order = payload.get("order") if isinstance(payload.get("order"), dict) else {}
    if event.startswith("member_"):
        fields = [("Member", member_line(member) or member_line(payload)), ("Member ID", member.get("id") or payload.get("id")), ("Status", member.get("status") or payload.get("status")), ("Created", member.get("created_at") or payload.get("created_at"))]
    elif event.startswith("subscription."):
        sub_id = subscription.get("id") or payload.get("subscription_id")
        status = subscription.get("status")
        autorenew = subscription.get("autorenew", subscription.get("auto_renew"))
        autorenew = str(autorenew).lower() if isinstance(autorenew, bool) else autorenew
        fields = [
            ("Member", member_line(member)),
            ("Member ID", member.get("id")),
            ("Plan", plan_line(payload.get("plan") if isinstance(payload.get("plan"), dict) else nested(subscription, "plan"))),
            ("Subscription", f"#{sub_id} - {status}, autorenew: {autorenew}" if sub_id else status),
            ("Created", subscription.get("created_at") or payload.get("created_at")),
        ]
    elif event.startswith("order."):
        total = order.get("total_cents") or order.get("amount_cents") or payload.get("total_cents")
        fields = [("Member", member_line(member)), ("Order ID", order.get("id") or payload.get("order_id")), ("Total", money(total)), ("Status", order.get("status") or payload.get("status")), ("Created", order.get("created_at") or payload.get("created_at"))]
    else:
        fields = top_level_fields(payload)
    return [(label, value) for label, value in fields[:6] if value not in (None, "", {})]


def print_event(payload: dict[str, Any], log_file: str) -> None:
    event = str(payload.get("event") or payload.get("type") or "unknown")
    title, style = event_style(event)
    console.print(Rule(style=style))
    console.print(f"  :incoming_envelope: [{style}]{title:<36}[/{style}] {datetime.now().strftime('%H:%M:%S')}")
    console.print(Rule(style=style))
    for label, value in collect_fields(event, payload):
        console.print(f"  [bold]{label + ':':<14}[/bold] {value}")
    console.print()
    console.print(f"  [dim]Full payload logged to {Path(log_file)}[/dim]")
    console.print(Rule(style=style))
