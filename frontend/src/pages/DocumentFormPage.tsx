import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { documentsApi } from '../lib/api';
import { DetailPageHeader } from '../components/ui';
import { DocumentForm } from '../components/forms';

export function DocumentFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data, isLoading } = useQuery({
    queryKey: ['document', id],
    queryFn: () => documentsApi.get(id!),
    enabled: isEdit,
  });

  const document = data?.data;

  if (isEdit && isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <DetailPageHeader
        title={isEdit ? 'Edit Document' : 'New Document'}
        backLink="/documents"
        backLabel="Back to Documents"
      />
      <DocumentForm
        document={isEdit ? document : undefined}
        onSuccess={() => navigate(isEdit ? `/documents/${id}` : '/documents')}
      />
    </div>
  );
}
