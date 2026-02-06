import type { ReactNode } from 'react';

interface InfoItemProps {
  label: string;
  value: ReactNode;
}

export function InfoItem({ label, value }: InfoItemProps) {
  return (
    <div>
      <dt className="text-sm font-medium text-gray-500">{label}</dt>
      <dd className="mt-1 text-sm text-gray-900">{value || '-'}</dd>
    </div>
  );
}

interface InfoGridProps {
  children: ReactNode;
  columns?: 2 | 3 | 4;
}

export function InfoGrid({ children, columns = 3 }: InfoGridProps) {
  const colClass = {
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
  }[columns];

  return <dl className={`grid ${colClass} gap-6`}>{children}</dl>;
}
