interface StatusBadgeProps {
  status: string;
  colorMap?: Record<string, string>;
}

const defaultColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-800',
  in_review: 'bg-yellow-100 text-yellow-800',
  released: 'bg-green-100 text-green-800',
  approved: 'bg-green-100 text-green-800',
  active: 'bg-green-100 text-green-800',
  obsolete: 'bg-red-100 text-red-800',
  rejected: 'bg-red-100 text-red-800',
  cancelled: 'bg-red-100 text-red-800',
  pending: 'bg-yellow-100 text-yellow-800',
  submitted: 'bg-blue-100 text-blue-800',
  implemented: 'bg-purple-100 text-purple-800',
  closed: 'bg-gray-100 text-gray-800',
};

export function StatusBadge({ status, colorMap }: StatusBadgeProps) {
  const colors = colorMap || defaultColors;
  const colorClass = colors[status] || 'bg-gray-100 text-gray-800';

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded ${colorClass}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}
