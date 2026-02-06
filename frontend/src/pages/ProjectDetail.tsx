import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { projectsApi } from '../lib/api';
import { DetailPageHeader, DetailSection, InfoGrid, InfoItem, TabPanel } from '../components/ui';
import { StatusBadge } from '../components/forms';
import { Edit, Plus } from 'lucide-react';

interface Milestone {
  id: string;
  milestone_number: string;
  name: string;
  status: string;
  planned_date: string | null;
  actual_date: string | null;
}

interface Deliverable {
  id: string;
  deliverable_number: string;
  name: string;
  status: string;
  due_date: string | null;
  percent_complete: number;
}

interface Project {
  id: string;
  project_number: string;
  name: string;
  description: string | null;
  project_type: string | null;
  status: string;
  phase: string | null;
  customer_name: string | null;
  project_manager_name: string | null;
  start_date: string | null;
  target_end_date: string | null;
  budget: number | null;
  actual_cost: number | null;
  currency: string;
}

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id!),
    enabled: !!id,
  });

  const { data: milestonesData } = useQuery({
    queryKey: ['project', id, 'milestones'],
    queryFn: () => projectsApi.getMilestones(id!),
    enabled: !!id,
  });

  const { data: deliverablesData } = useQuery({
    queryKey: ['project', id, 'deliverables'],
    queryFn: () => projectsApi.getDeliverables(id!),
    enabled: !!id,
  });

  const project: Project | undefined = data?.data;
  const milestones: Milestone[] = milestonesData?.data || [];
  const deliverables: Deliverable[] = deliverablesData?.data || [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-500">Project not found</p>
      </div>
    );
  }

  const canEdit = project.status === 'proposed' || project.status === 'active';

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  const formatCurrency = (value: number | null) => {
    if (value === null) return '-';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: project.currency || 'USD',
    }).format(value);
  };

  const milestoneStatusColors: Record<string, string> = {
    not_started: 'bg-gray-100 text-gray-800',
    in_progress: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    at_risk: 'bg-red-100 text-red-800',
  };

  const OverviewTab = (
    <div className="space-y-6">
      <DetailSection title="General Information">
        <InfoGrid>
          <InfoItem label="Project Number" value={project.project_number} />
          <InfoItem label="Name" value={project.name} />
          <InfoItem label="Type" value={project.project_type} />
          <InfoItem label="Phase" value={project.phase} />
          <InfoItem label="Customer" value={project.customer_name} />
          <InfoItem label="Project Manager" value={project.project_manager_name} />
        </InfoGrid>
        {project.description && (
          <div className="mt-6">
            <dt className="text-sm font-medium text-gray-500">Description</dt>
            <dd className="mt-1 text-sm text-gray-900">{project.description}</dd>
          </div>
        )}
      </DetailSection>

      <DetailSection title="Schedule">
        <InfoGrid columns={2}>
          <InfoItem label="Start Date" value={formatDate(project.start_date)} />
          <InfoItem label="Target End Date" value={formatDate(project.target_end_date)} />
        </InfoGrid>
      </DetailSection>

      <DetailSection title="Budget">
        <InfoGrid columns={2}>
          <InfoItem label="Budget" value={formatCurrency(project.budget)} />
          <InfoItem label="Actual Cost" value={formatCurrency(project.actual_cost)} />
        </InfoGrid>
      </DetailSection>
    </div>
  );

  const MilestonesTab = (
    <DetailSection
      title={`Milestones (${milestones.length})`}
      actions={
        <button className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
          <Plus className="h-4 w-4" /> Add
        </button>
      }
    >
      {milestones.length === 0 ? (
        <p className="text-gray-500">No milestones defined</p>
      ) : (
        <div className="space-y-4">
          {milestones.map((m) => (
            <div key={m.id} className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <div className="font-medium text-gray-900">{m.name}</div>
                <div className="text-sm text-gray-500">{m.milestone_number}</div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-sm text-gray-500">
                  {formatDate(m.actual_date || m.planned_date)}
                </div>
                <StatusBadge status={m.status} colorMap={milestoneStatusColors} />
              </div>
            </div>
          ))}
        </div>
      )}
    </DetailSection>
  );

  const DeliverablesTab = (
    <DetailSection
      title={`Deliverables (${deliverables.length})`}
      actions={
        <button className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
          <Plus className="h-4 w-4" /> Add
        </button>
      }
    >
      {deliverables.length === 0 ? (
        <p className="text-gray-500">No deliverables defined</p>
      ) : (
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Deliverable
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Due Date
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Progress
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {deliverables.map((d) => (
              <tr key={d.id}>
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900">{d.name}</div>
                  <div className="text-sm text-gray-500">{d.deliverable_number}</div>
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">{formatDate(d.due_date)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-24 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${d.percent_complete}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-500">{d.percent_complete}%</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={d.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </DetailSection>
  );

  return (
    <div className="space-y-6">
      <DetailPageHeader
        title={project.project_number}
        subtitle={project.name}
        backLink="/projects"
        backLabel="Back to Projects"
        actions={
          canEdit && (
            <Link
              to={`/projects/${id}/edit`}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <Edit className="h-4 w-4" />
              Edit
            </Link>
          )
        }
      />

      <div className="flex items-center gap-4">
        <StatusBadge status={project.status} />
        {project.phase && <span className="text-sm text-gray-500">Phase: {project.phase}</span>}
      </div>

      <TabPanel
        tabs={[
          { id: 'overview', label: 'Overview', content: OverviewTab },
          { id: 'milestones', label: 'Milestones', content: MilestonesTab },
          { id: 'deliverables', label: 'Deliverables', content: DeliverablesTab },
        ]}
      />
    </div>
  );
}
