import { useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { changesApi } from '../../lib/api';
import { FormField, TextInput, SelectInput } from './index';

interface Change {
  id?: string;
  eco_number: string;
  title: string;
  description: string | null;
  reason: string;
  urgency: string;
  project_id: string | null;
}

interface ChangeFormProps {
  change?: Change;
  onSuccess: () => void;
}

const defaultChange: Omit<Change, 'id'> = {
  eco_number: '',
  title: '',
  description: null,
  reason: '',
  urgency: 'normal',
  project_id: null,
};

const urgencyOptions = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'normal', label: 'Normal' },
  { value: 'low', label: 'Low' },
];

const reasonOptions = [
  { value: 'cost_reduction', label: 'Cost Reduction' },
  { value: 'quality_improvement', label: 'Quality Improvement' },
  { value: 'design_correction', label: 'Design Correction' },
  { value: 'regulatory', label: 'Regulatory Compliance' },
  { value: 'customer_request', label: 'Customer Request' },
  { value: 'supplier_change', label: 'Supplier Change' },
];

export function ChangeForm({ change, onSuccess }: ChangeFormProps) {
  const [formData, setFormData] = useState<Omit<Change, 'id'>>({
    ...defaultChange,
    ...change,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const queryClient = useQueryClient();
  const isEdit = !!change?.id;

  const createMutation = useMutation({
    mutationFn: (data: Omit<Change, 'id'>) => changesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['changes'] });
      onSuccess();
    },
    onError: (err: Error) => {
      setErrors({ submit: err.message });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Change>) => changesApi.update(change!.id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['changes'] });
      queryClient.invalidateQueries({ queryKey: ['change', change!.id] });
      onSuccess();
    },
    onError: (err: Error) => {
      setErrors({ submit: err.message });
    },
  });

  const handleChange = (field: keyof Change, value: string | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!formData.eco_number.trim()) {
      newErrors.eco_number = 'ECO number is required';
    }
    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }
    if (!formData.reason.trim()) {
      newErrors.reason = 'Reason is required';
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
        <h2 className="text-lg font-semibold text-gray-900">Change Request Information</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField label="ECO Number" name="eco_number" required error={errors.eco_number}>
            <TextInput
              id="eco_number"
              value={formData.eco_number}
              onChange={(e) => handleChange('eco_number', e.target.value)}
              disabled={isEdit}
              error={!!errors.eco_number}
              placeholder="e.g., ECO-001"
            />
          </FormField>

          <FormField label="Urgency" name="urgency" required>
            <SelectInput
              id="urgency"
              value={formData.urgency}
              onChange={(e) => handleChange('urgency', e.target.value)}
              options={urgencyOptions}
            />
          </FormField>

          <FormField label="Title" name="title" required error={errors.title}>
            <TextInput
              id="title"
              value={formData.title}
              onChange={(e) => handleChange('title', e.target.value)}
              error={!!errors.title}
              placeholder="Change title"
            />
          </FormField>

          <FormField label="Reason" name="reason" required error={errors.reason}>
            <SelectInput
              id="reason"
              value={formData.reason}
              onChange={(e) => handleChange('reason', e.target.value)}
              options={reasonOptions}
              error={!!errors.reason}
              placeholder="Select reason"
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
            placeholder="Detailed description of the change"
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
          {isPending ? 'Saving...' : isEdit ? 'Save Changes' : 'Create ECO'}
        </button>
      </div>
    </form>
  );
}
