import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { bulletinsApi } from '../lib/api';
import { DetailPageHeader, DetailSection, InfoGrid, InfoItem } from '../components/ui';
import { StatusBadge } from '../components/forms';
import { AlertTriangle } from 'lucide-react';

interface Bulletin {
  id: string;
  bulletin_number: string;
  bulletin_type: string;
  status: string;
  title: string;
  summary: string | null;
  description: string | null;
  action_required: string | null;
  safety_issue: boolean;
  compliance_deadline: string | null;
  effective_date: string | null;
}

export function BulletinDetail() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ['bulletin', id],
    queryFn: () => bulletinsApi.get(id!),
    enabled: !!id,
  });

  const bulletin: Bulletin | undefined = data?.data;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error || !bulletin) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-500">Bulletin not found</p>
      </div>
    );
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  const typeColors: Record<string, string> = {
    mandatory: 'bg-red-100 text-red-800',
    optional: 'bg-blue-100 text-blue-800',
    alert: 'bg-orange-100 text-orange-800',
  };

  return (
    <div className="space-y-6">
      <DetailPageHeader
        title={bulletin.bulletin_number}
        subtitle={bulletin.title}
        backLink="/bulletins"
        backLabel="Back to Bulletins"
      />

      <div className="flex items-center gap-4">
        <StatusBadge status={bulletin.status} />
        <StatusBadge status={bulletin.bulletin_type} colorMap={typeColors} />
        {bulletin.safety_issue && (
          <span className="flex items-center gap-1 px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded">
            <AlertTriangle className="h-3 w-3" />
            Safety Issue
          </span>
        )}
      </div>

      <DetailSection title="General Information">
        <InfoGrid>
          <InfoItem label="Bulletin Number" value={bulletin.bulletin_number} />
          <InfoItem label="Title" value={bulletin.title} />
          <InfoItem label="Type" value={bulletin.bulletin_type} />
          <InfoItem label="Status" value={bulletin.status} />
          <InfoItem label="Effective Date" value={formatDate(bulletin.effective_date)} />
          <InfoItem label="Compliance Deadline" value={formatDate(bulletin.compliance_deadline)} />
        </InfoGrid>
      </DetailSection>

      {bulletin.summary && (
        <DetailSection title="Summary">
          <p className="text-sm text-gray-900">{bulletin.summary}</p>
        </DetailSection>
      )}

      {bulletin.description && (
        <DetailSection title="Description">
          <p className="text-sm text-gray-900 whitespace-pre-wrap">{bulletin.description}</p>
        </DetailSection>
      )}

      {bulletin.action_required && (
        <DetailSection title="Action Required">
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800 whitespace-pre-wrap">
              {bulletin.action_required}
            </p>
          </div>
        </DetailSection>
      )}
    </div>
  );
}
