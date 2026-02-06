import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { requirementsApi } from '../lib/api';
import { DetailPageHeader, DetailSection, InfoGrid, InfoItem } from '../components/ui';
import { StatusBadge } from '../components/forms';
import { Edit } from 'lucide-react';

interface Requirement {
  id: string;
  requirement_number: string;
  title: string;
  description: string | null;
  requirement_type: string;
  priority: string;
  status: string;
  source: string | null;
  verification_method: string | null;
  parent_id: string | null;
  project_id: string | null;
}

export function RequirementDetail() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ['requirement', id],
    queryFn: () => requirementsApi.get(id!),
    enabled: !!id,
  });

  const req: Requirement | undefined = data?.data;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error || !req) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-500">Requirement not found</p>
      </div>
    );
  }

  const canEdit = req.status === 'draft' || req.status === 'proposed';

  const priorityColors: Record<string, string> = {
    must_have: 'bg-red-100 text-red-800',
    should_have: 'bg-orange-100 text-orange-800',
    could_have: 'bg-yellow-100 text-yellow-800',
    wont_have: 'bg-gray-100 text-gray-800',
  };

  const typeColors: Record<string, string> = {
    functional: 'bg-blue-100 text-blue-800',
    performance: 'bg-purple-100 text-purple-800',
    interface: 'bg-cyan-100 text-cyan-800',
    regulatory: 'bg-orange-100 text-orange-800',
  };

  return (
    <div className="space-y-6">
      <DetailPageHeader
        title={req.requirement_number}
        subtitle={req.title}
        backLink="/requirements"
        backLabel="Back to Requirements"
        actions={
          canEdit && (
            <Link
              to={`/requirements/${id}/edit`}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <Edit className="h-4 w-4" />
              Edit
            </Link>
          )
        }
      />

      <div className="flex items-center gap-4">
        <StatusBadge status={req.status} />
        <StatusBadge status={req.requirement_type} colorMap={typeColors} />
        <StatusBadge status={req.priority.replace('_', ' ')} colorMap={priorityColors} />
      </div>

      <DetailSection title="General Information">
        <InfoGrid>
          <InfoItem label="Requirement Number" value={req.requirement_number} />
          <InfoItem label="Title" value={req.title} />
          <InfoItem label="Type" value={req.requirement_type} />
          <InfoItem label="Priority" value={req.priority.replace('_', ' ')} />
          <InfoItem label="Source" value={req.source} />
          <InfoItem
            label="Parent Requirement"
            value={
              req.parent_id ? (
                <Link to={`/requirements/${req.parent_id}`} className="text-blue-600 hover:underline">
                  View Parent
                </Link>
              ) : null
            }
          />
        </InfoGrid>
        {req.description && (
          <div className="mt-6">
            <dt className="text-sm font-medium text-gray-500">Description</dt>
            <dd className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">
              {req.description}
            </dd>
          </div>
        )}
      </DetailSection>

      <DetailSection title="Verification">
        <InfoGrid columns={2}>
          <InfoItem label="Verification Method" value={req.verification_method} />
          <InfoItem
            label="Project"
            value={
              req.project_id ? (
                <Link to={`/projects/${req.project_id}`} className="text-blue-600 hover:underline">
                  View Project
                </Link>
              ) : null
            }
          />
        </InfoGrid>
      </DetailSection>
    </div>
  );
}
