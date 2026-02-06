import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  Box,
  FileText,
  FolderTree,
  ClipboardList,
  Users,
  Shield,
  DollarSign,
  Wrench,
  FolderKanban,
  ArrowLeftRight,
  Menu,
  X,
} from 'lucide-react';
import { useState } from 'react';

const navigation = [
  { name: 'Parts', href: '/parts', icon: Box },
  { name: 'BOMs', href: '/boms', icon: FolderTree },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Changes', href: '/changes', icon: ArrowLeftRight },
  { name: 'Projects', href: '/projects', icon: FolderKanban },
  { name: 'Requirements', href: '/requirements', icon: ClipboardList },
  { name: 'Suppliers', href: '/suppliers', icon: Users },
  { name: 'Compliance', href: '/compliance', icon: Shield },
  { name: 'Costing', href: '/costing', icon: DollarSign },
  { name: 'Bulletins', href: '/bulletins', icon: Wrench },
];

export function Layout() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 transform transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-16 items-center justify-between px-4">
          <Link to="/" className="text-xl font-bold text-white">
            PLM System
          </Link>
          <button
            className="lg:hidden text-gray-400 hover:text-white"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-6 w-6" />
          </button>
        </div>
        <nav className="mt-4 px-2 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
                onClick={() => setSidebarOpen(false)}
              >
                <item.icon className="h-5 w-5" />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white border-b border-gray-200">
          <div className="flex h-16 items-center gap-4 px-4">
            <button
              className="lg:hidden text-gray-500 hover:text-gray-700"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-6 w-6" />
            </button>
            <div className="flex-1">
              <input
                type="search"
                placeholder="Search parts, documents..."
                className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
