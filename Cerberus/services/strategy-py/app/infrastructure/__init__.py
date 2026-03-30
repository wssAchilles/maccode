"""Infrastructure package.

Import concrete adapters from their submodules to avoid eager package-level imports
that can create circular dependencies during test collection and application startup.
"""

__all__: list[str] = []
