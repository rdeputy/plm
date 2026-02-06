"""
Document Management Tests

Tests for document CRUD, check-in/check-out, versioning, and file operations.
"""

import pytest
from uuid import uuid4
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from plm.db.base import Base
from plm.documents.models import (
    DocumentType,
    DocumentStatus,
    CheckoutStatus,
    Document,
    DocumentVersion,
    DocumentLink,
    increment_document_revision,
)


# Test database setup
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

# Create all tables
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    """Override database dependency for tests."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    """Create test client with dependency override."""
    from plm.api.app import app
    from plm.api.deps import get_db_session

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def api_headers():
    """API headers with auth key."""
    return {"X-API-Key": "dev-key"}


# =============================================================================
# Domain Model Tests
# =============================================================================


class TestDocumentModels:
    """Tests for document domain models."""

    def test_document_creation(self):
        """Test creating a document."""
        doc = Document(
            id=str(uuid4()),
            document_number="DWG-2024-001",
            revision="A",
            title="Test Drawing",
            document_type=DocumentType.DRAWING,
        )
        assert doc.document_number == "DWG-2024-001"
        assert doc.revision == "A"
        assert doc.full_document_number == "DWG-2024-001-A"
        assert doc.status == DocumentStatus.DRAFT
        assert doc.checkout_status == CheckoutStatus.AVAILABLE

    def test_document_can_checkout(self):
        """Test checkout eligibility."""
        doc = Document(
            id=str(uuid4()),
            document_number="DWG-2024-002",
            revision="A",
            title="Checkout Test",
        )
        assert doc.can_checkout() is True

        doc.checkout_status = CheckoutStatus.CHECKED_OUT
        assert doc.can_checkout() is False

        doc.checkout_status = CheckoutStatus.AVAILABLE
        doc.status = DocumentStatus.OBSOLETE
        assert doc.can_checkout() is False

    def test_document_can_checkin(self):
        """Test checkin eligibility."""
        user_id = "user-001"
        doc = Document(
            id=str(uuid4()),
            document_number="DWG-2024-003",
            revision="A",
            title="Checkin Test",
            checkout_status=CheckoutStatus.CHECKED_OUT,
            checked_out_by=user_id,
        )
        assert doc.can_checkin(user_id) is True
        assert doc.can_checkin("other-user") is False

    def test_document_version_creation(self):
        """Test creating a document version."""
        version = DocumentVersion(
            id=str(uuid4()),
            document_id=str(uuid4()),
            version_number=1,
            revision="A",
            storage_path="/docs/test.pdf",
            file_hash="abc123",
            file_size=1024,
        )
        assert version.version_number == 1
        assert version.file_size == 1024

    def test_document_link_creation(self):
        """Test creating a document link."""
        link = DocumentLink(
            id=str(uuid4()),
            document_id=str(uuid4()),
            part_id=str(uuid4()),
            link_type="primary",
        )
        assert link.link_type == "primary"

    def test_increment_revision_alpha(self):
        """Test incrementing alpha revisions."""
        assert increment_document_revision("A") == "B"
        assert increment_document_revision("B") == "C"
        assert increment_document_revision("Z") == "AA"

    def test_increment_revision_numeric(self):
        """Test incrementing numeric revisions."""
        assert increment_document_revision("1.0") == "1.1"
        assert increment_document_revision("1.9") == "1.10"
        assert increment_document_revision("2.5") == "2.6"


# =============================================================================
# API Router Tests
# =============================================================================


class TestDocumentsRouter:
    """Tests for documents API endpoints."""

    def test_list_documents(self, client, api_headers):
        """Test listing documents."""
        response = client.get("/api/v1/documents", headers=api_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_document(self, client, api_headers):
        """Test creating a document."""
        data = {
            "document_number": "DWG-API-001",
            "title": "API Test Drawing",
            "description": "Created via API test",
            "document_type": "drawing",
            "category": "Structural",
        }
        response = client.post(
            "/api/v1/documents?created_by=test-user",
            json=data,
            headers=api_headers
        )
        assert response.status_code == 201
        result = response.json()
        assert result["document_number"] == "DWG-API-001"
        assert result["title"] == "API Test Drawing"
        assert result["status"] == "draft"
        assert result["revision"] == "A"
        return result["id"]

    def test_get_document(self, client, api_headers):
        """Test getting a document."""
        # First create one
        data = {
            "document_number": "DWG-API-002",
            "title": "Get Test Document",
        }
        create_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=data,
            headers=api_headers
        )
        doc_id = create_resp.json()["id"]

        # Now get it
        response = client.get(f"/api/v1/documents/{doc_id}", headers=api_headers)
        assert response.status_code == 200
        assert response.json()["document_number"] == "DWG-API-002"

    def test_get_nonexistent_document(self, client, api_headers):
        """Test getting a nonexistent document returns 404."""
        response = client.get(f"/api/v1/documents/{uuid4()}", headers=api_headers)
        assert response.status_code == 404

    def test_update_document(self, client, api_headers):
        """Test updating a document."""
        # Create
        data = {"document_number": "DWG-API-003", "title": "Original Title"}
        create_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=data,
            headers=api_headers
        )
        doc_id = create_resp.json()["id"]

        # Update
        update_data = {"title": "Updated Title", "description": "New description"}
        response = client.patch(
            f"/api/v1/documents/{doc_id}",
            json=update_data,
            headers=api_headers
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_delete_draft_document(self, client, api_headers):
        """Test deleting a draft document."""
        # Create
        data = {"document_number": "DWG-API-004", "title": "To Delete"}
        create_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=data,
            headers=api_headers
        )
        doc_id = create_resp.json()["id"]

        # Delete
        response = client.delete(f"/api/v1/documents/{doc_id}", headers=api_headers)
        assert response.status_code == 204


class TestCheckInCheckOut:
    """Tests for check-in/check-out workflow."""

    def test_checkout_document(self, client, api_headers):
        """Test checking out a document."""
        # Create
        data = {"document_number": "DWG-CHK-001", "title": "Checkout Test"}
        create_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=data,
            headers=api_headers
        )
        doc_id = create_resp.json()["id"]

        # Checkout
        checkout_data = {"user_id": "engineer-001", "notes": "Making changes"}
        response = client.post(
            f"/api/v1/documents/{doc_id}/checkout",
            json=checkout_data,
            headers=api_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["checkout_status"] == "checked_out"
        assert result["checked_out_by"] == "engineer-001"

    def test_checkin_document(self, client, api_headers):
        """Test checking in a document."""
        # Create and checkout
        data = {"document_number": "DWG-CHK-002", "title": "Checkin Test"}
        create_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=data,
            headers=api_headers
        )
        doc_id = create_resp.json()["id"]

        checkout_data = {"user_id": "engineer-001"}
        client.post(
            f"/api/v1/documents/{doc_id}/checkout",
            json=checkout_data,
            headers=api_headers
        )

        # Checkin
        checkin_data = {"user_id": "engineer-001", "change_summary": "Updated layout"}
        response = client.post(
            f"/api/v1/documents/{doc_id}/checkin",
            json=checkin_data,
            headers=api_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["checkout_status"] == "available"
        assert result["checked_out_by"] is None

    def test_cannot_checkout_already_checked_out(self, client, api_headers):
        """Test cannot checkout an already checked out document."""
        # Create and checkout
        data = {"document_number": "DWG-CHK-003", "title": "Double Checkout Test"}
        create_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=data,
            headers=api_headers
        )
        doc_id = create_resp.json()["id"]

        checkout_data = {"user_id": "engineer-001"}
        client.post(
            f"/api/v1/documents/{doc_id}/checkout",
            json=checkout_data,
            headers=api_headers
        )

        # Try to checkout again
        response = client.post(
            f"/api/v1/documents/{doc_id}/checkout",
            json={"user_id": "engineer-002"},
            headers=api_headers
        )
        assert response.status_code == 400

    def test_cancel_checkout(self, client, api_headers):
        """Test canceling a checkout."""
        # Create and checkout
        data = {"document_number": "DWG-CHK-004", "title": "Cancel Test"}
        create_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=data,
            headers=api_headers
        )
        doc_id = create_resp.json()["id"]

        checkout_data = {"user_id": "engineer-001"}
        client.post(
            f"/api/v1/documents/{doc_id}/checkout",
            json=checkout_data,
            headers=api_headers
        )

        # Cancel
        response = client.post(
            f"/api/v1/documents/{doc_id}/cancel-checkout?user_id=engineer-001",
            headers=api_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["checkout_status"] == "available"


class TestDocumentWorkflow:
    """Tests for document approval workflow."""

    def test_submit_for_review(self, client, api_headers):
        """Test submitting a document for review."""
        # Create
        data = {"document_number": "DWG-WKF-001", "title": "Workflow Test"}
        create_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=data,
            headers=api_headers
        )
        doc_id = create_resp.json()["id"]

        # Submit
        response = client.post(
            f"/api/v1/documents/{doc_id}/submit-for-review?submitted_by=engineer-001",
            headers=api_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "pending_review"

    def test_approve_document(self, client, api_headers):
        """Test approving a document."""
        # Create and submit
        data = {"document_number": "DWG-WKF-002", "title": "Approval Test"}
        create_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=data,
            headers=api_headers
        )
        doc_id = create_resp.json()["id"]

        client.post(
            f"/api/v1/documents/{doc_id}/submit-for-review?submitted_by=engineer-001",
            headers=api_headers
        )

        # Approve
        response = client.post(
            f"/api/v1/documents/{doc_id}/approve?approved_by=manager-001",
            headers=api_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "approved"
        assert result["released_by"] == "manager-001"

    def test_revise_approved_document(self, client, api_headers):
        """Test creating a new revision of an approved document."""
        # Create, submit, and approve
        data = {"document_number": "DWG-WKF-003", "title": "Revision Test"}
        create_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=data,
            headers=api_headers
        )
        doc_id = create_resp.json()["id"]

        client.post(
            f"/api/v1/documents/{doc_id}/submit-for-review?submitted_by=engineer-001",
            headers=api_headers
        )
        client.post(
            f"/api/v1/documents/{doc_id}/approve?approved_by=manager-001",
            headers=api_headers
        )

        # Revise
        response = client.post(
            f"/api/v1/documents/{doc_id}/revise?revised_by=engineer-001",
            headers=api_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["revision"] == "B"
        assert result["status"] == "draft"
        assert result["document_number"] == "DWG-WKF-003"


class TestDocumentLinks:
    """Tests for document linking."""

    def test_link_document_to_part(self, client, api_headers):
        """Test linking a document to a part."""
        # Create a document
        doc_data = {"document_number": "DWG-LNK-001", "title": "Link Test"}
        doc_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=doc_data,
            headers=api_headers
        )
        doc_id = doc_resp.json()["id"]

        # Create a part first
        from uuid import uuid4
        from sqlalchemy.orm import sessionmaker
        from plm.db.models import PartModel

        db = TestSessionLocal()
        part = PartModel(
            id=str(uuid4()),
            part_number="PART-LNK-001",
            revision="A",
            name="Link Test Part",
            part_type="component",
            status="draft",
        )
        db.add(part)
        db.commit()
        part_id = part.id
        db.close()

        # Link document to part
        link_data = {"part_id": part_id, "link_type": "primary"}
        response = client.post(
            f"/api/v1/documents/{doc_id}/links?created_by=engineer-001",
            json=link_data,
            headers=api_headers
        )
        assert response.status_code == 201
        result = response.json()
        assert result["part_id"] == part_id
        assert result["link_type"] == "primary"

    def test_list_document_links(self, client, api_headers):
        """Test listing document links."""
        # Create a document with links
        doc_data = {"document_number": "DWG-LNK-002", "title": "List Links Test"}
        doc_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=doc_data,
            headers=api_headers
        )
        doc_id = doc_resp.json()["id"]

        # List links (empty initially)
        response = client.get(f"/api/v1/documents/{doc_id}/links", headers=api_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestDocumentVersions:
    """Tests for document versioning."""

    def test_list_document_versions(self, client, api_headers):
        """Test listing document versions."""
        # Create a document
        doc_data = {"document_number": "DWG-VER-001", "title": "Version Test"}
        doc_resp = client.post(
            "/api/v1/documents?created_by=test-user",
            json=doc_data,
            headers=api_headers
        )
        doc_id = doc_resp.json()["id"]

        # List versions (empty initially)
        response = client.get(f"/api/v1/documents/{doc_id}/versions", headers=api_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestDocumentSearch:
    """Tests for document search."""

    def test_search_documents(self, client, api_headers):
        """Test searching documents."""
        search_data = {"query": "foundation structural", "limit": 10}
        response = client.post(
            "/api/v1/documents/search",
            json=search_data,
            headers=api_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestDocumentCrossReference:
    """Tests for document cross-reference queries."""

    def test_get_documents_for_part(self, client, api_headers):
        """Test getting documents linked to a part."""
        part_id = str(uuid4())
        response = client.get(
            f"/api/v1/documents/by-part/{part_id}",
            headers=api_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_documents_for_bom(self, client, api_headers):
        """Test getting documents linked to a BOM."""
        bom_id = str(uuid4())
        response = client.get(
            f"/api/v1/documents/by-bom/{bom_id}",
            headers=api_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_documents_for_eco(self, client, api_headers):
        """Test getting documents linked to an ECO."""
        eco_id = str(uuid4())
        response = client.get(
            f"/api/v1/documents/by-eco/{eco_id}",
            headers=api_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
