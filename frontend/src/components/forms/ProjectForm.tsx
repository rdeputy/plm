import { useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '../../lib/api';
import { FormField, TextInput, SelectInput } from './index';

interface Project {
  id?: string;
  project_number: string;
  name: string;
  description: string | null;
  project_type: string | null;
  customer_name: string | null;
  project_manager_name: string | null;
  start_date: string | null;
  target_end_date: string | null;
  budget: number;
  currency: string;
}

interface ProjectFormProps {
  project?: Project;
  onSuccess: () => void;
}

const defaultProject: Omit<Project, 'id'> = {
  project_number: '',
  name: '',
  description: null,
  project_type: null,
  customer_name: null,
  project_manager_name: null,
  start_date: null,
  target_end_date: null,
  budget: 0,
  currency: 'USD',
};

const projectTypeOptions = [
  { value: 'new_product', label: 'New Product Development' },
  { value: 'enhancement', label: 'Product Enhancement' },
  { value: 'cost_reduction', label: 'Cost Reduction' },
  { value: 'compliance', label: 'Compliance/Regulatory' },
  { value: 'maintenance', label: 'Maintenance' },
];

const currencyOptions = [
  { value: 'USD', label: 'USD' },
  { value: 'EUR', label: 'EUR' },
  { value: 'GBP', label: 'GBP' },
  { value: 'CAD', label: 'CAD' },
];

export function ProjectForm({ project, onSuccess }: ProjectFormProps) {
  const [formData, setFormData] = useState<Omit<Project, 'id'>>({
    ...defaultProject,
    ...project,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const queryClient = useQueryClient();
  const isEdit = !!project?.id;

  const createMutation = useMutation({
    mutationFn: (data: Omit<Project, 'id'>) => projectsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      onSuccess();
    },
    onError: (err: Error) => {
      setErrors({ submit: err.message });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Project>) => projectsApi.update(project!.id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['project', project!.id] });
      onSuccess();
    },
    onError: (err: Error) => {
      setErrors({ submit: err.message });
    },
  });

  const handleChange = (field: keyof Project, value: string | number | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!formData.project_number.trim()) {
      newErrors.project_number = 'Project number is required';
    }
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    if (isEdit) {
      updateMutation.mutate(formData);
    } else {
      createMutation.mutate(formData);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {errors.submit && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {errors.submit}
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        <h2 className="text-lg font-semibold text-gray-900">Project Information</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField label="Project Number" name="project_number" required error={errors.project_number}>
            <TextInput
              id="project_number"
              value={formData.project_number}
              onChange={(e) => handleChange('project_number', e.target.value)}
              disabled={isEdit}
              error={!!errors.project_number}
              placeholder="e.g., PRJ-001"
            />
          </FormField>

          <FormField label="Name" name="name" required error={errors.name}>
            <TextInput
              id="name"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              error={!!errors.name}
              placeholder="Project name"
            />
          </FormField>

          <FormField label="Project Type" name="project_type">
            <SelectInput
              id="project_type"
              value={formData.project_type || ''}
              onChange={(e) => handleChange('project_type', e.target.value || null)}
              options={projectTypeOptions}
              placeholder="Select type"
            />
          </FormField>

          <FormField label="Customer" name="customer_name">
            <TextInput
              id="customer_name"
              value={formData.customer_name || ''}
              onChange={(e) => handleChange('customer_name', e.target.value || null)}
              placeholder="Customer name"
            />
          </FormField>

          <FormField label="Project Manager" name="project_manager_name">
            <TextInput
              id="project_manager_name"
              value={formData.project_manager_name || ''}
              onChange={(e) => handleChange('project_manager_name', e.target.value || null)}
              placeholder="Manager name"
            />
          </FormField>
        </div>

        <FormField label="Description" name="description">
          <TextInput
            id="description"
            rows={3}
            value={formData.description || ''}
            onChange={(e) => handleChange('description', e.target.value || null)}
            placeholder="Project description"
          />
        </FormField>
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        <h2 className="text-lg font-semibold text-gray-900">Schedule & Budget</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField label="Start Date" name="start_date">
            <TextInput
              id="start_date"
              type="date"
              value={formData.start_date || ''}
              onChange={(e) => handleChange('start_date', e.target.value || null)}
            />
          </FormField>

          <FormField label="Target End Date" name="target_end_date">
            <TextInput
              id="target_end_date"
              type="date"
              value={formData.target_end_date || ''}
              onChange={(e) => handleChange('target_end_date', e.target.value || null)}
            />
          </FormField>

          <FormField label="Budget" name="budget">
            <TextInput
              id="budget"
              type="number"
              step="0.01"
              min="0"
              value={formData.budget}
              onChange={(e) =>
                handleChange('budget', e.target.value ? parseFloat(e.target.value) : 0)
              }
              placeholder="0.00"
            />
          </FormField>

          <FormField label="Currency" name="currency" required>
            <SelectInput
              id="currency"
              value={formData.currency}
              onChange={(e) => handleChange('currency', e.target.value)}
              options={currencyOptions}
            />
          </FormField>
        </div>
      </div>

      <div className="flex justify-end gap-4">
        <button
          type="button"
          onClick={() => window.history.back()}
          className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {isPending ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Project'}
        </button>
      </div>
    </form>
  );
}
