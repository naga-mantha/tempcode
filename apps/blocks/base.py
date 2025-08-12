from abc import ABC, abstractmethod

from django.shortcuts import render


class BaseBlock(ABC):
    """Base interface for block implementations.

    Subclasses are expected to provide configuration data and the
    runtime data separately via :meth:`get_config` and :meth:`get_data`.
    The :meth:`render` method uses both pieces to render the block's
    template.
    """

    template_name = ""
    supported_features: list[str] = []

    @abstractmethod
    def get_config(self, request):
        """Return configuration metadata for this block."""

    @abstractmethod
    def get_data(self, request):
        """Return the data required to render this block."""

    def render(self, request):
        """Render the block using its template and context."""
        config = self.get_config(request) or {}
        data = self.get_data(request) or {}
        context = {}
        if isinstance(config, dict):
            context.update(config)
        if isinstance(data, dict):
            context.update(data)
        return render(request, self.template_name, context)
