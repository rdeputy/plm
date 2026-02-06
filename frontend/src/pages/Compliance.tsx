import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { complianceApi } from '../lib/api';
import { Search, Shield, Award } from 'lucide-react';

interface Regulation {
  id: string;
  regulation_code: string;
  name: string;
  regulation_type: string;
  jurisdiction: string | null;
  status: string;
  effective_date: string | null;
}

interface Certificate {
  id: string;
  certificate_number: string;
  regulation_id: string;
  issuing_authority: string;
  issue_date: string;
  expiry_date: string | null;
  status: string;
  scope: string | null;
}

export function Compliance() {
  const [tab, setTab] = useState<'regulations' | 'certificates'>('regulations');
  const [search, setSearch] = useState('');

  const { data: regData, isLoading: regLoading } = useQuery({
    queryKey: ['regulations', search],
    queryFn: () => complianceApi.listRegulations({ ...(search && { search }) }),
    enabled: tab === 'regulations',
  });

  const { data: certData, isLoading: certLoading } = useQuery({
    queryKey: ['certificates', search],
    queryFn: () => complianceApi.listCertificates({ ...(search && { search }) }),
    enabled: tab === 'certificates',
  });

  const regulations: Regulation[] = regData?.data ?? [];
  const certificates: Certificate[] = certData?.data ?? [];

  const statusColors: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    pending: 'bg-yellow-100 text-yellow-800',
    expired: 'bg-red-100 text-red-800',
    superseded: 'bg-gray-100 text-gray-800',
  };

  const typeColors: Record<string, string> = {
    ROHS: 'bg-green-100 text-green-800',
    REACH: 'bg-blue-100 text-blue-800',
    WEEE: 'bg-purple-100 text-purple-800',
    CONFLICT_MINERALS: 'bg-orange-100 text-orange-800',
    AS9100: 'bg-indigo-100 text-indigo-800',
    ISO9001: 'bg-cyan-100 text-cyan-800',
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  const isExpiringSoon = (expiryDate: string | null) => {
    if (!expiryDate) return false;
    const expiry = new Date(expiryDate);
    const thirtyDays = new Date();
    thirtyDays.setDate(thirtyDays.getDate() + 30);
    return expiry <= thirtyDays;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Compliance</h1>
      </div>

      <div className="flex gap-4">
        <div className="flex bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setTab('regulations')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
              tab === 'regulations'
                ? 'bg-white shadow text-gray-900'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Shield className="h-4 w-4" />
            Regulations
          </button>
          <button
            onClick={() => setTab('certificates')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
              tab === 'certificates'
                ? 'bg-white shadow text-gray-900'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Award className="h-4 w-4" />
            Certificates
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
        {tab === 'regulations' ? (
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
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Jurisdiction
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Effective Date
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {regLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : regulations.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    No regulations found
                  </td>
                </tr>
              ) : (
                regulations.map((reg) => (
                  <tr key={reg.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                      {reg.regulation_code}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {reg.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          typeColors[reg.regulation_type] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {reg.regulation_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {reg.jurisdiction || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          statusColors[reg.status] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {reg.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(reg.effective_date)}
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
                  Certificate Number
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Issuing Authority
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Scope
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Issue Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Expiry Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {certLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : certificates.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    No certificates found
                  </td>
                </tr>
              ) : (
                certificates.map((cert) => (
                  <tr key={cert.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                      {cert.certificate_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {cert.issuing_authority}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {cert.scope || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(cert.issue_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={
                          isExpiringSoon(cert.expiry_date)
                            ? 'text-sm text-red-600 font-medium'
                            : 'text-sm text-gray-500'
                        }
                      >
                        {formatDate(cert.expiry_date)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          statusColors[cert.status] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {cert.status}
                      </span>
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
