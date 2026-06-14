"""
Plugin system base class.

Plugins are Python modules in the `plugins/` directory.
They register routes and can hook into the application lifecycle.

To create a plugin:
  1. Create a file in app/plugins/, e.g. myplugin.py
  2. Define a class that extends BasePlugin
  3. Implement `register(app)` to add routes/middleware
  4. The plugin is auto-discovered at startup
"""

from fastapi import FastAPI


class BasePlugin:
    """Base class for Null plugins."""

    name: str = "unnamed"
    version: str = "0.1.0"
    description: str = ""

    def register(self, app: FastAPI) -> None:
        """Called at startup. Override to add routes, middleware, etc."""
        raise NotImplementedError
