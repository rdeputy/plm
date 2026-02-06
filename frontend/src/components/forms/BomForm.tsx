import { useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { bomsApi } from '../../lib/api';
import { FormField, TextInput, SelectInput } from './index';

interface Bom {
  id?: string;
  bom_number: string;
  name: string;
  parent_part_id: string;
  description: string | null;
  bom_type: string;
  effectivity: string;
  effective_from: string | null;
  effective_to: string | null;
  project_id: string | null;
}

interface BomFormProps {
  bom?: Bom;
  onSuccess: () => void;
}

const defaultBom: Omit<Bom, 'id'> = {
  bom_number: '',
  name: '',
  parent_part_id: '',
  description: null,
  bom_type: 'engineering',
  effectivity: 'as_designed',
  effective_from: null,
  effective_to: null,
  project_id: null,
};

const bomTypeOptions = [
  { value: 'engineering', label: 'Engineering' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'service', label: 'Service' },
  { value: 'sales', label: 'Sales' },
];

const effectivityOptions = [
  { value: 'as_designed', label: 'As Designed' },
  { value: 'as_approved', label: 'As Approved' },
  { value: 'as_built', label: 'As Built' },
  { value: 'as_maintained', label: 'As Maintained' },
];

export function BomForm({ bom, onSuccess }: BomFormProps) {
  const [formData, setFormData] = useState<Omit<Bom, 'id'>>({
    ...defaultBom,
    ...bom,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const queryClient = useQueryClient();
  const isEdit = !!bom?.id;

  const createMutation = useMutation({
    mutationFn: (data: Omit<Bom, 'id'>) => bomsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['boms'] });
      onSuccess();
    },
    onError: (err: Error) => {
      setErrors({ submit: err.message });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Bom>) => bomsApi.update(bom!.id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['boms'] });
      queryClient.invalidateQueries({ queryKey: ['bom', bom!.id] });
      onSuccess();
    },
    onError: (err: Error) => {
      setErrors({ submit: err.message });
    },
  });

  const handleChange = (field: keyof Bom, value: string | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!formData.bom_number.trim()) {
      newErrors.bom_number = 'BOM number is required';
    }
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }
    if (!formData.parent_part_id.trim()) {
      newErrors.parent_part_id = 'Parent part ID is required';
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
        <h2 className="text-lg font-semibold text-gray-900">General Information</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField label="BOM Number" name="bom_number" required error={errors.bom_number}>
            <TextInput
              id="bom_number"
              value={formData.bom_number}
              onChange={(e) => handleChange('bom_number', e.target.value)}
              disabled={isEdit}
              error={!!errors.bom_number}
              placeholder="e.g., BOM-001"
            />
          </FormField>

          <FormField label="Name" name="name" required error={errors.name}>
            <TextInput
              id="name"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              error={!!errors.name}
              placeholder="BOM name"
            />
          </FormField>

          <FormField label="Parent Part ID" name="parent_part_id" required error={errors.parent_part_id}>
            <TextInput
              id="parent_part_id"
              value={formData.parent_part_id}
              onChange={(e) => handleChange('parent_part_id', e.target.value)}
              disabled={isEdit}
              error={!!errors.parent_part_id}
              placeholder="Part ID"
            />
          </FormField>

          <FormField label="BOM Type" name="bom_type" required>
            <SelectInput
              id="bom_type"
              value={formData.bom_type}
              onChange={(e) => handleChange('bom_type', e.target.value)}
              options={bomTypeOptions}
            />
          </FormField>

          <FormField label="Effectivity" name="effectivity" required>
            <SelectInput
              id="effectivity"
              value={formData.effectivity}
              onChange={(e) => handleChange('effectivity', e.target.value)}
              options={effectivityOptions}
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
            rows={3}
            value={formData.description || ''}
            onChange={(e) => handleChange('description', e.target.value || null)}
            placeholder="Optional description"
          />
        </FormField>
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        <h2 className="text-lg font-semibold text-gray-900">Effectivity Dates</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField label="Effective From" name="effective_from">
            <TextInput
              id="effective_from"
              type="date"
              value={formData.effective_from || ''}
              onChange={(e) => handleChange('effective_from', e.target.value || null)}
            />
          </FormField>

          <FormField label="Effective To" name="effective_to">
            <TextInput
              id="effective_to"
              type="date"
              value={formData.effective_to || ''}
              onChange={(e) => handleChange('effective_to', e.target.value || null)}
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
          {isPending ? 'Saving...' : isEdit ? 'Save Changes' : 'Create BOM'}
        </button>
      </div>
    </form>
  );
}
