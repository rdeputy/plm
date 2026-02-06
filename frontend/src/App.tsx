import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Parts } from './pages/Parts';
import { PartDetail } from './pages/PartDetail';
import { PartFormPage } from './pages/PartFormPage';
import { Projects } from './pages/Projects';
import { ProjectDetail } from './pages/ProjectDetail';
import { ProjectFormPage } from './pages/ProjectFormPage';
import { Boms } from './pages/Boms';
import { BomDetail } from './pages/BomDetail';
import { BomFormPage } from './pages/BomFormPage';
import { Documents } from './pages/Documents';
import { DocumentDetail } from './pages/DocumentDetail';
import { DocumentFormPage } from './pages/DocumentFormPage';
import { Changes } from './pages/Changes';
import { ChangeDetail } from './pages/ChangeDetail';
import { ChangeFormPage } from './pages/ChangeFormPage';
import { Requirements } from './pages/Requirements';
import { RequirementDetail } from './pages/RequirementDetail';
import { RequirementFormPage } from './pages/RequirementFormPage';
import { Suppliers } from './pages/Suppliers';
import { Compliance } from './pages/Compliance';
import { Costing } from './pages/Costing';
import { Bulletins } from './pages/Bulletins';
import { BulletinDetail } from './pages/BulletinDetail';

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
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />

            {/* Parts */}
            <Route path="parts" element={<Parts />} />
            <Route path="parts/new" element={<PartFormPage />} />
            <Route path="parts/:id" element={<PartDetail />} />
            <Route path="parts/:id/edit" element={<PartFormPage />} />

            {/* BOMs */}
            <Route path="boms" element={<Boms />} />
            <Route path="boms/new" element={<BomFormPage />} />
            <Route path="boms/:id" element={<BomDetail />} />
            <Route path="boms/:id/edit" element={<BomFormPage />} />

            {/* Documents */}
            <Route path="documents" element={<Documents />} />
            <Route path="documents/new" element={<DocumentFormPage />} />
            <Route path="documents/:id" element={<DocumentDetail />} />
            <Route path="documents/:id/edit" element={<DocumentFormPage />} />

            {/* Changes (ECOs) */}
            <Route path="changes" element={<Changes />} />
            <Route path="changes/new" element={<ChangeFormPage />} />
            <Route path="changes/:id" element={<ChangeDetail />} />
            <Route path="changes/:id/edit" element={<ChangeFormPage />} />

            {/* Projects */}
            <Route path="projects" element={<Projects />} />
            <Route path="projects/new" element={<ProjectFormPage />} />
            <Route path="projects/:id" element={<ProjectDetail />} />
            <Route path="projects/:id/edit" element={<ProjectFormPage />} />

            {/* Requirements */}
            <Route path="requirements" element={<Requirements />} />
            <Route path="requirements/new" element={<RequirementFormPage />} />
            <Route path="requirements/:id" element={<RequirementDetail />} />
            <Route path="requirements/:id/edit" element={<RequirementFormPage />} />

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
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
