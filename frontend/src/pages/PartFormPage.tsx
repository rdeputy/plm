import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { partsApi } from '../lib/api';
import { DetailPageHeader } from '../components/ui';
import { PartForm } from '../components/forms/PartForm';

export function PartFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data, isLoading } = useQuery({
    queryKey: ['part', id],
    queryFn: () => partsApi.get(id!),
    enabled: isEdit,
  });

  if (isEdit && isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  const part = data?.data;

  return (
    <div className="space-y-6">
      <DetailPageHeader
        title={isEdit ? 'Edit Part' : 'New Part'}
        subtitle={isEdit ? `${part?.part_number} Rev ${part?.revision}` : undefined}
        backLink={isEdit ? `/parts/${id}` : '/parts'}
        backLabel={isEdit ? 'Back to Part' : 'Back to Parts'}
      />
      <PartForm
        part={part}
        onSuccess={() => navigate(isEdit ? `/parts/${id}` : '/parts')}
      />
    </div>
  );
}
