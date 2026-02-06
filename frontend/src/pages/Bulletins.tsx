import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { bulletinsApi } from '../lib/api';
import {
  Plus,
  Search,
  ChevronRight,
  AlertTriangle,
  Wrench,
  Settings,
} from 'lucide-react';

interface ServiceBulletin {
  id: string;
  bulletin_number: string;
  bulletin_type: string;
  status: string;
  title: string;
  summary: string | null;
  safety_issue: boolean;
  compliance_deadline: string | null;
  effective_date: string | null;
}

interface MaintenanceSchedule {
  id: string;
  schedule_code: string;
  part_number: string | null;
  system: string | null;
  interval_type: string;
  interval_value: number;
  interval_unit: string;
  task_description: string | null;
  is_active: boolean;
}

interface UnitConfiguration {
  id: string;
  serial_number: string;
  part_id: string;
  part_number: string;
  current_revision: string;
  total_hours: number;
  total_cycles: number;
  owner_name: string | null;
  location: string | null;
}

export function Bulletins() {
  const [tab, setTab] = useState<'bulletins' | 'maintenance' | 'units'>('bulletins');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const { data: sbData, isLoading: sbLoading } = useQuery({
    queryKey: ['bulletins', search, typeFilter],
    queryFn: () =>
      bulletinsApi.list({
        ...(search && { search }),
        ...(typeFilter && { bulletin_type: typeFilter }),
      }),
    enabled: tab === 'bulletins',
  });

  const { data: maintData, isLoading: maintLoading } = useQuery({
    queryKey: ['maintenance-schedules', search],
    queryFn: () => bulletinsApi.listMaintenanceSchedules({ ...(search && { search }) }),
    enabled: tab === 'maintenance',
  });

  const { data: unitsData, isLoading: unitsLoading } = useQuery({
    queryKey: ['units', search],
    queryFn: () => bulletinsApi.listUnits({ ...(search && { search }) }),
    enabled: tab === 'units',
  });

  const bulletins: ServiceBulletin[] = sbData?.data ?? [];
  const schedules: MaintenanceSchedule[] = maintData?.data ?? [];
  const units: UnitConfiguration[] = unitsData?.data ?? [];

  const statusColors: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-800',
    active: 'bg-green-100 text-green-800',
    superseded: 'bg-yellow-100 text-yellow-800',
    cancelled: 'bg-red-100 text-red-800',
  };

  const typeColors: Record<string, string> = {
    mandatory: 'bg-red-100 text-red-800',
    optional: 'bg-blue-100 text-blue-800',
    alert: 'bg-orange-100 text-orange-800',
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Service Bulletins</h1>
        {tab === 'bulletins' && (
          <Link
            to="/bulletins/new"
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="h-5 w-5" />
            New Bulletin
          </Link>
        )}
      </div>

      <div className="flex gap-4 flex-wrap">
        <div className="flex bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setTab('bulletins')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
              tab === 'bulletins'
                ? 'bg-white shadow text-gray-900'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <AlertTriangle className="h-4 w-4" />
            Bulletins
          </button>
          <button
            onClick={() => setTab('maintenance')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
              tab === 'maintenance'
                ? 'bg-white shadow text-gray-900'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Wrench className="h-4 w-4" />
            Maintenance
          </button>
          <button
            onClick={() => setTab('units')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
              tab === 'units'
                ? 'bg-white shadow text-gray-900'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Settings className="h-4 w-4" />
            Units
          </button>
        </div>
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder={`Search ${tab}...`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        {tab === 'bulletins' && (
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Types</option>
            <option value="mandatory">Mandatory</option>
            <option value="optional">Optional</option>
            <option value="alert">Alert</option>
          </select>
        )}
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {tab === 'bulletins' ? (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Bulletin
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Deadline
                </th>
                <th className="relative px-6 py-3">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sbLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : bulletins.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    No bulletins found
                  </td>
                </tr>
              ) : (
                bulletins.map((sb) => (
                  <tr key={sb.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {sb.safety_issue && (
                          <AlertTriangle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="font-medium text-gray-900">
                          {sb.bulletin_number}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {sb.title}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          typeColors[sb.bulletin_type] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {sb.bulletin_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          statusColors[sb.status] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {sb.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(sb.compliance_deadline)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <Link
                        to={`/bulletins/${sb.id}`}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        <ChevronRight className="h-5 w-5" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        ) : tab === 'maintenance' ? (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Schedule Code
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Part Number
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  System
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Interval
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Task
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Active
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {maintLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : schedules.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    No maintenance schedules found
                  </td>
                </tr>
              ) : (
                schedules.map((sched) => (
                  <tr key={sched.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                      {sched.schedule_code}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {sched.part_number || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {sched.system || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {sched.interval_value} {sched.interval_unit} ({sched.interval_type})
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">
                      {sched.task_description || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          sched.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {sched.is_active ? 'Yes' : 'No'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Serial Number
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Part Number
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Revision
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total Hours
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cycles
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Owner
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Location
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {unitsLoading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : units.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                    No unit configurations found
                  </td>
                </tr>
              ) : (
                units.map((unit) => (
                  <tr key={unit.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                      {unit.serial_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {unit.part_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {unit.current_revision || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                      {unit.total_hours?.toLocaleString() || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                      {unit.total_cycles?.toLocaleString() || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {unit.owner_name || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {unit.location || '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
