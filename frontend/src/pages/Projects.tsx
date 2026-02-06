import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { projectsApi } from '../lib/api';
import { Plus, Search, Calendar } from 'lucide-react';

interface Project {
  id: string;
  project_number: string;
  name: string;
  status: string;
  phase: string;
  customer_name: string | null;
  project_manager_name: string | null;
  target_end_date: string | null;
  budget: number;
  actual_cost: number;
}

export function Projects() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['projects', search, statusFilter],
    queryFn: () =>
      projectsApi.list({
        ...(search && { search }),
        ...(statusFilter && { status: statusFilter }),
      }),
  });

  const projects: Project[] = data?.data ?? [];

  const statusColors: Record<string, string> = {
    proposed: 'bg-gray-100 text-gray-800',
    approved: 'bg-blue-100 text-blue-800',
    active: 'bg-green-100 text-green-800',
    on_hold: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-purple-100 text-purple-800',
    cancelled: 'bg-red-100 text-red-800',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
        <Link
          to="/projects/new"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus className="h-5 w-5" />
          New Project
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search projects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Statuses</option>
          <option value="proposed">Proposed</option>
          <option value="active">Active</option>
          <option value="on_hold">On Hold</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      {/* Project Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          <div className="col-span-full text-center py-8 text-gray-500">
            Loading...
          </div>
        ) : projects.length === 0 ? (
          <div className="col-span-full text-center py-8 text-gray-500">
            No projects found
          </div>
        ) : (
          projects.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="bg-white rounded-lg shadow hover:shadow-md transition-shadow"
            >
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-gray-500">{project.project_number}</p>
                    <h3 className="text-lg font-semibold text-gray-900 mt-1">
                      {project.name}
                    </h3>
                  </div>
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded ${
                      statusColors[project.status] || 'bg-gray-100'
                    }`}
                  >
                    {project.status}
                  </span>
                </div>

                <div className="mt-4 space-y-2">
                  {project.customer_name && (
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Customer:</span>{' '}
                      {project.customer_name}
                    </p>
                  )}
                  {project.project_manager_name && (
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">PM:</span>{' '}
                      {project.project_manager_name}
                    </p>
                  )}
                </div>

                <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Calendar className="h-4 w-4" />
                    {project.target_end_date || 'No deadline'}
                  </div>
                  <span className="text-xs font-medium text-gray-500 uppercase">
                    {project.phase}
                  </span>
                </div>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
