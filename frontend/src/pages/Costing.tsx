import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { costingApi } from '../lib/api';
import { Search, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';

interface CostVariance {
  id: string;
  part_id: string;
  part_number: string;
  period: string;
  standard_cost: number;
  actual_cost: number;
  variance: number;
  variance_percent: number;
  favorable: boolean;
}

export function Costing() {
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'unfavorable'>('all');

  const { data, isLoading } = useQuery({
    queryKey: ['variances', search],
    queryFn: () => costingApi.listVariances({ ...(search && { search }) }),
  });

  const allVariances: CostVariance[] = data?.data ?? [];
  const variances =
    filterType === 'unfavorable'
      ? allVariances.filter((v) => !v.favorable)
      : allVariances;

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
  };

  const totalVariance = variances.reduce((sum, v) => sum + v.variance, 0);
  const unfavorableCount = variances.filter((v) => !v.favorable).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Cost Variances</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Total Variance</div>
          <div
            className={`text-2xl font-bold ${
              totalVariance > 0 ? 'text-red-600' : 'text-green-600'
            }`}
          >
            {formatCurrency(totalVariance)}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Items Analyzed</div>
          <div className="text-2xl font-bold text-gray-900">{variances.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Unfavorable Variances</div>
          <div className="text-2xl font-bold text-red-600">{unfavorableCount}</div>
        </div>
      </div>

      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by part number..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value as 'all' | 'unfavorable')}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Variances</option>
          <option value="unfavorable">Unfavorable Only</option>
        </select>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Part Number
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Period
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Standard Cost
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actual Cost
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Variance
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Variance %
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                  Loading...
                </td>
              </tr>
            ) : variances.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                  No cost variances found
                </td>
              </tr>
            ) : (
              variances.map((variance) => (
                <tr key={variance.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                    {variance.part_number}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {variance.period}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    {formatCurrency(variance.standard_cost)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    {formatCurrency(variance.actual_cost)}
                  </td>
                  <td
                    className={`px-6 py-4 whitespace-nowrap text-sm font-medium text-right ${
                      variance.favorable ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {formatCurrency(variance.variance)}
                  </td>
                  <td
                    className={`px-6 py-4 whitespace-nowrap text-sm font-medium text-right ${
                      variance.favorable ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {formatPercent(variance.variance_percent)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    {variance.favorable ? (
                      <span className="inline-flex items-center gap-1 text-green-600">
                        <TrendingDown className="h-4 w-4" />
                        Favorable
                      </span>
                    ) : Math.abs(variance.variance_percent) > 10 ? (
                      <span className="inline-flex items-center gap-1 text-red-600">
                        <AlertTriangle className="h-4 w-4" />
                        Critical
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-orange-600">
                        <TrendingUp className="h-4 w-4" />
                        Unfavorable
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
