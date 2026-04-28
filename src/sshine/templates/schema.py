from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sshine.exceptions import TemplateJinja2RequiredError, TemplateValidationError

_JINJA2_PATTERN = re.compile(r"\{%-?\s*(if|for|block|macro|set|with|extends|include)\b")
_VAR_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")

BUILTIN_ACTIONS = {
    "shell",
    "user.create",
    "ssh.keygen",
    "ssh.authorize",
    "package.install",
    "docker.install",
}


@dataclass
class TemplateStep:
    name: str | None
    action: str
    params: dict[str, Any]
    condition: str | None = None  # `if:` field


@dataclass
class TemplateDefinition:
    name: str
    description: str
    vars: dict[str, str]
    steps: list[TemplateStep]
    raw_body: str = ""


def load_template(
    path: Path | None = None,
    body: str | None = None,
) -> TemplateDefinition:
    """
    Parse a ``.inittmp`` YAML file (or raw *body* string) into a
    :class:`TemplateDefinition`.

    Raises :class:`~sshine.exceptions.TemplateValidationError` on schema errors.
    Raises :class:`~sshine.exceptions.TemplateJinja2RequiredError` if the
    template uses Jinja2 syntax (``{% %}`` blocks) and ``jinja2`` is not installed.
    """
    if path is not None:
        body = path.read_text(encoding="utf-8")
    if body is None:
        raise TemplateValidationError("No template source provided.")

    _check_jinja2_requirement(body)

    try:
        from ruamel.yaml import YAML  # type: ignore[import]

        yaml = YAML()
        data = yaml.load(body)
    except Exception as exc:
        raise TemplateValidationError(f"YAML parse error: {exc}") from exc

    if not isinstance(data, dict):
        raise TemplateValidationError("Template root must be a YAML mapping.")

    tname = data.get("name") or (path.stem if path else "unnamed")
    description = data.get("description", "")
    vars_raw = data.get("vars", {}) or {}
    if not isinstance(vars_raw, dict):
        raise TemplateValidationError("`vars` must be a YAML mapping.")

    steps_raw = data.get("steps", []) or []
    if not isinstance(steps_raw, list):
        raise TemplateValidationError("`steps` must be a YAML list.")

    steps: list[TemplateStep] = []
    for i, step in enumerate(steps_raw, start=1):
        if not isinstance(step, dict):
            raise TemplateValidationError(f"Step {i} must be a YAML mapping.")
        action = step.get("action")
        if not action:
            raise TemplateValidationError(f"Step {i} is missing `action`.")
        params = {k: v for k, v in step.items() if k not in ("name", "action", "if")}
        steps.append(
            TemplateStep(
                name=step.get("name"),
                action=action,
                params=params,
                condition=step.get("if"),
            )
        )

    return TemplateDefinition(
        name=tname,
        description=description,
        vars={str(k): str(v) for k, v in vars_raw.items()},
        steps=steps,
        raw_body=body,
    )


def render_vars(value: str, context: dict[str, str], *, use_jinja2: bool = False) -> str:
    """
    Substitute ``{{ var }}`` placeholders in *value* using *context*.

    If *use_jinja2* is True (and jinja2 is installed), delegates to the
    Jinja2 environment for full expression support.
    """
    if use_jinja2:
        try:
            import jinja2  # type: ignore[import-untyped]

            env = jinja2.Environment(undefined=jinja2.StrictUndefined)
            return env.from_string(value).render(**context)
        except ImportError:
            pass

    def _replace(m: re.Match[str]) -> str:
        key = m.group(1)
        return context.get(key, m.group(0))

    return _VAR_PATTERN.sub(_replace, value)


def evaluate_condition(condition: str, context: dict[str, str]) -> bool:
    """
    Evaluate a step ``if:`` condition.

    Supports simple ``{{ a == b }}`` / ``{{ a != b }}`` patterns, and
    delegates to Jinja2 if available for complex expressions.
    """
    rendered = render_vars(condition, context, use_jinja2=True)

    # Simple equality checks: the rendered value itself
    rendered = rendered.strip()
    if rendered.lower() in ("true", "yes", "1"):
        return True
    if rendered.lower() in ("false", "no", "0", ""):
        return False

    # Try eval via Jinja2 boolean coercion (already rendered above)
    try:
        return bool(rendered)
    except Exception:
        return True


def _check_jinja2_requirement(body: str) -> None:
    """Raise if body uses Jinja2 block syntax but jinja2 is not installed."""
    if not _JINJA2_PATTERN.search(body):
        return
    try:
        import jinja2  # type: ignore[import-untyped]  # noqa: F401
    except ImportError as exc:
        raise TemplateJinja2RequiredError from exc
