import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { bomsApi } from '../lib/api';
import { DetailPageHeader } from '../components/ui';
import { BomForm } from '../components/forms';

export function BomFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data, isLoading } = useQuery({
    queryKey: ['bom', id],
    queryFn: () => bomsApi.get(id!),
    enabled: isEdit,
  });

  const bom = data?.data;

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
        title={isEdit ? 'Edit BOM' : 'New BOM'}
        backLink="/boms"
        backLabel="Back to BOMs"
      />
      <BomForm
        bom={isEdit ? bom : undefined}
        onSuccess={() => navigate(isEdit ? `/boms/${id}` : '/boms')}
      />
    </div>
  );
}
