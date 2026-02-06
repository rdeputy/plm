import { useLocation } from 'react-router-dom';

export function Placeholder() {
  const location = useLocation();
  const pageName = location.pathname.slice(1).replace(/-/g, ' ');

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 capitalize">{pageName}</h1>
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <p className="text-gray-500">
          This page is under construction.
        </p>
      </div>
    </div>
  );
}
