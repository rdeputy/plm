import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { projectsApi } from '../lib/api';
import { DetailPageHeader } from '../components/ui';
import { ProjectForm } from '../components/forms';

export function ProjectFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data, isLoading } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id!),
    enabled: isEdit,
  });

  const project = data?.data;

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
        title={isEdit ? 'Edit Project' : 'New Project'}
        backLink="/projects"
        backLabel="Back to Projects"
      />
      <ProjectForm
        project={isEdit ? project : undefined}
        onSuccess={() => navigate(isEdit ? `/projects/${id}` : '/projects')}
      />
    </div>
  );
}
