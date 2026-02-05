"""IPC (Illustrated Parts Catalog) Module.

Provides data structures and services for generating
Illustrated Parts Catalogs from PLM data.
"""
from .models import (
    EffectivityType,
    EffectivityRange,
    Supersession,
    FigureHotspot,
    IPCFigure,
    IPCEntry,
)

__all__ = [
    "EffectivityType",
    "EffectivityRange",
    "Supersession",
    "FigureHotspot",
    "IPCFigure",
    "IPCEntry",
]
