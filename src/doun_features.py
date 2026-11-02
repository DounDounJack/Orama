"""Doun Industries: features removed from this build.

Email, Calendar, Gallery and Tasks are taken out of the app. Their UI entry
points are hidden in static/css/email-calendar-notes-tasks.css (bottom block)
and their slash commands / shortcuts removed; here we make sure the AI can't
use the matching tools either, and the built-in email tool server isn't
started.

To bring a feature back, remove its names from these sets and delete the
matching CSS selectors.
"""

REMOVED_FEATURES = frozenset({"email", "calendar", "gallery", "tasks"})

# Built-in MCP tool servers not to start (src/builtin_mcp.py).
REMOVED_MCP_SERVERS = frozenset({"email"})

# Agent tools that only make sense with the removed features.
REMOVED_TOOLS = frozenset({
    # email
    "archive_email", "block_sender", "bulk_email", "delete_email",
    "download_attachment", "draft_email", "draft_email_reply",
    "list_email_accounts", "list_emails", "manage_email_state",
    "mark_email_read", "read_email", "reply_to_email",
    "scan_email_unsubscribes", "scan_spam", "search_emails", "send_email",
    "unsubscribe_email", "manage_contact", "resolve_contact",
    # calendar
    "manage_calendar",
    # tasks (scheduled background tasks; the agent's own todo list stays)
    "manage_tasks",
})
