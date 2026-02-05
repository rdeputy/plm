"""
PLM-Orchestrator DMS Integration

Bridges PLM document management with orchestrator's DMS for:
- File storage with audit logging
- Version tracking via checksums
- Semantic search via ChromaDB
- Document classification
- Metadata extraction

Usage:
    from plm.documents.dms_integration import PLMDocumentService

    service = PLMDocumentService()

    # Upload a file
    result = service.upload(
        document_id="...",
        file_content=bytes_data,
        filename="drawing.pdf",
        user_id="engineer-001"
    )

    # Download a file
    content = service.download(document_id)

    # Search documents
    results = service.search("foundation structural detail")
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Optional

logger = logging.getLogger(__name__)

# DMS root path - configurable via environment
PLM_DMS_ROOT = os.getenv("PLM_DMS_ROOT", "/mnt/c/dev/plm-documents")


@dataclass
class UploadResult:
    """Result of a file upload."""
    success: bool
    storage_path: str
    file_hash: str
    file_size: int
    mime_type: str
    error: Optional[str] = None
    version_recorded: bool = False
    indexed: bool = False


@dataclass
class SearchHit:
    """A search result."""
    document_id: str
    storage_path: str
    score: float
    snippet: str
    doc_type: str
    metadata: dict


class PLMDocumentService:
    """
    PLM Document Service integrating with Orchestrator DMS.

    Provides file operations, versioning, search, and classification
    for PLM documents with full audit trail.
    """

    def __init__(
        self,
        dms_root: str | None = None,
        use_orchestrator: bool = True,
    ):
        """
        Initialize the document service.

        Args:
            dms_root: Root path for document storage
            use_orchestrator: Whether to use orchestrator DMS (vs local-only)
        """
        self.dms_root = Path(dms_root or PLM_DMS_ROOT)
        self.use_orchestrator = use_orchestrator

        # Orchestrator DMS components (lazy-loaded)
        self._dms_manager = None
        self._version_tracker = None
        self._document_index = None
        self._classifier = None
        self._metadata_extractor = None

        # Ensure storage directories exist
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create storage directory structure."""
        for subdir in ["drawings", "specs", "submittals", "reports", "other", "temp"]:
            (self.dms_root / subdir).mkdir(parents=True, exist_ok=True)

    @property
    def dms_manager(self):
        """Lazy-load DMSManager from orchestrator."""
        if self._dms_manager is None and self.use_orchestrator:
            try:
                from orchestrator.dms import DMSManager
                self._dms_manager = DMSManager()
            except ImportError:
                logger.warning("orchestrator.dms not available, using local storage only")
        return self._dms_manager

    @property
    def version_tracker(self):
        """Lazy-load VersionTracker from orchestrator."""
        if self._version_tracker is None and self.use_orchestrator:
            try:
                from orchestrator.dms import VersionTracker
                self._version_tracker = VersionTracker()
            except ImportError:
                logger.warning("orchestrator.dms.versioning not available")
        return self._version_tracker

    @property
    def document_index(self):
        """Lazy-load DocumentIndex from orchestrator."""
        if self._document_index is None and self.use_orchestrator:
            try:
                from orchestrator.dms import DocumentIndex
                self._document_index = DocumentIndex()
            except ImportError:
                logger.warning("orchestrator.dms.search_index not available")
        return self._document_index

    @property
    def classifier(self):
        """Lazy-load DocumentClassifier from orchestrator."""
        if self._classifier is None and self.use_orchestrator:
            try:
                from orchestrator.dms import DocumentClassifier
                self._classifier = DocumentClassifier()
            except ImportError:
                logger.warning("orchestrator.dms.classifier not available")
        return self._classifier

    @property
    def metadata_extractor(self):
        """Lazy-load MetadataExtractor from orchestrator."""
        if self._metadata_extractor is None and self.use_orchestrator:
            try:
                from orchestrator.dms import MetadataExtractor
                self._metadata_extractor = MetadataExtractor()
            except ImportError:
                logger.warning("orchestrator.dms.metadata_extractor not available")
        return self._metadata_extractor

    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()

    def _get_mime_type(self, filename: str) -> str:
        """Determine MIME type from filename."""
        ext = Path(filename).suffix.lower()
        mime_types = {
            ".pdf": "application/pdf",
            ".dwg": "application/acad",
            ".dxf": "application/dxf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tif": "image/tiff",
            ".tiff": "image/tiff",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".3dm": "application/x-3dm",
            ".skp": "application/vnd.sketchup.skp",
            ".rvt": "application/x-rvt",
            ".ifc": "application/x-step",
        }
        return mime_types.get(ext, "application/octet-stream")

    def _get_storage_subdir(self, doc_type: str) -> str:
        """Get storage subdirectory based on document type."""
        type_map = {
            "drawing": "drawings",
            "model_3d": "drawings",
            "specification": "specs",
            "datasheet": "specs",
            "submittal": "submittals",
            "rfi": "submittals",
            "field_report": "reports",
            "inspection": "reports",
            "calculation": "reports",
            "test_report": "reports",
        }
        return type_map.get(doc_type, "other")

    def upload(
        self,
        document_id: str,
        content: bytes | BinaryIO,
        filename: str,
        user_id: str,
        document_type: str = "other",
        revision: str = "A",
        project_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UploadResult:
        """
        Upload a file to the document store.

        Args:
            document_id: PLM document ID
            content: File content (bytes or file-like object)
            filename: Original filename
            user_id: User performing upload
            document_type: PLM document type
            revision: Document revision
            project_id: Optional project ID for organization
            metadata: Additional metadata

        Returns:
            UploadResult with storage path and hash
        """
        # Read content if file-like
        if hasattr(content, "read"):
            content = content.read()

        # Compute hash
        file_hash = self._compute_hash(content)
        file_size = len(content)
        mime_type = self._get_mime_type(filename)

        # Build storage path
        subdir = self._get_storage_subdir(document_type)
        if project_id:
            storage_dir = self.dms_root / subdir / project_id
        else:
            storage_dir = self.dms_root / subdir
        storage_dir.mkdir(parents=True, exist_ok=True)

        # Use document_id + revision for uniqueness
        ext = Path(filename).suffix
        storage_filename = f"{document_id}_{revision}{ext}"
        storage_path = storage_dir / storage_filename

        try:
            # Write file
            storage_path.write_bytes(content)

            result = UploadResult(
                success=True,
                storage_path=str(storage_path),
                file_hash=file_hash,
                file_size=file_size,
                mime_type=mime_type,
            )

            # Record version if orchestrator available
            if self.version_tracker:
                try:
                    self.version_tracker.record(
                        path=str(storage_path),
                        event="upload",
                        actor=f"plm:{user_id}",
                        metadata={
                            "document_id": document_id,
                            "revision": revision,
                            "original_filename": filename,
                        },
                    )
                    result.version_recorded = True
                except Exception as e:
                    logger.error(f"Failed to record version: {e}")

            # Index for search if orchestrator available
            if self.document_index and mime_type == "application/pdf":
                try:
                    # Extract text for indexing
                    text = self._extract_text(storage_path)
                    if text:
                        self.document_index.add_document(
                            path=str(storage_path),
                            text=text,
                            doc_type=document_type,
                            metadata={
                                "document_id": document_id,
                                "revision": revision,
                                "project_id": project_id,
                                **(metadata or {}),
                            },
                        )
                        result.indexed = True
                except Exception as e:
                    logger.error(f"Failed to index document: {e}")

            return result

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return UploadResult(
                success=False,
                storage_path="",
                file_hash=file_hash,
                file_size=file_size,
                mime_type=mime_type,
                error=str(e),
            )

    def _extract_text(self, path: Path) -> str | None:
        """Extract text from a document for indexing."""
        try:
            if self.use_orchestrator:
                from orchestrator.documents.pdf_service import PDFExtractor
                extractor = PDFExtractor()
                result = extractor.extract(str(path))
                return result.full_text
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
        return None

    def download(self, storage_path: str) -> bytes | None:
        """
        Download a file from the document store.

        Args:
            storage_path: Full path to stored file

        Returns:
            File content as bytes, or None if not found
        """
        path = Path(storage_path)
        if not path.exists():
            logger.error(f"File not found: {storage_path}")
            return None

        return path.read_bytes()

    def delete(
        self,
        storage_path: str,
        user_id: str,
        reason: str = "",
    ) -> bool:
        """
        Delete a file (stages for deletion if using orchestrator).

        Args:
            storage_path: Path to file
            user_id: User performing deletion
            reason: Reason for deletion

        Returns:
            True if successful
        """
        path = Path(storage_path)
        if not path.exists():
            return False

        try:
            # Use orchestrator staged deletion if available
            if self.dms_manager:
                result = self.dms_manager.stage_delete(str(path), reason=reason)
                return result.success
            else:
                # Direct deletion
                path.unlink()
                return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    def search(
        self,
        query: str,
        document_type: str | None = None,
        project_id: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        """
        Search documents by content.

        Args:
            query: Search query (natural language)
            document_type: Filter by type
            project_id: Filter by project
            limit: Max results

        Returns:
            List of SearchHit results
        """
        if not self.document_index:
            logger.warning("Document search not available (no orchestrator)")
            return []

        try:
            metadata_filter = {}
            if document_type:
                metadata_filter["doc_type"] = document_type
            if project_id:
                metadata_filter["project_id"] = project_id

            results = self.document_index.search(
                query=query,
                doc_type=document_type,
                limit=limit,
                metadata_filter=metadata_filter if metadata_filter else None,
            )

            return [
                SearchHit(
                    document_id=r.metadata.get("document_id", ""),
                    storage_path=r.path,
                    score=r.score,
                    snippet=r.snippet,
                    doc_type=r.doc_type,
                    metadata=r.metadata,
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def classify(self, storage_path: str) -> dict[str, Any]:
        """
        Classify a document using orchestrator's classifier.

        Args:
            storage_path: Path to document

        Returns:
            Classification result with type and confidence
        """
        if not self.classifier:
            return {"type": "unknown", "confidence": 0.0, "suggestions": []}

        try:
            result = self.classifier.classify(storage_path)
            return {
                "type": result.document_type.value if hasattr(result.document_type, 'value') else result.document_type,
                "confidence": result.confidence,
                "suggestions": [
                    {"type": s.document_type, "confidence": s.confidence}
                    for s in (result.alternatives or [])
                ],
                "suggested_path": result.suggested_path,
            }
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return {"type": "unknown", "confidence": 0.0, "error": str(e)}

    def extract_metadata(self, storage_path: str, document_type: str) -> dict[str, Any]:
        """
        Extract structured metadata from a document.

        Args:
            storage_path: Path to document
            document_type: Type hint for extraction

        Returns:
            Extracted metadata (dates, amounts, references, etc.)
        """
        if not self.metadata_extractor:
            return {}

        try:
            result = self.metadata_extractor.extract(storage_path, document_type)
            return result.to_dict() if hasattr(result, 'to_dict') else {}
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return {"error": str(e)}

    def get_version_history(self, storage_path: str) -> list[dict[str, Any]]:
        """
        Get version history for a document.

        Args:
            storage_path: Path to document

        Returns:
            List of version records
        """
        if not self.version_tracker:
            return []

        try:
            history = self.version_tracker.get_history(storage_path)
            return [v.to_dict() for v in history]
        except Exception as e:
            logger.error(f"Version history retrieval failed: {e}")
            return []

    def verify_integrity(self, storage_path: str, expected_hash: str) -> bool:
        """
        Verify file integrity against expected hash.

        Args:
            storage_path: Path to file
            expected_hash: Expected SHA-256 hash

        Returns:
            True if file matches expected hash
        """
        path = Path(storage_path)
        if not path.exists():
            return False

        actual_hash = self._compute_hash(path.read_bytes())
        return actual_hash == expected_hash


# Convenience factory
def get_document_service() -> PLMDocumentService:
    """Get a configured PLMDocumentService instance."""
    return PLMDocumentService()
