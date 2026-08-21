"""Base class for FastBlocks htmy components."""

from __future__ import annotations

from htmy import Component, Context, SafeStr


class FastBlocksComponent:
    """Base for thin htmy wrappers over the ``fastblocks-ui`` string helpers.

    Subclasses implement :meth:`_markup` to return HTML produced by a
    ``fastblocks-ui`` helper. The result is wrapped in htmy's ``SafeStr`` so it
    renders without re-escaping. Styling is **never** reimplemented here — it comes
    entirely from the ``fastblocks-ui`` CSS bundle, which keeps this layer a thin,
    type-safe veneer that cannot drift from the design system.

    IMPORTANT: instantiating a component (e.g. ``Button(label="Save")``) does
    **not** by itself produce markup — ``.htmy(context)`` must actually be
    called and awaited/rendered through htmy's own render pipeline (or via
    FastBlocks' ``render_component()`` template global, which does exactly
    that). A bare instance handed to a template engine's normal output
    mechanism (e.g. a raw Jinja ``[[ Button(...) ]]`` expression with no
    ``render_component`` involved) will print this object's ``repr``, not
    HTML. ``__str__``/``__html__`` are provided below as a best-effort
    fallback for accidental bare-object stringification (using htmy's
    synchronous rendering path with an empty context), but real usage should
    go through ``HTMY().render(...)`` or FastBlocks' ``render_component()``.
    """

    def _markup(self, context: Context) -> str:
        raise NotImplementedError

    def htmy(self, context: Context) -> Component:
        return SafeStr(self._markup(context))

    def __html__(self) -> str:
        # Best-effort fallback: render with an empty context so accidental
        # bare stringification (str(), Jinja's default output, f-strings)
        # produces markup instead of a dataclass repr. Components that need
        # ``context`` for anything beyond their own fields should be
        # rendered explicitly instead of relying on this fallback.
        return self._markup({})

    def __str__(self) -> str:
        return self.__html__()
