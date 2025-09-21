"""Bidirectional HTMY-Jinja2 test component for FastBlocks."""

from dataclasses import dataclass
from typing import Any

# FastBlocks has its own HTMY implementation, doesn't use the htmy library
Component = Any
Context = dict
HTMY_AVAILABLE = False


def div(**kwargs):
    attrs = " ".join(f'{k}="{v}"' for k, v in kwargs.items()) if kwargs else ""
    return f"<div {attrs}>" if attrs else "<div>"


def h2(content) -> str:
    return f"<h2>{content}</h2>"


def p(content) -> str:
    return f"<p>{content}</p>"


def ul(**kwargs) -> str:
    return "<ul>"


def li(content) -> str:
    return f"<li>{content}</li>"


@dataclass
class BidirectionalTest:
    """Component that tests bidirectional HTMY-Jinja2 interoperability."""

    title: str = "Bidirectional Test"
    template_name: str | None = None

    async def htmy(self, context: Context) -> Component:
        """Render the bidirectional test component."""
        # Test if we can call Jinja2 from HTMY
        if "render_template" in context and self.template_name:
            try:
                # Call Jinja2 template from within HTMY component
                template_content = await context["render_template"](
                    self.template_name,
                    {
                        "test_title": "Jinja2 from HTMY",
                        "test_content": "This content was rendered by Jinja2 template called from HTMY component",
                        "component_name": "BidirectionalTest",
                    },
                )

                # Build HTML with template content
                if HTMY_AVAILABLE:
                    return div(class_="bidirectional-test success")[
                        h2[f"{self.title} - Success"],
                        p["HTMY component successfully called Jinja2 template:"],
                        template_content,  # Raw HTML from Jinja2
                        p["End of Jinja2 content - back to HTMY"],
                    ]
                else:
                    return (
                        div(class_="bidirectional-test success")
                        + h2(f"{self.title} - Success")
                        + p("HTMY component successfully called Jinja2 template:")
                        + template_content
                        + p("End of Jinja2 content - back to HTMY")
                        + "</div>"
                    )

            except Exception as e:
                # Error handling
                if HTMY_AVAILABLE:
                    return div(class_="bidirectional-test error")[
                        h2[f"{self.title} - Error"],
                        p[f"Failed to call Jinja2 template: {e}"],
                    ]
                else:
                    return (
                        div(class_="bidirectional-test error")
                        + h2(f"{self.title} - Error")
                        + p(f"Failed to call Jinja2 template: {e}")
                        + "</div>"
                    )

        # Pure HTMY mode
        if HTMY_AVAILABLE:
            return div(class_="bidirectional-test pure")[
                h2[f"{self.title} - Pure HTMY"],
                p["This is pure HTMY content (no Jinja2 template)"],
                ul[
                    li["Context keys available:"],
                    *[
                        li[key]
                        for key in sorted(context.keys())
                        if not key.startswith("_")
                    ],
                ],
            ]
        else:
            return (
                div(class_="bidirectional-test pure")
                + h2(f"{self.title} - Pure HTMY")
                + p("This is pure HTMY content (no Jinja2 template)")
                + ul()
                + li("Context keys available:")
                + "".join(
                    [
                        li(key)
                        for key in sorted(context.keys())
                        if not key.startswith("_")
                    ]
                )
                + "</ul></div>"
            )
