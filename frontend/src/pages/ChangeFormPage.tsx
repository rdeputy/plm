import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { changesApi } from '../lib/api';
import { DetailPageHeader } from '../components/ui';
import { ChangeForm } from '../components/forms';

export function ChangeFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data, isLoading } = useQuery({
    queryKey: ['change', id],
    queryFn: () => changesApi.get(id!),
    enabled: isEdit,
  });

  const change = data?.data;

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
        title={isEdit ? 'Edit Change Request' : 'New Change Request'}
        backLink="/changes"
        backLabel="Back to Changes"
      />
      <ChangeForm
        change={isEdit ? change : undefined}
        onSuccess={() => navigate(isEdit ? `/changes/${id}` : '/changes')}
      />
    </div>
  );
}
