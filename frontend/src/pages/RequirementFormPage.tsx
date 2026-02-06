import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { requirementsApi } from '../lib/api';
import { DetailPageHeader } from '../components/ui';
import { RequirementForm } from '../components/forms';

export function RequirementFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data, isLoading } = useQuery({
    queryKey: ['requirement', id],
    queryFn: () => requirementsApi.get(id!),
    enabled: isEdit,
  });

  const requirement = data?.data;

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
        title={isEdit ? 'Edit Requirement' : 'New Requirement'}
        backLink="/requirements"
        backLabel="Back to Requirements"
      />
      <RequirementForm
        requirement={isEdit ? requirement : undefined}
        onSuccess={() => navigate(isEdit ? `/requirements/${id}` : '/requirements')}
      />
    </div>
  );
}
