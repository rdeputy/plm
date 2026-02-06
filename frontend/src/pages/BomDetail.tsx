import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { bomsApi } from '../lib/api';
import { DetailPageHeader, DetailSection, InfoGrid, InfoItem } from '../components/ui';
import { StatusBadge } from '../components/forms';
import { Edit, ExternalLink } from 'lucide-react';

interface BomItem {
  id: string;
  part_id: string;
  part_number: string;
  part_revision: string;
  quantity: number;
  unit_of_measure: string;
  find_number: string | null;
  reference_designator: string | null;
  notes: string | null;
}

interface Bom {
  id: string;
  bom_number: string;
  revision: string;
  name: string;
  description: string | null;
  bom_type: string;
  status: string;
  parent_part_id: string | null;
  effectivity: string | null;
  effective_from: string | null;
  effective_to: string | null;
  items: BomItem[];
}

export function BomDetail() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ['bom', id],
    queryFn: () => bomsApi.get(id!),
    enabled: !!id,
  });

  const bom: Bom | undefined = data?.data;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error || !bom) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-500">BOM not found</p>
      </div>
    );
  }

  const canEdit = bom.status === 'draft' || bom.status === 'in_review';
  const items = bom.items || [];

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  return (
    <div className="space-y-6">
      <DetailPageHeader
        title={`${bom.bom_number} Rev ${bom.revision}`}
        subtitle={bom.name}
        backLink="/boms"
        backLabel="Back to BOMs"
        actions={
          canEdit && (
            <Link
              to={`/boms/${id}/edit`}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <Edit className="h-4 w-4" />
              Edit
            </Link>
          )
        }
      />

      <div className="flex items-center gap-4">
        <StatusBadge status={bom.status} />
        <span className="text-sm text-gray-500">Type: {bom.bom_type}</span>
      </div>

      <DetailSection title="General Information">
        <InfoGrid>
          <InfoItem label="BOM Number" value={bom.bom_number} />
          <InfoItem label="Revision" value={bom.revision} />
          <InfoItem label="Name" value={bom.name} />
          <InfoItem label="Type" value={bom.bom_type} />
          <InfoItem label="Effectivity" value={bom.effectivity} />
          <InfoItem
            label="Parent Part"
            value={
              bom.parent_part_id ? (
                <Link to={`/parts/${bom.parent_part_id}`} className="text-blue-600 hover:underline">
                  View Part
                </Link>
              ) : null
            }
          />
        </InfoGrid>
        {bom.description && (
          <div className="mt-6">
            <dt className="text-sm font-medium text-gray-500">Description</dt>
            <dd className="mt-1 text-sm text-gray-900">{bom.description}</dd>
          </div>
        )}
      </DetailSection>

      <DetailSection title="Effectivity Dates">
        <InfoGrid columns={2}>
          <InfoItem label="Effective From" value={formatDate(bom.effective_from)} />
          <InfoItem label="Effective To" value={formatDate(bom.effective_to)} />
        </InfoGrid>
      </DetailSection>

      <DetailSection title={`Line Items (${items.length})`}>
        {items.length === 0 ? (
          <p className="text-gray-500">No items in this BOM</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Find #
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Part Number
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Qty
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    UoM
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Ref Des
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Notes
                  </th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-900">{item.find_number || '-'}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className="font-medium text-gray-900">{item.part_number}</span>
                      <span className="text-gray-500 ml-1">Rev {item.part_revision}</span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-right">{item.quantity}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{item.unit_of_measure}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {item.reference_designator || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">
                      {item.notes || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <Link
                        to={`/parts/${item.part_id}`}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </DetailSection>
    </div>
  );
}
