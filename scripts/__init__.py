"""Stand-alone CI lint scripts for FastBlocks.

Each script in this package is independently runnable (e.g.
``python -m scripts.check_metric_cardinality``) and exits non-zero
when its specific contract is violated. Scripts in this directory
are NOT shipped as part of the installed ``fastblocks`` package —
they live in the source tree so contributors can run them locally
and CI can pin them to a known revision.
"""

__all__: list[str] = []
