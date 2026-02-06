import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Parts } from './pages/Parts';
import { PartDetail } from './pages/PartDetail';
import { PartFormPage } from './pages/PartFormPage';
import { Projects } from './pages/Projects';
import { ProjectDetail } from './pages/ProjectDetail';
import { Boms } from './pages/Boms';
import { BomDetail } from './pages/BomDetail';
import { Documents } from './pages/Documents';
import { DocumentDetail } from './pages/DocumentDetail';
import { Changes } from './pages/Changes';
import { ChangeDetail } from './pages/ChangeDetail';
import { Requirements } from './pages/Requirements';
import { RequirementDetail } from './pages/RequirementDetail';
import { Suppliers } from './pages/Suppliers';
import { Compliance } from './pages/Compliance';
import { Costing } from './pages/Costing';
import { Bulletins } from './pages/Bulletins';
import { BulletinDetail } from './pages/BulletinDetail';
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

            {/* Parts */}
            <Route path="parts" element={<Parts />} />
            <Route path="parts/new" element={<PartFormPage />} />
            <Route path="parts/:id" element={<PartDetail />} />
            <Route path="parts/:id/edit" element={<PartFormPage />} />

            {/* BOMs */}
            <Route path="boms" element={<Boms />} />
            <Route path="boms/new" element={<Placeholder />} />
            <Route path="boms/:id" element={<BomDetail />} />
            <Route path="boms/:id/edit" element={<Placeholder />} />

            {/* Documents */}
            <Route path="documents" element={<Documents />} />
            <Route path="documents/new" element={<Placeholder />} />
            <Route path="documents/:id" element={<DocumentDetail />} />
            <Route path="documents/:id/edit" element={<Placeholder />} />

            {/* Changes (ECOs) */}
            <Route path="changes" element={<Changes />} />
            <Route path="changes/new" element={<Placeholder />} />
            <Route path="changes/:id" element={<ChangeDetail />} />
            <Route path="changes/:id/edit" element={<Placeholder />} />

            {/* Projects */}
            <Route path="projects" element={<Projects />} />
            <Route path="projects/new" element={<Placeholder />} />
            <Route path="projects/:id" element={<ProjectDetail />} />
            <Route path="projects/:id/edit" element={<Placeholder />} />

            {/* Requirements */}
            <Route path="requirements" element={<Requirements />} />
            <Route path="requirements/new" element={<Placeholder />} />
            <Route path="requirements/:id" element={<RequirementDetail />} />
            <Route path="requirements/:id/edit" element={<Placeholder />} />

            {/* Suppliers */}
            <Route path="suppliers" element={<Suppliers />} />

            {/* Compliance */}
            <Route path="compliance" element={<Compliance />} />

            {/* Costing */}
            <Route path="costing" element={<Costing />} />

            {/* Bulletins */}
            <Route path="bulletins" element={<Bulletins />} />
            <Route path="bulletins/:id" element={<BulletinDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
