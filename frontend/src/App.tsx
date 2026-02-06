import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Parts } from './pages/Parts';
import { Projects } from './pages/Projects';
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
            <Route path="boms" element={<Placeholder />} />
            <Route path="boms/:id" element={<Placeholder />} />
            <Route path="documents" element={<Placeholder />} />
            <Route path="documents/:id" element={<Placeholder />} />
            <Route path="changes" element={<Placeholder />} />
            <Route path="changes/:id" element={<Placeholder />} />
            <Route path="projects" element={<Projects />} />
            <Route path="projects/:id" element={<Placeholder />} />
            <Route path="requirements" element={<Placeholder />} />
            <Route path="suppliers" element={<Placeholder />} />
            <Route path="compliance" element={<Placeholder />} />
            <Route path="costing" element={<Placeholder />} />
            <Route path="bulletins" element={<Placeholder />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
