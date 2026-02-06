import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { changesApi } from '../lib/api';
import { DetailPageHeader, DetailSection, InfoGrid, InfoItem } from '../components/ui';
import { StatusBadge } from '../components/forms';
import { Edit, Send, Play, CheckCircle, XCircle } from 'lucide-react';

interface Change {
  id: string;
  eco_number: string;
  title: string;
  description: string | null;
  change_type: string;
  reason: string | null;
  urgency: string | null;
  status: string;
  priority: string;
  requester: string | null;
  affected_parts: string[];
  affected_boms: string[];
  created_at: string | null;
  submitted_at: string | null;
  implementation_date: string | null;
}

export function ChangeDetail() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ['change', id],
    queryFn: () => changesApi.get(id!),
    enabled: !!id,
  });

  const change: Change | undefined = data?.data;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error || !change) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-500">Change not found</p>
      </div>
    );
  }

  const canEdit = change.status === 'draft';
  const canSubmit = change.status === 'draft';
  const canStartReview = change.status === 'submitted';
  const canApprove = change.status === 'in_review';

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  const urgencyColors: Record<string, string> = {
    low: 'bg-gray-100 text-gray-800',
    medium: 'bg-yellow-100 text-yellow-800',
    high: 'bg-orange-100 text-orange-800',
    critical: 'bg-red-100 text-red-800',
  };

  const affectedParts = change.affected_parts || [];
  const affectedBoms = change.affected_boms || [];

  return (
    <div className="space-y-6">
      <DetailPageHeader
        title={change.eco_number}
        subtitle={change.title}
        backLink="/changes"
        backLabel="Back to Changes"
        actions={
          <>
            {canEdit && (
              <Link
                to={`/changes/${id}/edit`}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                <Edit className="h-4 w-4" />
                Edit
              </Link>
            )}
            {canSubmit && (
              <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                <Send className="h-4 w-4" />
                Submit
              </button>
            )}
            {canStartReview && (
              <button className="flex items-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700">
                <Play className="h-4 w-4" />
                Start Review
              </button>
            )}
            {canApprove && (
              <>
                <button className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
                  <CheckCircle className="h-4 w-4" />
                  Approve
                </button>
                <button className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">
                  <XCircle className="h-4 w-4" />
                  Reject
                </button>
              </>
            )}
          </>
        }
      />

      <div className="flex items-center gap-4">
        <StatusBadge status={change.status} />
        {change.urgency && (
          <StatusBadge status={change.urgency} colorMap={urgencyColors} />
        )}
        <span className="text-sm text-gray-500">Type: {change.change_type}</span>
      </div>

      <DetailSection title="General Information">
        <InfoGrid>
          <InfoItem label="ECO Number" value={change.eco_number} />
          <InfoItem label="Title" value={change.title} />
          <InfoItem label="Type" value={change.change_type} />
          <InfoItem label="Priority" value={change.priority} />
          <InfoItem label="Reason" value={change.reason} />
          <InfoItem label="Requester" value={change.requester} />
        </InfoGrid>
        {change.description && (
          <div className="mt-6">
            <dt className="text-sm font-medium text-gray-500">Description</dt>
            <dd className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">
              {change.description}
            </dd>
          </div>
        )}
      </DetailSection>

      <DetailSection title="Timeline">
        <InfoGrid columns={3}>
          <InfoItem label="Created" value={formatDate(change.created_at)} />
          <InfoItem label="Submitted" value={formatDate(change.submitted_at)} />
          <InfoItem label="Implementation" value={formatDate(change.implementation_date)} />
        </InfoGrid>
      </DetailSection>

      <DetailSection title={`Affected Parts (${affectedParts.length})`}>
        {affectedParts.length === 0 ? (
          <p className="text-gray-500">No affected parts</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {affectedParts.map((partId) => (
              <Link
                key={partId}
                to={`/parts/${partId}`}
                className="px-3 py-1 bg-gray-100 rounded-lg text-sm text-gray-700 hover:bg-gray-200"
              >
                {partId}
              </Link>
            ))}
          </div>
        )}
      </DetailSection>

      <DetailSection title={`Affected BOMs (${affectedBoms.length})`}>
        {affectedBoms.length === 0 ? (
          <p className="text-gray-500">No affected BOMs</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {affectedBoms.map((bomId) => (
              <Link
                key={bomId}
                to={`/boms/${bomId}`}
                className="px-3 py-1 bg-gray-100 rounded-lg text-sm text-gray-700 hover:bg-gray-200"
              >
                {bomId}
              </Link>
            ))}
          </div>
        )}
      </DetailSection>
    </div>
  );
}
