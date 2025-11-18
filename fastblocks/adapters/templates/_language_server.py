"""FastBlocks Language Server Protocol implementation."""

import asyncio
import typing as t
from contextlib import suppress
from typing import Any
from uuid import UUID

from acb.config import Settings
from acb.depends import depends

from ._syntax_support import FastBlocksSyntaxSupport


class LanguageServerSettings(Settings):
    """Settings for FastBlocks Language Server."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d87-2345-6789-abcd-123456789def")
    MODULE_STATUS: str = "stable"

    # Server settings
    port: int = 7777
    host: str = "localhost"
    enable_tcp: bool = False
    enable_stdio: bool = True

    # Feature flags
    enable_completions: bool = True
    enable_hover: bool = True
    enable_diagnostics: bool = True
    enable_formatting: bool = True
    enable_signature_help: bool = True

    # Performance settings
    completion_trigger_characters: list[str] = ["[", "|", ".", "("]
    signature_trigger_characters: list[str] = ["(", ","]
    diagnostic_delay_ms: int = 500
    completion_timeout_ms: int = 1000


class FastBlocksLanguageServer:
    """Language Server Protocol implementation for FastBlocks templates."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d87-2345-6789-abcd-123456789def")
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        """Initialize language server."""
        self.settings: LanguageServerSettings | None = None
        self.syntax_support: FastBlocksSyntaxSupport | None = None
        self._documents: dict[str, str] = {}
        self._diagnostics: dict[str, list[dict[str, Any]]] = {}

        # Register with ACB
        with suppress(Exception):
            depends.set(self)

        # Initialize syntax support
        self.syntax_support = FastBlocksSyntaxSupport()

    async def initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle LSP initialize request."""
        if not self.settings:
            self.settings = LanguageServerSettings()

        capabilities: dict[str, Any] = {
            "textDocumentSync": {
                "openClose": True,
                "change": 1,  # Full document sync
                "save": {"includeText": True},
            }
        }

        if self.settings.enable_completions:
            capabilities["completionProvider"] = {
                "triggerCharacters": self.settings.completion_trigger_characters,
                "resolveProvider": True,
            }

        if self.settings.enable_hover:
            capabilities["hoverProvider"] = True

        if self.settings.enable_formatting:
            capabilities["documentFormattingProvider"] = True

        if self.settings.enable_signature_help:
            capabilities["signatureHelpProvider"] = {
                "triggerCharacters": self.settings.signature_trigger_characters
            }

        return {
            "capabilities": capabilities,
            "serverInfo": {"name": "FastBlocks Language Server", "version": "1.0.0"},
        }

    async def text_document_did_open(self, params: dict[str, Any]) -> None:
        """Handle document open event."""
        doc = params["textDocument"]
        uri = doc["uri"]
        content = doc["text"]

        self._documents[uri] = content

        # Run diagnostics
        if self.settings and self.settings.enable_diagnostics:
            await self._run_diagnostics(uri, content)

    async def text_document_did_change(self, params: dict[str, Any]) -> None:
        """Handle document change event."""
        uri = params["textDocument"]["uri"]
        changes = params["contentChanges"]

        # For full document sync
        if changes:
            self._documents[uri] = changes[0]["text"]

            # Delayed diagnostics
            if self.settings and self.settings.enable_diagnostics:
                await asyncio.sleep(self.settings.diagnostic_delay_ms / 1000)
                await self._run_diagnostics(uri, self._documents[uri])

    async def text_document_completion(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle completion request."""
        if not self.settings or not self.settings.enable_completions:
            return {"items": []}

        uri = params["textDocument"]["uri"]
        position = params["position"]
        content = self._documents.get(uri, "")

        if not self.syntax_support:
            return {"items": []}

        # Get completions
        completions = self.syntax_support.get_completions(
            content, position["line"], position["character"]
        )

        items = []
        for completion in completions:
            item = {
                "label": completion.label,
                "kind": self._completion_kind_to_lsp(completion.kind),
                "detail": completion.detail,
                "documentation": completion.documentation,
                "insertText": completion.insert_text or completion.label,
                "sortText": f"{100 - completion.priority:03d}_{completion.label}",
            }

            # Add snippet support
            if completion.insert_text and "$" in completion.insert_text:
                item["insertTextFormat"] = 2  # Snippet

            items.append(item)

        return {"items": items}

    async def text_document_hover(
        self, params: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Handle hover request."""
        if not self.settings or not self.settings.enable_hover:
            return None

        uri = params["textDocument"]["uri"]
        position = params["position"]
        content = self._documents.get(uri, "")

        if not self.syntax_support:
            return None

        hover_info = self.syntax_support.get_hover_info(
            content, position["line"], position["character"]
        )

        if hover_info:
            return {"contents": {"kind": "markdown", "value": hover_info}}

        return None

    async def text_document_formatting(
        self, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Handle formatting request."""
        if not self.settings or not self.settings.enable_formatting:
            return []

        uri = params["textDocument"]["uri"]
        content = self._documents.get(uri, "")

        if not self.syntax_support:
            return []

        formatted = self.syntax_support.format_template(content)

        if formatted != content:
            lines = content.split("\n")
            return [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": len(lines), "character": 0},
                    },
                    "newText": formatted,
                }
            ]

        return []

    async def _run_diagnostics(self, uri: str, content: str) -> None:
        """Run diagnostics on document."""
        if not self.syntax_support:
            return

        errors = self.syntax_support.check_syntax(content)
        diagnostics = []

        for error in errors:
            diagnostic = {
                "range": {
                    "start": {"line": error.line, "character": error.column},
                    "end": {"line": error.line, "character": error.column + 10},
                },
                "severity": self._severity_to_lsp(error.severity),
                "code": error.code,
                "source": "FastBlocks",
                "message": error.message,
            }

            if error.fix_suggestion:
                t.cast(dict[str, t.Any], diagnostic)["data"] = {
                    "fix": error.fix_suggestion
                }

            diagnostics.append(diagnostic)

        self._diagnostics[uri] = diagnostics

        # In a real LSP implementation, you would send this to the client
        # self.send_notification("textDocument/publishDiagnostics", {
        #     "uri": uri,
        #     "diagnostics": diagnostics
        # })

    def _completion_kind_to_lsp(self, kind: str) -> int:
        """Convert completion kind to LSP constants."""
        mapping = {
            "function": 3,  # Function
            "variable": 6,  # Variable
            "filter": 12,  # Value
            "block": 14,  # Keyword
            "component": 9,  # Module
            "snippet": 15,  # Snippet
        }
        return mapping.get(kind, 1)  # Text

    def _severity_to_lsp(self, severity: str) -> int:
        """Convert severity to LSP constants."""
        mapping = {"error": 1, "warning": 2, "info": 3, "hint": 4}
        return mapping.get(severity, 1)

    def get_current_diagnostics(self, uri: str) -> list[dict[str, Any]]:
        """Get current diagnostics for a document."""
        return self._diagnostics.get(uri, [])

    async def shutdown(self) -> None:
        """Handle server shutdown."""
        self._documents.clear()
        self._diagnostics.clear()


class FastBlocksLanguageClient:
    """Simple language client for testing and integration."""

    def __init__(self) -> None:
        """Initialize language client."""
        self.server = FastBlocksLanguageServer()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the language server."""
        if self._initialized:
            return

        await self.server.initialize(
            {
                "processId": None,
                "clientInfo": {"name": "FastBlocks Client", "version": "1.0.0"},
                "capabilities": {},
            }
        )
        self._initialized = True

    async def open_document(self, uri: str, content: str) -> None:
        """Open a document."""
        await self.initialize()
        await self.server.text_document_did_open(
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": "fastblocks",
                    "version": 1,
                    "text": content,
                }
            }
        )

    async def change_document(self, uri: str, content: str) -> None:
        """Change document content."""
        await self.server.text_document_did_change(
            {
                "textDocument": {"uri": uri, "version": 2},
                "contentChanges": [{"text": content}],
            }
        )

    async def get_completions(
        self, uri: str, line: int, character: int
    ) -> list[dict[str, Any]]:
        """Get completions at position."""
        result = await self.server.text_document_completion(
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
            }
        )
        return t.cast(list[dict[str, Any]], result.get("items", []))

    async def get_hover(
        self, uri: str, line: int, character: int
    ) -> dict[str, Any] | None:
        """Get hover information."""
        return await self.server.text_document_hover(
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
            }
        )

    async def format_document(self, uri: str) -> list[dict[str, Any]]:
        """Format document."""
        return await self.server.text_document_formatting(
            {"textDocument": {"uri": uri}}
        )

    def get_diagnostics(self, uri: str) -> list[dict[str, Any]]:
        """Get current diagnostics."""
        return self.server.get_current_diagnostics(uri)


# VS Code extension configuration generator
def generate_vscode_extension() -> dict[str, Any]:
    """Generate VS Code extension configuration for FastBlocks."""
    return {
        "name": "fastblocks-language-support",
        "displayName": "FastBlocks Language Support",
        "description": "Language support for FastBlocks templates",
        "version": "1.0.0",
        "publisher": "fastblocks",
        "engines": {"vscode": "^1.74.0"},
        "categories": ["Programming Languages"],
        "activationEvents": ["onLanguage:fastblocks"],
        "main": "./out/extension.js",
        "contributes": {
            "languages": [
                {
                    "id": "fastblocks",
                    "aliases": ["FastBlocks", "fastblocks"],
                    "extensions": [".fb.html", ".fastblocks"],
                    "configuration": "./language-configuration.json",
                }
            ],
            "grammars": [
                {
                    "language": "fastblocks",
                    "scopeName": "text.html.fastblocks",
                    "path": "./syntaxes/fastblocks.tmLanguage.json",
                }
            ],
            "configuration": {
                "type": "object",
                "title": "FastBlocks",
                "properties": {
                    "fastblocks.languageServer.enabled": {
                        "type": "boolean",
                        "default": True,
                        "description": "Enable FastBlocks language server",
                    },
                    "fastblocks.languageServer.port": {
                        "type": "number",
                        "default": 7777,
                        "description": "Language server port",
                    },
                    "fastblocks.completion.enabled": {
                        "type": "boolean",
                        "default": True,
                        "description": "Enable auto-completion",
                    },
                    "fastblocks.diagnostics.enabled": {
                        "type": "boolean",
                        "default": True,
                        "description": "Enable error checking",
                    },
                },
            },
        },
        "scripts": {
            "vscode:prepublish": "npm run compile",
            "compile": "tsc -p ./",
            "watch": "tsc -watch -p ./",
        },
        "devDependencies": {
            "@types/vscode": "^1.74.0",
            "@typescript-eslint/eslint-plugin": "^5.45.0",
            "@typescript-eslint/parser": "^5.45.0",
            "eslint": "^8.28.0",
            "typescript": "^4.9.4",
        },
        "dependencies": {"vscode-languageclient": "^8.1.0"},
    }


# TextMate grammar for syntax highlighting
def generate_textmate_grammar() -> dict[str, Any]:
    """Generate TextMate grammar for FastBlocks syntax highlighting."""
    return {
        "$schema": "https://raw.githubusercontent.com/martinring/tmlanguage/master/tmlanguage.json",
        "name": "FastBlocks",
        "scopeName": "text.html.fastblocks",
        "patterns": [
            {"include": "#fastblocks-variable"},
            {"include": "#fastblocks-block"},
            {"include": "#fastblocks-comment"},
            {"include": "text.html.basic"},
        ],
        "repository": {
            "fastblocks-variable": {
                "name": "meta.tag.template.value.fastblocks",
                "begin": r"\[\[",
                "end": r"\]\]",
                "beginCaptures": {
                    "0": {"name": "punctuation.definition.tag.begin.fastblocks"}
                },
                "endCaptures": {
                    "0": {"name": "punctuation.definition.tag.end.fastblocks"}
                },
                "patterns": [
                    {"include": "#fastblocks-filter"},
                    {"include": "#fastblocks-string"},
                    {"include": "#fastblocks-identifier"},
                ],
            },
            "fastblocks-block": {
                "name": "meta.tag.template.block.fastblocks",
                "begin": r"\[%",
                "end": r"%\]",
                "beginCaptures": {
                    "0": {"name": "punctuation.definition.tag.begin.fastblocks"}
                },
                "endCaptures": {
                    "0": {"name": "punctuation.definition.tag.end.fastblocks"}
                },
                "patterns": [
                    {
                        "name": "keyword.control.fastblocks",
                        "match": r"\b(if|else|elif|endif|for|endfor|block|endblock|extends|include|set|macro|endmacro)\b",
                    },
                    {"include": "#fastblocks-string"},
                    {"include": "#fastblocks-identifier"},
                ],
            },
            "fastblocks-comment": {
                "name": "comment.block.fastblocks",
                "begin": r"\[#",
                "end": r"#\]",
                "beginCaptures": {
                    "0": {"name": "punctuation.definition.comment.begin.fastblocks"}
                },
                "endCaptures": {
                    "0": {"name": "punctuation.definition.comment.end.fastblocks"}
                },
            },
            "fastblocks-filter": {
                "name": "support.function.filter.fastblocks",
                "match": r"\|\s*(\w+)",
                "captures": {"1": {"name": "entity.name.function.filter.fastblocks"}},
            },
            "fastblocks-string": {
                "name": "string.quoted.double.fastblocks",
                "begin": r'"',
                "end": r'"',
                "patterns": [
                    {"name": "constant.character.escape.fastblocks", "match": r"\\."}
                ],
            },
            "fastblocks-identifier": {
                "name": "variable.other.fastblocks",
                "match": r"\b[a-zA-Z_][a-zA-Z0-9_]*\b",
            },
        },
    }


# ACB 0.19.0+ compatibility
__all__ = [
    "FastBlocksLanguageServer",
    "FastBlocksLanguageClient",
    "LanguageServerSettings",
    "generate_vscode_extension",
    "generate_textmate_grammar",
]
