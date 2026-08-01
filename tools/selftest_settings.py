#!/usr/bin/env python3
"""Assertion 3 for tools/selftest.sh: settings-key drift check.

Every doc in this repo that shows a Claude Code settings.json snippet is an
independent copy that can drift - a typo in one doc's key name would
otherwise go unnoticed until a reader hit it. This script defines the
canonical list of valid top-level settings.json keys ONCE, then extracts
every JSON code block from every .md file in the repo that looks like a
Claude Code settings snippet and asserts its top-level keys are all in that
list. A single canonical list means a typo in any doc fails this check.

Reference for the canonical list: https://docs.anthropic.com/en/claude-code/settings
"""
import json
import os
import re
import sys

# Canonical top-level settings.json keys, per the "Available settings" table
# at https://docs.anthropic.com/en/claude-code/settings. Keep this list as
# the ONLY copy of valid keys in this repo - every doc snippet is checked
# against it, nothing else.
CANONICAL_SETTINGS_KEYS = {
    "advisorModel", "agent", "agentPushNotifEnabled", "allowAllClaudeAiMcps",
    "allowManagedHooksOnly", "allowManagedMcpServersOnly",
    "allowManagedPermissionRulesOnly", "allowedChannelPlugins",
    "allowedHttpHookUrls", "allowedMcpServers", "alwaysThinkingEnabled",
    "apiKeyHelper", "askUserQuestionTimeout", "attribution",
    "autoCompactEnabled", "autoMemoryDirectory", "autoMemoryEnabled",
    "autoMode", "autoScrollEnabled", "autoUpdatesChannel", "availableModels",
    "awaySummaryEnabled", "awsAuthRefresh", "awsCredentialExport",
    "axScreenReader", "blockedMarketplaces", "browserExternalPageTools",
    "channelsEnabled", "claudeMd", "claudeMdExcludes", "cleanupPeriodDays",
    "companyAnnouncements", "defaultShell", "deniedMcpServers",
    "disableAgentView", "disableAllHooks", "disableArtifact",
    "disableAutoMode", "disableBrowserExternalNavigation",
    "disableBundledSkills", "disableClaudeAiConnectors",
    "disableDeepLinkRegistration", "disableMobileSimulatorTools",
    "disableRemoteControl", "disableSideloadFlags",
    "disableSkillShellExecution", "disableWorkflows",
    "disabledMcpjsonServers", "editorMode", "effortLevel",
    "emojiCompletionEnabled", "enableAllProjectMcpServers", "enableArtifact",
    "enabledMcpjsonServers", "enforceAvailableModels", "env",
    "fallbackModel", "fastMode", "fastModePerSessionOptIn",
    "feedbackSurveyRate", "fileCheckpointingEnabled", "fileSuggestion",
    "footerLinksRegexes", "forceLoginGatewayUrl", "forceLoginMethod",
    "forceLoginOrgUUID", "forceRemoteSettingsRefresh", "gcpAuthRefresh",
    "hooks", "httpHookAllowedEnvVars", "includeGitInstructions",
    "inputNeededNotifEnabled", "language", "minimumVersion", "model",
    "modelOverrides", "otelHeadersHelper", "outputStyle",
    "parentSettingsBehavior", "permissions", "plansDirectory",
    "pluginSuggestionMarketplaces", "pluginTrustMessage", "policyHelper",
    "prUrlTemplate", "preferredNotifChannel", "prefersReducedMotion",
    "processWrapper", "remote", "remoteControlAtStartup",
    "requiredMaximumVersion", "requiredMinimumVersion", "respectGitignore",
    "respondToBashCommands", "showClearContextOnPlanAccept",
    "showThinkingSummaries", "showTurnDuration", "skillListingBudgetFraction",
    "skillListingMaxDescChars", "skillOverrides", "skipWebFetchPreflight",
    "spinnerTipsEnabled", "spinnerTipsOverride", "spinnerVerbs",
    "sshConfigs", "statusLine", "strictKnownMarketplaces",
    "strictPluginOnlyCustomization", "switchModelsOnFlag",
    "syntaxHighlightingDisabled", "teammateMode",
    "terminalProgressBarEnabled", "theme", "tui", "ultracode",
    "useAutoModeDuringPlan", "verbose", "viewMode", "vimInsertModeRemaps",
    "voice", "voiceEnabled", "wheelScrollAccelerationEnabled",
    "workflowKeywordTriggerEnabled", "workflowSizeGuideline",
    "wslInheritsWindowsSettings",
    # Also legitimate at the top of settings.json but documented under
    # nested sections rather than the main table:
    "includeCoAuthoredBy",
}

FENCE_RE = re.compile(r"```json\n(.*?)```", re.DOTALL)
COMMENT_LINE_RE = re.compile(r"^\s*//.*$", re.MULTILINE)

# How far back (characters) to look before a fence for introducing prose.
# Docs in this repo introduce a settings block with a line mentioning
# .claude/settings.json (or settings.local.json) shortly above the fence -
# that phrase survives every possible key typo inside the block, so it is
# the primary signal for "this is a settings snippet". A handful of lines
# is enough; this is a character budget rather than a line count so it
# doesn't matter how long individual lines are.
PROSE_LOOKBACK_CHARS = 400
SETTINGS_PROSE_RE = re.compile(r"\.claude/settings|settings\.local\.json|settings\.json", re.IGNORECASE)


def _canonical_case_insensitive_map():
    return {k.lower(): k for k in CANONICAL_SETTINGS_KEYS}


CANONICAL_LOWER_MAP = _canonical_case_insensitive_map()


def find_md_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for name in filenames:
            if name.endswith(".md"):
                yield os.path.join(dirpath, name)


def strip_comment_lines(block):
    """Doc snippets sometimes annotate a block with a leading // comment
    line naming the file it belongs in. That is not valid JSON, so strip
    whole-line // comments before parsing."""
    return COMMENT_LINE_RE.sub("", block)


def key_line_number(block_start_line, block_text, key):
    """Best-effort line number for a specific top-level key within a block,
    for a debuggable failure message."""
    pattern = re.compile(r'^\s*"' + re.escape(key) + r'"\s*:', re.MULTILINE)
    m = pattern.search(block_text)
    if not m:
        return block_start_line
    return block_start_line + block_text[: m.start()].count("\n")


def check_repo(root):
    """Returns (checked_count, failures). failures is a list of dicts with
    file, line, key, block_start_line, and an optional near_miss key."""
    failures = []
    checked = 0
    for path in find_md_files(root):
        rel = os.path.relpath(path, root).replace("\\", "/")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for m in FENCE_RE.finditer(text):
            raw_block = m.group(1)
            block_start_line = text[: m.start()].count("\n") + 2  # first line inside fence
            cleaned = strip_comment_lines(raw_block)
            try:
                parsed = json.loads(cleaned)
            except Exception:
                # Not a standalone parseable JSON object (partial fragment,
                # unrelated example, etc.) - not a settings snippet, skip.
                continue
            if not isinstance(parsed, dict):
                continue
            top_keys = set(parsed.keys())

            # Signal A: introducing prose just above the fence names
            # settings.json. This is the primary signal - it does not
            # depend on any key inside the block being spelled correctly,
            # so a block whose ONLY key is a typo of a real key is still
            # caught (this is the case the key-intersection signal alone
            # misses).
            lookback_start = max(0, m.start() - PROSE_LOOKBACK_CHARS)
            preceding = text[lookback_start:m.start()]
            introduced_by_prose = bool(SETTINGS_PROSE_RE.search(preceding))

            # Signal B: at least one top-level key is already a real
            # settings key. Kept as an OR so a block with no introducing
            # prose but obviously-correct keys is still checked.
            has_known_key = bool(top_keys & CANONICAL_SETTINGS_KEYS)

            if not (introduced_by_prose or has_known_key):
                continue
            checked += 1
            bad_keys = top_keys - CANONICAL_SETTINGS_KEYS
            for key in sorted(bad_keys):
                near_miss = CANONICAL_LOWER_MAP.get(key.lower())
                if near_miss == key:
                    near_miss = None
                failures.append({
                    "file": rel,
                    "key": key,
                    "line": key_line_number(block_start_line, raw_block, key),
                    "near_miss": near_miss,
                })
    return checked, failures


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    checked, failures = check_repo(root)

    if checked == 0:
        # A zero-block result means the extractor found nothing to check,
        # not that everything checked out clean. If the fence pattern or
        # prose signal ever stops matching real docs, this is what should
        # go red instead of the suite quietly going green with nothing
        # under test.
        print(
            "FAIL: found 0 settings-like JSON blocks in this repo's .md files. "
            "This means the check did not run, not that it passed - the "
            "extractor (fence pattern or introducing-prose signal in "
            "tools/selftest_settings.py) is not matching anything.",
            file=sys.stderr,
        )
        sys.exit(1)

    if failures:
        print("FAIL: settings-key drift detected in the following doc snippets:", file=sys.stderr)
        for f in failures:
            line = f"  {f['file']}:{f['line']}: unknown settings key \"{f['key']}\""
            if f["near_miss"]:
                line += f" (case near-miss of canonical key \"{f['near_miss']}\")"
            print(line, file=sys.stderr)
        print(
            f"Checked {checked} settings-like JSON block(s) across the repo's .md files.",
            file=sys.stderr,
        )
        print(
            "Canonical key list is defined once in tools/selftest_settings.py "
            "(see https://docs.anthropic.com/en/claude-code/settings).",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"OK: {checked} settings-like JSON block(s) checked, all keys valid.")
    sys.exit(0)


if __name__ == "__main__":
    main()
