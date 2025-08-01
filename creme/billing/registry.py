import warnings

warnings.warn(
    'The module "billing.registry" is deprecated.', DeprecationWarning,
)


def __getattr__(name):
    if name == 'LinesRegistry':
        from .core import line

        warnings.warn(
            '"LinesRegistry" is deprecated; use "core.line.LineRegistry" instead.',
            DeprecationWarning,
        )
        return line.LineRegistry

    if name == 'lines_registry':
        from .core import line

        warnings.warn(
            '"lines_registry" is deprecated; use "core.line.line_registry" instead.',
            DeprecationWarning,
        )
        return line.line_registry

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
