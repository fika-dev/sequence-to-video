#!/usr/bin/env python3
"""
Stop Hook: Check if tests need to be updated after agent completes work.

Runs when the main agent finishes. Analyzes conversation to determine if 
domain code was modified and whether corresponding tests should be updated.

Exit codes:
- 0: Allow stop (no test update needed OR already handled)  
- 2: Block stop with reason (instructs agent to update tests)
"""

import json
import sys
from pathlib import Path


def load_transcript(transcript_path: str) -> list[dict]:
    messages = []
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return messages


def extract_modified_files(messages: list[dict]) -> set[str]:
    modified_files = set()
    
    for msg in messages:
        if msg.get("type") != "tool_use":
            continue
        
        tool_name = msg.get("tool_name", "")
        tool_input = msg.get("tool_input", {})
        
        if tool_name in ("Write", "Edit", "mcp_write", "mcp_edit"):
            file_path = tool_input.get("file_path") or tool_input.get("filePath", "")
            if file_path:
                modified_files.add(file_path)
    
    return modified_files


def categorize_modified_files(files: set[str]) -> dict:
    categories = {
        "domain_code": [],
        "test_code": [],
        "other": [],
    }
    
    for f in files:
        path = Path(f)
        parts = path.parts
        
        is_test_file = "tests" in parts or "test_" in path.name or "_test.py" in path.name
        is_domain_code = "domains" in parts and path.suffix == ".py"
        
        if is_test_file:
            categories["test_code"].append(f)
        elif is_domain_code:
            categories["domain_code"].append(f)
        else:
            categories["other"].append(f)
    
    return categories


def get_affected_domains(domain_files: list[str]) -> set[str]:
    domains = set()
    for f in domain_files:
        path = Path(f)
        parts = path.parts
        try:
            domains_idx = parts.index("domains")
            if domains_idx + 1 < len(parts):
                domains.add(parts[domains_idx + 1])
        except ValueError:
            continue
    return domains


def check_if_tests_were_updated(test_files: list[str], affected_domains: set[str]) -> bool:
    for f in test_files:
        path = Path(f)
        for domain in affected_domains:
            if domain in str(path):
                return True
    return False


def check_conversation_for_test_intent(messages: list[dict]) -> bool:
    test_keywords = [
        "test update", "update test", "tests need", "테스트 업데이트",
        "test-update-hook", "check-test-update",
    ]
    
    for msg in messages:
        content = str(msg.get("content", "")).lower()
        if any(keyword in content for keyword in test_keywords):
            return True
    return False


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    
    if input_data.get("stop_hook_active", False):
        sys.exit(0)
    
    transcript_path = input_data.get("transcript_path", "")
    if not transcript_path:
        sys.exit(0)
    
    messages = load_transcript(transcript_path)
    if not messages:
        sys.exit(0)
    
    modified_files = extract_modified_files(messages)
    if not modified_files:
        sys.exit(0)
    
    categories = categorize_modified_files(modified_files)
    
    if not categories["domain_code"]:
        sys.exit(0)
    
    affected_domains = get_affected_domains(categories["domain_code"])
    if not affected_domains:
        sys.exit(0)
    
    if check_if_tests_were_updated(categories["test_code"], affected_domains):
        sys.exit(0)
    
    if check_conversation_for_test_intent(messages):
        sys.exit(0)
    
    domains_str = ", ".join(sorted(affected_domains))
    modified_str = "\n".join(f"  - {f}" for f in sorted(categories["domain_code"]))
    
    reason = f"""[TEST UPDATE CHECK]

Domain code was modified but corresponding tests were not updated.

Affected domains: {domains_str}
Modified files:
{modified_str}

Please check if tests in tests/domains/{{{domains_str}}}/ need to be updated.
If tests need updating:
1. Review tests/AGENTS.md for test structure
2. Update relevant test files to cover the changes
3. Run: uv run pytest tests/ -v

If no test update is needed, explain why and proceed."""

    print(reason, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
