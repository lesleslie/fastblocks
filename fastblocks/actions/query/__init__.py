"""Universal Query Actions for FastBlocks.

Actions for parsing and executing database queries from HTTP request parameters.
Integrates with ACB's universal query system to provide seamless query handling.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-13
"""

from .parser import UniversalQueryParser, create_query_context, get_model_for_query

__all__ = ["UniversalQueryParser", "create_query_context", "get_model_for_query"]
