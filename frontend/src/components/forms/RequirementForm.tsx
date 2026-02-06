import { useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { requirementsApi } from '../../lib/api';
import { FormField, TextInput, SelectInput } from './index';

interface Requirement {
  id?: string;
  requirement_number: string;
  title: string;
  description: string | null;
  requirement_type: string;
  priority: string;
  verification_method: string;
  source: string | null;
  parent_id: string | null;
  project_id: string | null;
}

interface RequirementFormProps {
  requirement?: Requirement;
  onSuccess: () => void;
}

const defaultRequirement: Omit<Requirement, 'id'> = {
  requirement_number: '',
  title: '',
  description: null,
  requirement_type: 'functional',
  priority: 'must_have',
  verification_method: 'test',
  source: null,
  parent_id: null,
  project_id: null,
};

const requirementTypeOptions = [
  { value: 'functional', label: 'Functional' },
  { value: 'performance', label: 'Performance' },
  { value: 'interface', label: 'Interface' },
  { value: 'environmental', label: 'Environmental' },
  { value: 'safety', label: 'Safety' },
  { value: 'regulatory', label: 'Regulatory' },
];

const priorityOptions = [
  { value: 'must_have', label: 'Must Have' },
  { value: 'should_have', label: 'Should Have' },
  { value: 'could_have', label: 'Could Have' },
  { value: 'wont_have', label: "Won't Have" },
];

const verificationMethodOptions = [
  { value: 'test', label: 'Test' },
  { value: 'analysis', label: 'Analysis' },
  { value: 'inspection', label: 'Inspection' },
  { value: 'demonstration', label: 'Demonstration' },
];

export function RequirementForm({ requirement, onSuccess }: RequirementFormProps) {
  const [formData, setFormData] = useState<Omit<Requirement, 'id'>>({
    ...defaultRequirement,
    ...requirement,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const queryClient = useQueryClient();
  const isEdit = !!requirement?.id;

  const createMutation = useMutation({
    mutationFn: (data: Omit<Requirement, 'id'>) => requirementsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirements'] });
      onSuccess();
    },
    onError: (err: Error) => {
      setErrors({ submit: err.message });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Requirement>) => requirementsApi.update(requirement!.id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requirements'] });
      queryClient.invalidateQueries({ queryKey: ['requirement', requirement!.id] });
      onSuccess();
    },
    onError: (err: Error) => {
      setErrors({ submit: err.message });
    },
  });

  const handleChange = (field: keyof Requirement, value: string | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!formData.requirement_number.trim()) {
      newErrors.requirement_number = 'Requirement number is required';
    }
    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
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
        <h2 className="text-lg font-semibold text-gray-900">Requirement Information</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField label="Requirement Number" name="requirement_number" required error={errors.requirement_number}>
            <TextInput
              id="requirement_number"
              value={formData.requirement_number}
              onChange={(e) => handleChange('requirement_number', e.target.value)}
              disabled={isEdit}
              error={!!errors.requirement_number}
              placeholder="e.g., REQ-001"
            />
          </FormField>

          <FormField label="Type" name="requirement_type" required>
            <SelectInput
              id="requirement_type"
              value={formData.requirement_type}
              onChange={(e) => handleChange('requirement_type', e.target.value)}
              options={requirementTypeOptions}
            />
          </FormField>

          <FormField label="Title" name="title" required error={errors.title}>
            <TextInput
              id="title"
              value={formData.title}
              onChange={(e) => handleChange('title', e.target.value)}
              error={!!errors.title}
              placeholder="Requirement title"
            />
          </FormField>

          <FormField label="Priority" name="priority" required>
            <SelectInput
              id="priority"
              value={formData.priority}
              onChange={(e) => handleChange('priority', e.target.value)}
              options={priorityOptions}
            />
          </FormField>

          <FormField label="Verification Method" name="verification_method" required>
            <SelectInput
              id="verification_method"
              value={formData.verification_method}
              onChange={(e) => handleChange('verification_method', e.target.value)}
              options={verificationMethodOptions}
            />
          </FormField>

          <FormField label="Source" name="source">
            <TextInput
              id="source"
              value={formData.source || ''}
              onChange={(e) => handleChange('source', e.target.value || null)}
              placeholder="e.g., Customer Spec, Standard"
            />
          </FormField>

          <FormField label="Parent Requirement ID" name="parent_id">
            <TextInput
              id="parent_id"
              value={formData.parent_id || ''}
              onChange={(e) => handleChange('parent_id', e.target.value || null)}
              placeholder="For derived requirements"
            />
          </FormField>

          <FormField label="Project ID" name="project_id">
            <TextInput
              id="project_id"
              value={formData.project_id || ''}
              onChange={(e) => handleChange('project_id', e.target.value || null)}
              placeholder="Optional project ID"
            />
          </FormField>
        </div>

        <FormField label="Description" name="description">
          <TextInput
            id="description"
            rows={4}
            value={formData.description || ''}
            onChange={(e) => handleChange('description', e.target.value || null)}
            placeholder="Detailed requirement description"
          />
        </FormField>
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
          {isPending ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Requirement'}
        </button>
      </div>
    </form>
  );
}
