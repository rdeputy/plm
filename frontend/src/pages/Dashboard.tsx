import { useQuery } from '@tanstack/react-query';
import { partsApi, projectsApi, changesApi } from '../lib/api';
import { Box, FolderKanban, ArrowLeftRight, AlertCircle } from 'lucide-react';

export function Dashboard() {
  const { data: parts } = useQuery({
    queryKey: ['parts', 'count'],
    queryFn: () => partsApi.list({ limit: '1' }),
  });

  const { data: projects } = useQuery({
    queryKey: ['projects', 'active'],
    queryFn: () => projectsApi.list({ status: 'active', limit: '5' }),
  });

  const { data: changes } = useQuery({
    queryKey: ['changes', 'pending'],
    queryFn: () => changesApi.list({ status: 'pending', limit: '5' }),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Box className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Parts</p>
              <p className="text-2xl font-bold">
                {parts?.data?.length ?? '...'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <FolderKanban className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Active Projects</p>
              <p className="text-2xl font-bold">
                {projects?.data?.length ?? '...'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-yellow-100 rounded-lg">
              <ArrowLeftRight className="h-6 w-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Pending Changes</p>
              <p className="text-2xl font-bold">
                {changes?.data?.length ?? '...'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold">Active Projects</h2>
          </div>
          <div className="p-6">
            {projects?.data?.length ? (
              <ul className="space-y-3">
                {projects.data.map((project: any) => (
                  <li
                    key={project.id}
                    className="flex items-center justify-between"
                  >
                    <div>
                      <p className="font-medium">{project.name}</p>
                      <p className="text-sm text-gray-500">
                        {project.project_number}
                      </p>
                    </div>
                    <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded">
                      {project.phase}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500">No active projects</p>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold">Pending Changes</h2>
          </div>
          <div className="p-6">
            {changes?.data?.length ? (
              <ul className="space-y-3">
                {changes.data.map((change: any) => (
                  <li key={change.id} className="flex items-center gap-3">
                    <AlertCircle className="h-5 w-5 text-yellow-500" />
                    <div>
                      <p className="font-medium">{change.eco_number}</p>
                      <p className="text-sm text-gray-500">{change.title}</p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500">No pending changes</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
