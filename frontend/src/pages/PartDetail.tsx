import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { partsApi } from '../lib/api';
import { DetailPageHeader, DetailSection, InfoGrid, InfoItem } from '../components/ui';
import { StatusBadge } from '../components/forms';
import { Edit, CheckCircle, RefreshCw } from 'lucide-react';

interface Part {
  id: string;
  part_number: string;
  revision: string;
  name: string;
  description: string | null;
  part_type: string;
  status: string;
  category: string | null;
  csi_code: string | null;
  uniformat_code: string | null;
  unit_of_measure: string;
  unit_cost: number | null;
  manufacturer: string | null;
  manufacturer_pn: string | null;
  lead_time_days: number | null;
}

export function PartDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['part', id],
    queryFn: () => partsApi.get(id!),
    enabled: !!id,
  });

  const releaseMutation = useMutation({
    mutationFn: () => partsApi.release(id!, 'current-user'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['part', id] });
    },
  });

  const part: Part | undefined = data?.data;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error || !part) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-500">Part not found</p>
      </div>
    );
  }

  const canEdit = part.status === 'draft' || part.status === 'in_review';
  const canRelease = part.status === 'in_review';
  const canRevise = part.status === 'released';

  const formatCurrency = (value: number | null) => {
    if (value === null) return '-';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  return (
    <div className="space-y-6">
      <DetailPageHeader
        title={`${part.part_number} Rev ${part.revision}`}
        subtitle={part.name}
        backLink="/parts"
        backLabel="Back to Parts"
        actions={
          <>
            {canEdit && (
              <Link
                to={`/parts/${id}/edit`}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                <Edit className="h-4 w-4" />
                Edit
              </Link>
            )}
            {canRelease && (
              <button
                onClick={() => releaseMutation.mutate()}
                disabled={releaseMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                <CheckCircle className="h-4 w-4" />
                {releaseMutation.isPending ? 'Releasing...' : 'Release'}
              </button>
            )}
            {canRevise && (
              <button
                onClick={() => navigate(`/parts/${id}/revise`)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <RefreshCw className="h-4 w-4" />
                Revise
              </button>
            )}
          </>
        }
      />

      <div className="flex items-center gap-4">
        <StatusBadge status={part.status} />
        <span className="text-sm text-gray-500">Type: {part.part_type}</span>
      </div>

      <DetailSection title="General Information">
        <InfoGrid>
          <InfoItem label="Part Number" value={part.part_number} />
          <InfoItem label="Revision" value={part.revision} />
          <InfoItem label="Name" value={part.name} />
          <InfoItem label="Type" value={part.part_type} />
          <InfoItem label="Category" value={part.category} />
          <InfoItem label="Unit of Measure" value={part.unit_of_measure} />
        </InfoGrid>
        {part.description && (
          <div className="mt-6">
            <dt className="text-sm font-medium text-gray-500">Description</dt>
            <dd className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">
              {part.description}
            </dd>
          </div>
        )}
      </DetailSection>

      <DetailSection title="Classification">
        <InfoGrid columns={2}>
          <InfoItem label="CSI Code" value={part.csi_code} />
          <InfoItem label="Uniformat Code" value={part.uniformat_code} />
        </InfoGrid>
      </DetailSection>

      <DetailSection title="Cost & Procurement">
        <InfoGrid>
          <InfoItem label="Unit Cost" value={formatCurrency(part.unit_cost)} />
          <InfoItem label="Manufacturer" value={part.manufacturer} />
          <InfoItem label="Manufacturer P/N" value={part.manufacturer_pn} />
          <InfoItem
            label="Lead Time"
            value={part.lead_time_days ? `${part.lead_time_days} days` : null}
          />
        </InfoGrid>
      </DetailSection>
    </div>
  );
}
