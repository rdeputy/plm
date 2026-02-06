import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Parts } from './pages/Parts';
import { Projects } from './pages/Projects';
import { Boms } from './pages/Boms';
import { Documents } from './pages/Documents';
import { Changes } from './pages/Changes';
import { Requirements } from './pages/Requirements';
import { Suppliers } from './pages/Suppliers';
import { Compliance } from './pages/Compliance';
import { Costing } from './pages/Costing';
import { Bulletins } from './pages/Bulletins';
import { Placeholder } from './pages/Placeholder';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="parts" element={<Parts />} />
            <Route path="parts/:id" element={<Placeholder />} />
            <Route path="boms" element={<Boms />} />
            <Route path="boms/:id" element={<Placeholder />} />
            <Route path="documents" element={<Documents />} />
            <Route path="documents/:id" element={<Placeholder />} />
            <Route path="changes" element={<Changes />} />
            <Route path="changes/:id" element={<Placeholder />} />
            <Route path="projects" element={<Projects />} />
            <Route path="projects/:id" element={<Placeholder />} />
            <Route path="requirements" element={<Requirements />} />
            <Route path="requirements/:id" element={<Placeholder />} />
            <Route path="suppliers" element={<Suppliers />} />
            <Route path="compliance" element={<Compliance />} />
            <Route path="costing" element={<Costing />} />
            <Route path="bulletins" element={<Bulletins />} />
            <Route path="bulletins/:id" element={<Placeholder />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
