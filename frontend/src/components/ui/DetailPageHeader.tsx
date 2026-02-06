import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

interface DetailPageHeaderProps {
  title: string;
  subtitle?: string;
  backLink: string;
  backLabel?: string;
  actions?: ReactNode;
}

export function DetailPageHeader({
  title,
  subtitle,
  backLink,
  backLabel = 'Back',
  actions,
}: DetailPageHeaderProps) {
  return (
    <div className="space-y-4">
      <Link
        to={backLink}
        className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" />
        {backLabel}
      </Link>
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          {subtitle && <p className="text-gray-500 mt-1">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}
