from __future__ import annotations
import threading
from contextlib import contextmanager
from typing import Optional

try:
    from colorama import Fore, Style, init as _colorama_init
    _colorama_init(autoreset=True)
except Exception:
    # Fallback definitions if colorama is not installed yet
    class _Dummy:
        RESET_ALL = ""
    class Fore:
        GREEN = ""
        CYAN = ""
        YELLOW = ""
        MAGENTA = ""
        RED = ""
        BLUE = ""
    Style = _Dummy()


class TreeLogger:
    """A simple tree structured logger with color support.

    Usage:
        log = TreeLogger(node_id='abcd')
        with log.branch('BOOT'):
            log.log('Started')
            with log.branch('DISCOVERY'):
                log.log('ping', target='aa11')
"""

    _local = threading.local()

    def __init__(self, node_id: Optional[str] = None, indent: int = 2):
        self.node_id = node_id or "-"
        self.indent = indent
        # stack is per-thread
        if not hasattr(TreeLogger._local, "stack"):
            TreeLogger._local.stack = []
        # track printed group headers so we only print them once
        if not hasattr(TreeLogger._local, "printed_groups"):
            TreeLogger._local.printed_groups = set()
        # config: width of node id column (SHA1 hex = 40)
        self.node_width = 40

    @property
    def _stack(self):
        # ensure each thread has its own stack list
        if not hasattr(TreeLogger._local, "stack"):
            TreeLogger._local.stack = []
        return TreeLogger._local.stack

    @contextmanager
    def branch(self, operation: str, last: bool = False):
        """Enter a nested branch; yields a logger for that scope.

        last=True marks this branch as the last child at its level (affects marker).
        """
        # push tuple (name, last)
        self._stack.append((operation, bool(last)))
        try:
            yield self
        finally:
            self._stack.pop()

    def _prefix(self) -> str:
        # build a prettier tree-like prefix using classic tree chars
        if not self._stack:
            return f"{Fore.GREEN}{self.node_id}{Style.RESET_ALL} "

        parts = []
        depth = len(self._stack)
        for i, tpl in enumerate(self._stack):
            # tpl is (op_name, last_flag) for branch entries
            if isinstance(tpl, tuple):
                op, last_flag = tpl
            else:
                op, last_flag = tpl, False

            if i < depth - 1:
                # ancestor levels: show vertical column
                parts.append(f"{Fore.MAGENTA}│   {Style.RESET_ALL}")
            else:
                # final level shows branch marker and operation name; if last_flag then use '└───'
                marker = "└───" if last_flag else "├───"
                parts.append(f"{Fore.CYAN}{marker}{op}{Style.RESET_ALL}")

        return f"{Fore.GREEN}{self.node_id}{Style.RESET_ALL} " + "".join(parts) + " "

    def log(self, message: str, **meta):
        """Log a message with optional metadata printed as key=val.

        This writes to stdout using print to keep things simple for tests.
        """
        # backwards-compatible: accept optional 'group' kwarg to group logs
        group = meta.pop("group", None)
        op_name = message
        # color mapping by operation name (adjust as needed)
        color = Fore.MAGENTA
        if op_name and isinstance(op_name, str):
            if op_name.upper().startswith("WELCOME"):
                color = Fore.GREEN
            elif op_name.upper().startswith("STORE") or op_name.upper().startswith("SET"):
                color = Fore.BLUE
            else:
                color = Fore.CYAN

        # If a group is provided, ensure its header(s) are printed once
        if group:
            self._print_group_headers(group)

        # Allow explicit node_id in kwargs
        nid = meta.pop("node_id", None) or getattr(self, "node_id", None)
        meta_s = "".join([f" {Fore.YELLOW}{k}{Style.RESET_ALL}={v}" for k, v in meta.items()])

        # Build entry line: indent according to group depth (if any)
        marker = "├───"
        last = bool(meta.pop("last", False))
        if last:
            marker = "└───"

        if group:
            depth = len(group.split("/"))
            indent_prefix = "│   " * (depth - 1)
            entry_prefix = f"{indent_prefix}{marker}"
        else:
            entry_prefix = marker if self._stack else ""

        # format node id into fixed width column
        nid_str = (nid or "-")[: self.node_width].ljust(self.node_width)
        id_part = f"| {color}{nid_str}{Style.RESET_ALL} |"

        # align operation column by a single space (node_id fixed width ensures alignment)
        print(f"{entry_prefix} {id_part} {op_name}{meta_s}")

    def _print_group_headers(self, group: str):
        # Print each level of the group if not yet printed
        # ensure thread-local printed_groups exists for this thread
        if not hasattr(TreeLogger._local, "printed_groups"):
            TreeLogger._local.printed_groups = set()
        printed = TreeLogger._local.printed_groups
        parts = group.split("/")
        for i in range(len(parts)):
            path = "/".join(parts[: i + 1])
            if path in printed:
                continue
            # compute indentation for this level
            indent = "    " * i
            # choose marker: if it's the last element in the group path, use '└───' else '├───'
            marker = "└───" if i == len(parts) - 1 else "├───"
            line = f"{indent}{marker}{parts[i]}"
            print(line)
            printed.add(path)


# convenience global
default_logger: Optional[TreeLogger] = None


def init_logger(node_id: Optional[str] = None) -> TreeLogger:
    global default_logger
    default_logger = TreeLogger(node_id=node_id)
    return default_logger
