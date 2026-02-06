import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { documentsApi } from '../lib/api';
import { DetailPageHeader, DetailSection, InfoGrid, InfoItem } from '../components/ui';
import { StatusBadge } from '../components/forms';
import { Edit, Download, FileText } from 'lucide-react';

interface Document {
  id: string;
  document_number: string;
  revision: string;
  title: string;
  description: string | null;
  document_type: string;
  status: string;
  category: string | null;
  file_name: string | null;
  file_size: number | null;
  mime_type: string | null;
  created_at: string | null;
  created_by: string | null;
}

export function DocumentDetail() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ['document', id],
    queryFn: () => documentsApi.get(id!),
    enabled: !!id,
  });

  const doc: Document | undefined = data?.data;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-500">Document not found</p>
      </div>
    );
  }

  const canEdit = doc.status === 'draft' || doc.status === 'in_review';

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  return (
    <div className="space-y-6">
      <DetailPageHeader
        title={`${doc.document_number} Rev ${doc.revision}`}
        subtitle={doc.title}
        backLink="/documents"
        backLabel="Back to Documents"
        actions={
          <>
            {canEdit && (
              <Link
                to={`/documents/${id}/edit`}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                <Edit className="h-4 w-4" />
                Edit
              </Link>
            )}
            {doc.file_name && (
              <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                <Download className="h-4 w-4" />
                Download
              </button>
            )}
          </>
        }
      />

      <div className="flex items-center gap-4">
        <StatusBadge status={doc.status} />
        <span className="text-sm text-gray-500">Type: {doc.document_type}</span>
      </div>

      <DetailSection title="General Information">
        <InfoGrid>
          <InfoItem label="Document Number" value={doc.document_number} />
          <InfoItem label="Revision" value={doc.revision} />
          <InfoItem label="Title" value={doc.title} />
          <InfoItem label="Type" value={doc.document_type} />
          <InfoItem label="Category" value={doc.category} />
          <InfoItem label="Created" value={formatDate(doc.created_at)} />
        </InfoGrid>
        {doc.description && (
          <div className="mt-6">
            <dt className="text-sm font-medium text-gray-500">Description</dt>
            <dd className="mt-1 text-sm text-gray-900">{doc.description}</dd>
          </div>
        )}
      </DetailSection>

      <DetailSection title="File Information">
        {doc.file_name ? (
          <div className="flex items-start gap-4">
            <div className="p-3 bg-gray-100 rounded-lg">
              <FileText className="h-8 w-8 text-gray-500" />
            </div>
            <InfoGrid columns={2}>
              <InfoItem label="File Name" value={doc.file_name} />
              <InfoItem label="File Size" value={formatFileSize(doc.file_size)} />
              <InfoItem label="MIME Type" value={doc.mime_type} />
              <InfoItem label="Created By" value={doc.created_by} />
            </InfoGrid>
          </div>
        ) : (
          <p className="text-gray-500">No file attached</p>
        )}
      </DetailSection>
    </div>
  );
}
