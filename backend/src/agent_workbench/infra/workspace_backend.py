"""Workspace-scoped Deep Agents backend helpers."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from deepagents.backends import LocalShellBackend
from deepagents.backends.protocol import EditResult, LsResult, WriteResult

from ..services.bms_validation import validate_bms_file
from ..services.topology_layout import reshape_architecture_for_topology

HOST_PATH_PREFIXES = ("Users/", "home/", "private/", "var/", "tmp/", "Volumes/")

BMS_OUTPUT_RE = re.compile(
    r"^bms/(architecture\.bms\.json|safety_rules\.ya?ml|components/[^/]+\.json)$",
    re.IGNORECASE,
)
BMS_JSON_READ_LIMIT = 500
DEFAULT_AGENT_READ_LIMIT = 100


class WorkspacePathError(ValueError):
    """Raised when a tool path escapes the active workspace."""


def is_host_filesystem_path(path: str) -> bool:
    bare = path.lstrip("/")
    return any(bare.startswith(prefix) for prefix in HOST_PATH_PREFIXES)


def normalize_virtual_path(path: str, workspace_root: Path) -> str:
    """Rewrite host paths under `workspace_root` to virtual workspace paths."""
    raw = (path or "/").strip() or "/"
    if raw in {".", "/"}:
        return "/"

    root = workspace_root.resolve()
    root_posix = root.as_posix().rstrip("/")
    normalized = raw.rstrip("/")

    if normalized == root_posix or normalized.startswith(f"{root_posix}/"):
        suffix = normalized[len(root_posix) :] or "/"
        return suffix if suffix.startswith("/") else f"/{suffix}"

    if not raw.startswith("/"):
        return f"/{raw.lstrip('/')}"

    if is_host_filesystem_path(raw):
        try:
            resolved = Path(raw).resolve()
            relative = resolved.relative_to(root)
        except ValueError as exc:
            raise WorkspacePathError(
                f"Path '{raw}' is outside the active workspace ({root_posix}). "
                "Use workspace paths like `/bms/architecture.bms.json` — not host paths under /Users/... "
                "The workspace root is the full project scope for this session."
            ) from exc
        return "/" if relative.as_posix() == "." else f"/{relative.as_posix()}"

    return raw


def workspace_relative_path(path: str, workspace_root: Path) -> str:
    """Return a normalized workspace-relative path without a leading slash."""
    virtual = normalize_virtual_path(path, workspace_root)
    return virtual.lstrip("/")


def is_bms_output_path(path: str) -> bool:
    return bool(BMS_OUTPUT_RE.match(path.replace("\\", "/").lstrip("/")))


def prepare_bms_write_content(path: str, content: str) -> tuple[str, str | None]:
    """Normalize and validate BMS artifact content before the agent writes it."""
    normalized = path.replace("\\", "/").lstrip("/")
    write_content = content

    if normalized.endswith(".bms.json"):
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            return content, f"Invalid JSON in BMS architecture file: {exc.msg} at line {exc.lineno}"
        if "templates/" not in normalized:
            data.pop("template_meta", None)
            data = reshape_architecture_for_topology(data)
            write_content = json.dumps(data, indent=2) + "\n"

    try:
        validate_bms_file(normalized, write_content)
    except ValueError as exc:
        return write_content, str(exc)

    return write_content, None


class WorkspaceLocalShellBackend(LocalShellBackend):
    """Local shell backend that accepts host paths under the active workspace."""

    def __init__(self, root_dir: str | Path, **kwargs) -> None:
        kwargs.setdefault("virtual_mode", True)
        super().__init__(root_dir=root_dir, **kwargs)
        self._workspace_root = Path(root_dir).resolve()

    def _resolve_path(self, key: str) -> Path:
        return super()._resolve_path(normalize_virtual_path(key, self._workspace_root))

    def ls(self, path: str) -> LsResult:
        try:
            return super().ls(path)
        except WorkspacePathError as exc:
            return LsResult(error=str(exc), entries=[])

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        """Return full `.bms.json` files on first read — default agent limit is 100 lines."""
        relative = workspace_relative_path(file_path, self._workspace_root)
        if (
            relative.endswith(".bms.json")
            and offset == 0
            and limit <= DEFAULT_AGENT_READ_LIMIT
        ):
            limit = BMS_JSON_READ_LIMIT
        return super().read(file_path, offset=offset, limit=limit)

    def write(self, file_path: str, content: str) -> WriteResult:
        relative = workspace_relative_path(file_path, self._workspace_root)
        if is_bms_output_path(relative):
            prepared, error = prepare_bms_write_content(relative, content)
            if error:
                return WriteResult(error=error)
            resolved = self._resolve_path(file_path)
            if resolved.exists():
                return self._write_overwrite(file_path, prepared)
            return super().write(file_path, prepared)
        return super().write(file_path, content)

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,  # noqa: FBT001, FBT002
    ) -> EditResult:
        relative = workspace_relative_path(file_path, self._workspace_root)
        if is_bms_output_path(relative):
            read_result = self.read(file_path)
            if read_result.error or read_result.file_data is None:
                return super().edit(file_path, old_string, new_string, replace_all=replace_all)

            from deepagents.backends.utils import perform_string_replacement

            current = read_result.file_data["content"]
            if isinstance(current, list):
                current = "".join(current)
            replacement = perform_string_replacement(current, old_string, new_string, replace_all)
            if isinstance(replacement, str):
                return EditResult(error=replacement)

            _, error = prepare_bms_write_content(relative, replacement)
            if error:
                return EditResult(error=error)

        return super().edit(file_path, old_string, new_string, replace_all=replace_all)

    def _write_overwrite(self, file_path: str, content: str) -> WriteResult:
        try:
            resolved_path = self._resolve_path(file_path)
        except (OSError, RuntimeError) as exc:
            return WriteResult(error=f"Error writing file '{file_path}': {exc}")

        try:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(resolved_path, flags, 0o644)
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(content)
            return WriteResult(path=file_path)
        except (OSError, UnicodeEncodeError) as exc:
            return WriteResult(error=f"Error writing file '{file_path}': {exc}")
