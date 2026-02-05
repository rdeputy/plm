"""
Reports Module

PLM reporting and analytics dashboards.
"""
from .service import ReportService, get_report_service

__all__ = [
    "ReportService",
    "get_report_service",
]
