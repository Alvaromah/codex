from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import os
import shlex

ApprovalPolicy = str  # 'suggest', 'auto-edit', 'full-auto'

@dataclass
class SafetyAssessment:
    type: str
    reason: Optional[str] = None
    group: Optional[str] = None
    run_in_sandbox: bool = False


SAFE_COMMANDS = {
    "cd": ("Change directory", "Navigating"),
    "ls": ("List directory", "Searching"),
    "pwd": ("Print working directory", "Navigating"),
    "true": ("No-op", "Utility"),
    "echo": ("Echo string", "Printing"),
    "cat": ("View file contents", "Reading files"),
    "nl": ("View file with line numbers", "Reading files"),
    "rg": ("Ripgrep search", "Searching"),
    "grep": ("Text search", "Searching"),
    "head": ("Show file head", "Reading files"),
    "tail": ("Show file tail", "Reading files"),
    "wc": ("Word count", "Reading files"),
    "which": ("Locate command", "Searching"),
}


def is_safe_command(cmd: List[str]) -> Optional[Tuple[str, str]]:
    info = SAFE_COMMANDS.get(cmd[0])
    if info:
        return info
    if cmd[0] == "git" and len(cmd) > 1:
        sub = cmd[1]
        if sub in {"status", "branch", "log", "diff", "show"}:
            return (f"Git {sub}", "Using git")
    if cmd[0] == "cargo" and len(cmd) > 1 and cmd[1] == "check":
        return ("Cargo check", "Running command")
    if cmd[0] == "find":
        unsafe = {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fls", "-fprint", "-fprint0", "-fprintf"}
        if any(arg in unsafe for arg in cmd):
            return None
        return ("Find files", "Searching")
    if cmd[0] == "sed" and len(cmd) >= 3 and cmd[1] == "-n" and _valid_sed_n(cmd[2]):
        return ("Sed print subset", "Reading files")
    return None


def _valid_sed_n(arg: str) -> bool:
    import re
    return bool(re.match(r"^(\d+,)?\d+p$", arg or ""))


def can_auto_approve(command: List[str], policy: ApprovalPolicy) -> SafetyAssessment:
    safe = is_safe_command(command)
    if safe:
        reason, group = safe
        return SafetyAssessment(type="auto-approve", reason=reason, group=group)
    if policy == "full-auto":
        return SafetyAssessment(
            type="auto-approve",
            reason="Full auto mode",
            group="Running commands",
            run_in_sandbox=True,
        )
    return SafetyAssessment(type="ask-user")
