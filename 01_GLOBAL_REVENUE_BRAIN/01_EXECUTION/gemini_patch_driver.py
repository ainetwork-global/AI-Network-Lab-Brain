from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from google import genai

MODEL = os.environ.get("BRAIN_GEMINI_MODEL", "gemini-3-flash-preview")
MAX_CONTEXT_CHARS = 140_000
BLOCKED_PREFIXES = (
    ".git/", ".github/", ".env", "secrets", "credentials",
)
TEXT_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".c", ".cc",
    ".cpp", ".h", ".hpp", ".json", ".toml", ".yaml", ".yml", ".md",
}


def git(source: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=source, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )
    return result.stdout


def select_context(source: Path, task: str) -> str:
    terms = {
        term.lower() for term in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", task)
        if term.lower() not in {"this", "that", "with", "from", "implementation", "requirements"}
    }
    files = git(source, "ls-files").splitlines()
    ranked: list[tuple[int, str]] = []
    for name in files:
        path = Path(name)
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        lowered = name.lower()
        score = sum(3 for term in terms if term in lowered)
        if path.name.lower() in {"readme.md", "package.json", "pyproject.toml", "cargo.toml", "go.mod"}:
            score += 5
        if "test" in lowered or "spec" in lowered:
            score += 2
        ranked.append((score, name))
    ranked.sort(key=lambda item: (-item[0], len(item[1]), item[1]))

    chunks: list[str] = []
    used = 0
    for _, name in ranked:
        path = source / name
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if len(text) > 30_000:
            text = text[:30_000] + "\n[TRUNCATED]\n"
        block = f"\n--- FILE: {name} ---\n{text}\n"
        if used + len(block) > MAX_CONTEXT_CHARS:
            continue
        chunks.append(block)
        used += len(block)
    return "".join(chunks)


def extract_diff(output: str) -> str:
    fenced = re.search(r"```(?:diff)?\s*\n(.*?)\n```", output, re.S)
    patch = fenced.group(1) if fenced else output
    start = patch.find("diff --git ")
    if start < 0:
        raise ValueError("Model did not return a unified git diff.")
    return patch[start:].strip() + "\n"


def validate_paths(patch: str) -> None:
    paths = re.findall(r"^\+\+\+ b/(.+)$", patch, re.M)
    if not paths:
        raise ValueError("Patch has no target files.")
    for name in paths:
        lowered = name.lower()
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError(f"Unsafe patch path: {name}")
        if lowered.startswith(BLOCKED_PREFIXES):
            raise ValueError(f"Protected path rejected: {name}")
        if any(word in lowered for word in ("secret", "credential", "private_key", "wallet")):
            raise ValueError(f"Sensitive path rejected: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()
    source = Path(args.source).resolve()
    prompt_path = Path(args.prompt).resolve()

    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY is unavailable.", file=sys.stderr)
        return 2

    task = prompt_path.read_text(encoding="utf-8")
    context = select_context(source, task)
    instruction = f"""You are a senior software engineer operating in a guarded coding pipeline.
Implement the requested task using only the repository context below.

Hard rules:
- Return exactly one unified git diff beginning with 'diff --git'.
- Make the smallest complete change and add or update automated tests.
- Do not modify .github, workflows, credentials, secrets, wallets, payment code,
  lockfiles, dependency manifests, generated files, or unrelated code.
- Do not use network access, claim a bounty, publish anything, or invent test results.
- If the task cannot be solved from this context, return the exact text NO_SAFE_PATCH.

TASK:
{task}

REPOSITORY CONTEXT:
{context}
"""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    interaction = client.interactions.create(model=MODEL, input=instruction)
    output = interaction.output_text or ""
    if output.strip() == "NO_SAFE_PATCH":
        print(output, file=sys.stderr)
        return 3
    patch = extract_diff(output)
    validate_paths(patch)
    patch_file = source.parent / "MODEL.patch"
    patch_file.write_text(patch, encoding="utf-8")
    check = subprocess.run(
        ["git", "apply", "--check", str(patch_file)], cwd=source,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if check.returncode:
        print(check.stdout, file=sys.stderr)
        return 4
    applied = subprocess.run(
        ["git", "apply", str(patch_file)], cwd=source,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    print(f"Gemini patch applied with model {MODEL}.")
    return applied.returncode


if __name__ == "__main__":
    raise SystemExit(main())
