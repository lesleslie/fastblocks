"""FastBlocks templates adapters.

Advanced Template Management System for FastBlocks Week 7-8.

This package provides comprehensive template management with:
- Enhanced Jinja2 configuration with FastBlocks `[[` `]]` delimiters
- Template syntax checking and error reporting with line numbers
- Fragment and partial template support for HTMX
- Template variable autocomplete for adapter functions
- Async template rendering with proper error handling
- Template caching and performance optimization
- Security-focused template rendering with sandboxed environments
- Block rendering for HTMX partials and fragments
- Integration with all secondary adapters (Cloudflare Images, TwicPics, WebAwesome, etc.)
- Context-aware template suggestions and real-time validation
- Language Server Protocol (LSP) implementation for IDE integration
- FastBlocks syntax support with autocomplete and error checking
- IDE configuration generators for VS Code, Vim, and Emacs
- Multi-IDE syntax highlighting and language support

Key Components:
- HybridTemplatesManager: Core validation and autocomplete
- AsyncTemplateRenderer: High-performance async rendering
- BlockRenderer: HTMX-optimized block rendering
- FastBlocksSyntaxSupport: IDE integration and autocomplete
- FastBlocksLanguageServer: LSP implementation for real-time features
- Enhanced filters for all secondary adapters
- Unified integration interface

Usage:
```python
from fastblocks.adapters.templates import (
    get_hybrid_templates,
    validate_template_source,
    get_template_autocomplete,
    render_htmx_block,
    render_template_fragment,
    FastBlocksSyntaxSupport,
    FastBlocksLanguageServer,
)

# Get hybrid templates integration
integration = await get_hybrid_templates()

# Validate template
result = await validate_template_source(template_source, "my_template.html")

# Get autocomplete suggestions
suggestions = await get_template_autocomplete("[[", 2, "my_template.html")

# Render HTMX block
response = await render_htmx_block(request, "user_profile", {"user": user})

# Syntax support for IDE integration
syntax_support = FastBlocksSyntaxSupport()
completions = syntax_support.get_completions(content, line, column)
errors = syntax_support.check_syntax(template_content)
```

CLI Commands:
```bash
# Syntax checking and formatting
python -m fastblocks syntax-check templates/my_template.fb.html
python -m fastblocks format-template templates/my_template.fb.html --in-place

# IDE configuration generation
python -m fastblocks generate-ide-config --ide vscode --output .vscode
python -m fastblocks generate-ide-config --ide vim --output ~/.vim/syntax
python -m fastblocks generate-ide-config --ide emacs --output ~/.emacs.d

# Language server for real-time IDE features
python -m fastblocks start-language-server --port 7777
```
"""

from ._advanced_manager import (
    AutocompleteItem,
    FragmentInfo,
    HybridTemplatesManager,
    HybridTemplatesSettings,
    SecurityLevel,
    TemplateError,  # Explicitly export TemplateError
    TemplateValidationResult,
    ValidationLevel,
)
from ._async_filters import FASTBLOCKS_ASYNC_FILTERS
from ._async_renderer import (
    AsyncTemplateRenderer,
    CacheStrategy,
    RenderContext,
    RenderMode,
    RenderResult,
)
from ._block_renderer import (
    BlockDefinition,
    BlockRegistry,
    BlockRenderer,
    BlockRenderRequest,
    BlockRenderResult,
    BlockTrigger,
    BlockUpdateMode,
)
from ._enhanced_filters import ENHANCED_ASYNC_FILTERS, ENHANCED_FILTERS
from ._filters import FASTBLOCKS_FILTERS
from ._language_server import (
    FastBlocksLanguageClient,
    FastBlocksLanguageServer,
    LanguageServerSettings,
    generate_textmate_grammar,
    generate_vscode_extension,
)
from ._syntax_support import (
    CompletionItem,
    FastBlocksSyntaxSettings,
    FastBlocksSyntaxSupport,
    SyntaxError,
    register_syntax_filters,
)
from .hybrid import (
    HybridTemplates,
    get_hybrid_templates,
    get_template_autocomplete,
    render_htmx_block,
    render_template_fragment,
    validate_template_source,
)
from .jinja2 import Templates, TemplatesSettings

__all__ = [
    # Main integration
    "HybridTemplates",
    "get_hybrid_templates",
    # Convenience functions
    "validate_template_source",
    "get_template_autocomplete",
    "render_htmx_block",
    "render_template_fragment",
    # Core components
    "HybridTemplatesManager",
    "AsyncTemplateRenderer",
    "BlockRenderer",
    "Templates",
    # Settings and configuration
    "HybridTemplatesSettings",
    "TemplatesSettings",
    "ValidationLevel",
    "SecurityLevel",
    "RenderMode",
    "CacheStrategy",
    "BlockUpdateMode",
    "BlockTrigger",
    # Data structures
    "TemplateError",
    "TemplateValidationResult",
    "FragmentInfo",
    "AutocompleteItem",
    "RenderContext",
    "RenderResult",
    "BlockDefinition",
    "BlockRenderRequest",
    "BlockRenderResult",
    "BlockRegistry",
    # Filter collections
    "FASTBLOCKS_FILTERS",
    "FASTBLOCKS_ASYNC_FILTERS",
    "ENHANCED_FILTERS",
    "ENHANCED_ASYNC_FILTERS",
    # Syntax support and IDE integration
    "FastBlocksSyntaxSupport",
    "FastBlocksLanguageServer",
    "FastBlocksLanguageClient",
    "FastBlocksSyntaxSettings",
    "LanguageServerSettings",
    "CompletionItem",
    "SyntaxError",
    "register_syntax_filters",
    "generate_vscode_extension",
    "generate_textmate_grammar",
]
