import { useState } from 'react';
import type { ReactNode } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface DetailSectionProps {
  title: string;
  children: ReactNode;
  collapsible?: boolean;
  defaultOpen?: boolean;
  actions?: ReactNode;
}

export function DetailSection({
  title,
  children,
  collapsible = false,
  defaultOpen = true,
  actions,
}: DetailSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="bg-white rounded-lg shadow">
      <div
        className={`px-6 py-4 border-b border-gray-200 flex items-center justify-between ${
          collapsible ? 'cursor-pointer hover:bg-gray-50' : ''
        }`}
        onClick={collapsible ? () => setIsOpen(!isOpen) : undefined}
      >
        <div className="flex items-center gap-2">
          {collapsible && (
            <span className="text-gray-400">
              {isOpen ? (
                <ChevronDown className="h-5 w-5" />
              ) : (
                <ChevronRight className="h-5 w-5" />
              )}
            </span>
          )}
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        </div>
        {actions && (
          <div onClick={(e) => e.stopPropagation()}>{actions}</div>
        )}
      </div>
      {(!collapsible || isOpen) && <div className="p-6">{children}</div>}
    </div>
  );
}
