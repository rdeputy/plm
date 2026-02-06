import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { suppliersApi } from '../lib/api';
import { Search, Building2, Truck } from 'lucide-react';

interface Manufacturer {
  id: string;
  manufacturer_code: string;
  name: string;
  country: string | null;
  status: string;
  website: string | null;
}

interface Vendor {
  id: string;
  vendor_code: string;
  name: string;
  tier: string;
  status: string;
  contact_email: string | null;
}

export function Suppliers() {
  const [tab, setTab] = useState<'manufacturers' | 'vendors'>('manufacturers');
  const [search, setSearch] = useState('');

  const { data: mfgData, isLoading: mfgLoading } = useQuery({
    queryKey: ['manufacturers', search],
    queryFn: () => suppliersApi.listManufacturers({ ...(search && { search }) }),
    enabled: tab === 'manufacturers',
  });

  const { data: vendorData, isLoading: vendorLoading } = useQuery({
    queryKey: ['vendors', search],
    queryFn: () => suppliersApi.listVendors({ ...(search && { search }) }),
    enabled: tab === 'vendors',
  });

  const manufacturers: Manufacturer[] = mfgData?.data ?? [];
  const vendors: Vendor[] = vendorData?.data ?? [];

  const statusColors: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    inactive: 'bg-gray-100 text-gray-800',
    suspended: 'bg-red-100 text-red-800',
  };

  const tierColors: Record<string, string> = {
    preferred: 'bg-blue-100 text-blue-800',
    approved: 'bg-green-100 text-green-800',
    conditional: 'bg-yellow-100 text-yellow-800',
    disqualified: 'bg-red-100 text-red-800',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Suppliers</h1>
      </div>

      <div className="flex gap-4">
        <div className="flex bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setTab('manufacturers')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
              tab === 'manufacturers'
                ? 'bg-white shadow text-gray-900'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Building2 className="h-4 w-4" />
            Manufacturers
          </button>
          <button
            onClick={() => setTab('vendors')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
              tab === 'vendors'
                ? 'bg-white shadow text-gray-900'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Truck className="h-4 w-4" />
            Vendors
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
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {tab === 'manufacturers' ? (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Code
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Country
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Website
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {mfgLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : manufacturers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                    No manufacturers found
                  </td>
                </tr>
              ) : (
                manufacturers.map((mfg) => (
                  <tr key={mfg.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                      {mfg.manufacturer_code}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {mfg.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {mfg.country || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          statusColors[mfg.status] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {mfg.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-600">
                      {mfg.website ? (
                        <a href={mfg.website} target="_blank" rel="noopener noreferrer">
                          {mfg.website}
                        </a>
                      ) : (
                        '-'
                      )}
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
                  Code
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tier
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Contact
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {vendorLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : vendors.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                    No vendors found
                  </td>
                </tr>
              ) : (
                vendors.map((vendor) => (
                  <tr key={vendor.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                      {vendor.vendor_code}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {vendor.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          tierColors[vendor.tier] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {vendor.tier}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          statusColors[vendor.status] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {vendor.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {vendor.contact_email || '-'}
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
