"""Demo script showcasing FastBlocks syntax support and autocomplete features."""
# type: ignore  # Example file - not strict type checking

import asyncio
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from acb.config import Settings
from acb.depends import depends

from .language_server import FastBlocksLanguageClient
from .syntax_support import FastBlocksSyntaxSupport


class SyntaxDemoSettings(Settings):
    """Settings for syntax demo."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d87-3456-789a-bcde-123456789def")
    MODULE_STATUS: str = "stable"

    # Demo settings
    demo_templates_dir: str = "templates/demo"
    generate_sample_templates: bool = True
    run_interactive_demo: bool = False


async def create_sample_templates(demo_dir: Path) -> dict[str, str]:
    """Create sample FastBlocks templates for demonstration."""
    demo_dir.mkdir(parents=True, exist_ok=True)

    templates = {
        "basic.fb.html": """[# FastBlocks Basic Template Demo #]
[% extends "base.html" %]

[% block title %]Welcome to FastBlocks[% endblock %]

[% block content %]
    <div class="hero">
        <h1>[[ title | default("Welcome") ]]</h1>
        <p>[[ user.name if user else "Guest" ]]</p>

        [# User navigation with icons #]
        [% if user %]
            <nav class="user-nav">
                [[ ph_icon("user-circle", variant="fill", size="lg") | safe ]]
                <span>[[ user.email ]]</span>
                [[ ph_interactive("sign-out", action="logout()") | safe ]]
            </nav>
        [% else %]
            <a href="/login" class="login-btn">
                [[ ph_button_icon("sign-in", "Sign In", variant="bold") | safe ]]
            </a>
        [% endif %]
    </div>

    [# Dynamic content section #]
    <section class="content">
        [% for item in items %]
            <article class="item">
                <h2>[[ item.title | title ]]</h2>
                <p>[[ item.description | truncate(150) ]]</p>

                [# Component rendering #]
                [[ render_component("user_card", {
                    "name": item.author.name,
                    "email": item.author.email,
                    "avatar_url": item.author.avatar | cloudflare_img(width=64, height=64)
                }) | safe ]]

                <div class="actions">
                    [[ ph_icon("heart", interactive=True, color="danger") | safe ]]
                    [[ ph_icon("bookmark", interactive=True) | safe ]]
                    [[ ph_icon("share", interactive=True) | safe ]]
                </div>
            </article>
        [% endfor %]

        [% if not items %]
            <div class="empty-state">
                [[ ph_icon("inbox", size="3x", color="muted") | safe ]]
                <p>No items found</p>
            </div>
        [% endif %]
    </section>
[% endblock %]""",
        "advanced.fb.html": """[# Advanced FastBlocks Features Demo #]
[% extends "layouts/dashboard.html" %]

[% block head %]
    [[ phosphor_stylesheet_links() | safe ]]
    [[ webawesome_stylesheet_links() | safe ]]
[% endblock %]

[% block dashboard_content %]
    [# Error handling with syntax validation #]
    [% set user_status = get_config("user.status") | default("active") %]

    <div class="dashboard-grid">
        [# Widget with duotone icons #]
        <div class="widget stats">
            <h3>
                [[ ph_duotone("chart-bar", primary_color="#007bff", secondary_color="#e3f2fd") | safe ]]
                Analytics
            </h3>

            <div class="metrics">
                [% for metric in dashboard_metrics %]
                    <div class="metric">
                        <span class="value">[[ metric.value | number_format ]]</span>
                        <span class="label">[[ metric.label ]]</span>
                        [% if metric.trend == "up" %]
                            [[ ph_icon("trend-up", color="success", size="sm") | safe ]]
                        [% elif metric.trend == "down" %]
                            [[ ph_icon("trend-down", color="danger", size="sm") | safe ]]
                        [% else %]
                            [[ ph_icon("minus", color="muted", size="sm") | safe ]]
                        [% endif %]
                    </div>
                [% endfor %]
            </div>
        </div>

        [# Interactive notifications widget #]
        <div class="widget notifications">
            <h3>
                [[ ph_interactive("bell", variant="fill",
                    action="toggleNotifications()",
                    class="notification-toggle") | safe ]]
                Notifications ([[ notifications | length ]])
            </h3>

            [% for notification in notifications[:5] %]
                <div class="notification [[ 'unread' if not notification.read else '' ]]">
                    [[ ph_icon(notification.icon, variant="regular", size="sm") | safe ]]
                    <div class="content">
                        <p>[[ notification.message ]]</p>
                        <small>[[ notification.created_at | timeago ]]</small>
                    </div>
                    [% if not notification.read %]
                        [[ ph_interactive("check", size="xs",
                            action="markAsRead(" ~ notification.id ~ ")") | safe ]]
                    [% endif %]
                </div>
            [% endfor %]
        </div>

        [# File upload with progress #]
        <div class="widget upload">
            <h3>
                [[ ph_icon("upload-simple", variant="bold") | safe ]]
                File Upload
            </h3>

            <div id="upload-zone" class="upload-zone">
                [[ ph_icon("cloud-arrow-up", size="2x", color="primary") | safe ]]
                <p>Drag files here or click to browse</p>

                [% if upload_progress %]
                    <div class="progress-bar">
                        <div class="progress" style="width: [[ upload_progress ]]%"></div>
                    </div>
                    <small>[[ upload_progress ]]% complete</small>
                [% endif %]
            </div>
        </div>

        [# User management table #]
        <div class="widget users">
            <h3>
                [[ ph_icon("users-three", variant="fill") | safe ]]
                Recent Users
            </h3>

            <table class="users-table">
                <thead>
                    <tr>
                        <th>User</th>
                        <th>Status</th>
                        <th>Last Active</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    [% for user in recent_users %]
                        <tr>
                            <td>
                                <div class="user-info">
                                    <img src="[[ user.avatar | cloudflare_img(width=32, height=32) ]]"
                                         alt="[[ user.name ]]" class="avatar">
                                    <div>
                                        <strong>[[ user.name ]]</strong>
                                        <small>[[ user.email ]]</small>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <span class="status [[ user.status ]]">
                                    [% if user.status == "online" %]
                                        [[ ph_icon("circle", variant="fill", color="success", size="xs") | safe ]]
                                    [% elif user.status == "away" %]
                                        [[ ph_icon("circle", variant="fill", color="warning", size="xs") | safe ]]
                                    [% else %]
                                        [[ ph_icon("circle", color="muted", size="xs") | safe ]]
                                    [% endif %]
                                    [[ user.status | title ]]
                                </span>
                            </td>
                            <td>[[ user.last_active | timeago ]]</td>
                            <td>
                                <div class="actions">
                                    [[ ph_interactive("envelope", size="sm",
                                        action="sendMessage('" ~ user.id ~ "')") | safe ]]
                                    [[ ph_interactive("gear", size="sm",
                                        action="editUser('" ~ user.id ~ "')") | safe ]]
                                    [% if current_user.is_admin %]
                                        [[ ph_interactive("trash", size="sm", color="danger",
                                            action="confirmDelete('" ~ user.id ~ "')") | safe ]]
                                    [% endif %]
                                </div>
                            </td>
                        </tr>
                    [% endfor %]
                </tbody>
            </table>
        </div>
    </div>

    [# Custom component example #]
    <div class="custom-components">
        [[ render_component("chart", {
            "type": "line",
            "data": chart_data,
            "options": {"responsive": True, "animation": True}
        }) | safe ]]

        [[ render_component("data_table", {
            "columns": table_columns,
            "data": table_data,
            "searchable": True,
            "sortable": True,
            "pagination": True
        }) | safe ]]
    </div>
[% endblock %]""",
        "error_examples.fb.html": """[# Template with intentional errors for syntax checking demo #]
[% extends "base.html" %]

[% block content %]
    [# Missing closing delimiter #]
    [[ user.name

    [# Unknown filter #]
    [[ content | unknown_filter ]]

    [# Unbalanced delimiters #]
    [[ items | length ]] items found ]]

    [# Unknown function #]
    [[ missing_function("test") ]]

    [# Correct syntax examples #]
    [[ user.name | default("Anonymous") ]]
    [[ ph_icon("check", variant="fill", color="success") | safe ]]
    [[ render_component("user_card", {"name": user.name}) | safe ]]
[% endblock %]""",
    }

    for filename, content in templates.items():
        (demo_dir / filename).write_text(content)

    return templates


async def demonstrate_syntax_checking():
    """Demonstrate syntax checking capabilities."""
    print("🔍 FastBlocks Syntax Checking Demo")
    print("=" * 50)

    syntax_support = FastBlocksSyntaxSupport()

    # Test template with errors
    error_template = """[[ user.name
[[ content | unknown_filter ]]
[[ items | length ]] items ]]
[% if user %]
    [[ missing_function() ]]
[% endblock %]"""

    print("\n📝 Checking template with errors:")
    print(error_template)
    print("\n❌ Syntax errors found:")

    errors = syntax_support.check_syntax(error_template)
    for error in errors:
        print(f"  Line {error.line + 1}, Col {error.column + 1}: {error.message}")
        if error.fix_suggestion:
            print(f"    💡 Fix: {error.fix_suggestion}")

    # Test valid template
    valid_template = """[[ user.name | default("Guest") ]]
[% if user %]
    [[ ph_icon("user", variant="fill") | safe ]]
[% endif %]"""

    print("\n📝 Checking valid template:")
    print(valid_template)

    errors = syntax_support.check_syntax(valid_template)
    if not errors:
        print("\n✅ No syntax errors found!")


async def demonstrate_autocomplete():
    """Demonstrate autocomplete capabilities."""
    print("\n🔮 FastBlocks Autocomplete Demo")
    print("=" * 50)

    syntax_support = FastBlocksSyntaxSupport()

    test_cases = [
        ("[[|", "variable context"),
        ("[%|", "block context"),
        ("{{ user.name ||", "filter context"),
        ("{{ render_|", "function context"),
    ]

    for content, context_name in test_cases:
        cursor_pos = content.find("|")
        test_content = content.replace("|", "")

        print(f"\n📍 Context: {context_name}")
        print(f"Content: '{test_content}' (cursor at position {cursor_pos})")

        completions = syntax_support.get_completions(test_content, 0, cursor_pos)

        print("💭 Completions:")
        for completion in completions[:5]:  # Show top 5
            print(f"  {completion.kind}: {completion.label}")
            if completion.detail:
                print(f"    {completion.detail}")


async def demonstrate_language_server():
    """Demonstrate language server functionality."""
    print("\n🖥️  FastBlocks Language Server Demo")
    print("=" * 50)

    client = FastBlocksLanguageClient()

    # Test document
    test_uri = "file:///demo/test.fb.html"
    test_content = """[[ user.name | default("Guest") ]]
[% if user %]
    [[ ph_icon("user", variant="fill") | safe ]]
[% endif %]"""

    print("\n📄 Opening test document:")
    print(test_content)

    await client.open_document(test_uri, test_content)

    # Test completions
    print("\n💭 Getting completions at line 1, character 5:")
    completions = await client.get_completions(test_uri, 1, 5)
    for completion in completions[:3]:
        print(f"  {completion.get('label', '')} ({completion.get('kind', '')})")

    # Test hover
    print("\n🖱️  Getting hover info for 'ph_icon':")
    hover = await client.get_hover(test_uri, 2, 8)
    if hover and hover.get("contents"):
        print(f"  {hover['contents'].get('value', '')}")

    # Test diagnostics
    print("\n🔍 Current diagnostics:")
    diagnostics = client.get_diagnostics(test_uri)
    if diagnostics:
        for diag in diagnostics:
            print(f"  {diag.get('severity', '')}: {diag.get('message', '')}")
    else:
        print("  No diagnostics found")


async def demonstrate_formatting():
    """Demonstrate template formatting."""
    print("\n📐 FastBlocks Template Formatting Demo")
    print("=" * 50)

    syntax_support = FastBlocksSyntaxSupport()

    unformatted = """[[ user.name ]]
[% if user %]
[[ user.email ]]
[% for item in items %]
<div>[[ item.name ]]</div>
[% endfor %]
[% endif %]"""

    print("\n📝 Unformatted template:")
    print(unformatted)

    formatted = syntax_support.format_template(unformatted)

    print("\n✨ Formatted template:")
    print(formatted)


async def run_comprehensive_demo():
    """Run comprehensive FastBlocks syntax support demo."""
    print("🚀 FastBlocks Syntax Support Comprehensive Demo")
    print("=" * 60)

    # Initialize components
    settings = SyntaxDemoSettings()

    if settings.generate_sample_templates:
        demo_dir = Path(settings.demo_templates_dir)
        templates = await create_sample_templates(demo_dir)
        print(f"📁 Created {len(templates)} sample templates in {demo_dir}")

    # Run demonstrations
    await demonstrate_syntax_checking()
    await demonstrate_autocomplete()
    await demonstrate_language_server()
    await demonstrate_formatting()

    print("\n🎉 Demo completed!")
    print("\n📚 Available CLI commands:")
    print("  python -m fastblocks syntax-check <file>")
    print("  python -m fastblocks format-template <file>")
    print("  python -m fastblocks generate-ide-config")
    print("  python -m fastblocks start-language-server")


if __name__ == "__main__":
    with suppress(Exception):
        depends.set(SyntaxDemoSettings())

    asyncio.run(run_comprehensive_demo())
