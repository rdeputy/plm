import { useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { partsApi } from '../../lib/api';
import { FormField, TextInput, SelectInput } from './index';

interface Part {
  id?: string;
  part_number: string;
  revision: string;
  name: string;
  description: string | null;
  part_type: string;
  category: string | null;
  csi_code: string | null;
  uniformat_code: string | null;
  unit_of_measure: string;
  unit_cost: number | null;
  manufacturer: string | null;
  manufacturer_pn: string | null;
  lead_time_days: number | null;
}

interface PartFormProps {
  part?: Part;
  onSuccess: () => void;
}

const defaultPart: Omit<Part, 'id'> = {
  part_number: '',
  revision: 'A',
  name: '',
  description: null,
  part_type: 'component',
  category: null,
  csi_code: null,
  uniformat_code: null,
  unit_of_measure: 'EA',
  unit_cost: null,
  manufacturer: null,
  manufacturer_pn: null,
  lead_time_days: null,
};

const partTypeOptions = [
  { value: 'component', label: 'Component' },
  { value: 'assembly', label: 'Assembly' },
  { value: 'raw_material', label: 'Raw Material' },
  { value: 'consumable', label: 'Consumable' },
  { value: 'tool', label: 'Tool' },
];

const uomOptions = [
  { value: 'EA', label: 'Each (EA)' },
  { value: 'LF', label: 'Linear Feet (LF)' },
  { value: 'SF', label: 'Square Feet (SF)' },
  { value: 'CY', label: 'Cubic Yards (CY)' },
  { value: 'LB', label: 'Pounds (LB)' },
  { value: 'GAL', label: 'Gallons (GAL)' },
];

export function PartForm({ part, onSuccess }: PartFormProps) {
  const [formData, setFormData] = useState<Omit<Part, 'id'>>({
    ...defaultPart,
    ...part,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const queryClient = useQueryClient();
  const isEdit = !!part?.id;

  const createMutation = useMutation({
    mutationFn: (data: Omit<Part, 'id'>) => partsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['parts'] });
      onSuccess();
    },
    onError: (err: Error) => {
      setErrors({ submit: err.message });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Part>) => partsApi.update(part!.id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['parts'] });
      queryClient.invalidateQueries({ queryKey: ['part', part!.id] });
      onSuccess();
    },
    onError: (err: Error) => {
      setErrors({ submit: err.message });
    },
  });

  const handleChange = (field: keyof Part, value: string | number | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!formData.part_number.trim()) {
      newErrors.part_number = 'Part number is required';
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
        <h2 className="text-lg font-semibold text-gray-900">General Information</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField label="Part Number" name="part_number" required error={errors.part_number}>
            <TextInput
              id="part_number"
              value={formData.part_number}
              onChange={(e) => handleChange('part_number', e.target.value)}
              disabled={isEdit}
              error={!!errors.part_number}
              placeholder="e.g., PN-001"
            />
          </FormField>

          <FormField label="Revision" name="revision" required>
            <TextInput
              id="revision"
              value={formData.revision}
              onChange={(e) => handleChange('revision', e.target.value)}
              disabled={isEdit}
              placeholder="e.g., A"
            />
          </FormField>

          <FormField label="Name" name="name" required error={errors.name}>
            <TextInput
              id="name"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              error={!!errors.name}
              placeholder="Part name"
            />
          </FormField>

          <FormField label="Type" name="part_type" required>
            <SelectInput
              id="part_type"
              value={formData.part_type}
              onChange={(e) => handleChange('part_type', e.target.value)}
              options={partTypeOptions}
            />
          </FormField>

          <FormField label="Category" name="category">
            <TextInput
              id="category"
              value={formData.category || ''}
              onChange={(e) => handleChange('category', e.target.value || null)}
              placeholder="e.g., Electrical"
            />
          </FormField>

          <FormField label="Unit of Measure" name="unit_of_measure" required>
            <SelectInput
              id="unit_of_measure"
              value={formData.unit_of_measure}
              onChange={(e) => handleChange('unit_of_measure', e.target.value)}
              options={uomOptions}
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
        <h2 className="text-lg font-semibold text-gray-900">Classification</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField label="CSI Code" name="csi_code">
            <TextInput
              id="csi_code"
              value={formData.csi_code || ''}
              onChange={(e) => handleChange('csi_code', e.target.value || null)}
              placeholder="e.g., 26 05 00"
            />
          </FormField>

          <FormField label="Uniformat Code" name="uniformat_code">
            <TextInput
              id="uniformat_code"
              value={formData.uniformat_code || ''}
              onChange={(e) => handleChange('uniformat_code', e.target.value || null)}
              placeholder="e.g., D5010"
            />
          </FormField>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        <h2 className="text-lg font-semibold text-gray-900">Cost & Procurement</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField label="Unit Cost" name="unit_cost">
            <TextInput
              id="unit_cost"
              type="number"
              step="0.01"
              min="0"
              value={formData.unit_cost ?? ''}
              onChange={(e) =>
                handleChange('unit_cost', e.target.value ? parseFloat(e.target.value) : null)
              }
              placeholder="0.00"
            />
          </FormField>

          <FormField label="Lead Time (days)" name="lead_time_days">
            <TextInput
              id="lead_time_days"
              type="number"
              min="0"
              value={formData.lead_time_days ?? ''}
              onChange={(e) =>
                handleChange('lead_time_days', e.target.value ? parseInt(e.target.value) : null)
              }
              placeholder="0"
            />
          </FormField>

          <FormField label="Manufacturer" name="manufacturer">
            <TextInput
              id="manufacturer"
              value={formData.manufacturer || ''}
              onChange={(e) => handleChange('manufacturer', e.target.value || null)}
              placeholder="Manufacturer name"
            />
          </FormField>

          <FormField label="Manufacturer Part Number" name="manufacturer_pn">
            <TextInput
              id="manufacturer_pn"
              value={formData.manufacturer_pn || ''}
              onChange={(e) => handleChange('manufacturer_pn', e.target.value || null)}
              placeholder="Manufacturer's part number"
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
          {isPending ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Part'}
        </button>
      </div>
    </form>
  );
}
