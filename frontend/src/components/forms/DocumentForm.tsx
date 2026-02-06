import { useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi } from '../../lib/api';
import { FormField, TextInput, SelectInput } from './index';

interface Document {
  id?: string;
  document_number: string;
  revision: string;
  title: string;
  description: string | null;
  document_type: string;
  category: string | null;
  discipline: string | null;
  project_id: string | null;
}

interface DocumentFormProps {
  document?: Document;
  onSuccess: () => void;
}

const defaultDocument: Omit<Document, 'id'> = {
  document_number: '',
  revision: 'A',
  title: '',
  description: null,
  document_type: 'specification',
  category: null,
  discipline: null,
  project_id: null,
};

const documentTypeOptions = [
  { value: 'specification', label: 'Specification' },
  { value: 'drawing', label: 'Drawing' },
  { value: 'model_3d', label: '3D Model' },
  { value: 'manual', label: 'Manual' },
  { value: 'report', label: 'Report' },
  { value: 'procedure', label: 'Procedure' },
  { value: 'submittal', label: 'Submittal' },
];

const disciplineOptions = [
  { value: 'mechanical', label: 'Mechanical' },
  { value: 'electrical', label: 'Electrical' },
  { value: 'structural', label: 'Structural' },
  { value: 'civil', label: 'Civil' },
  { value: 'architectural', label: 'Architectural' },
  { value: 'plumbing', label: 'Plumbing' },
];

export function DocumentForm({ document, onSuccess }: DocumentFormProps) {
  const [formData, setFormData] = useState<Omit<Document, 'id'>>({
    ...defaultDocument,
    ...document,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const queryClient = useQueryClient();
  const isEdit = !!document?.id;

  const createMutation = useMutation({
    mutationFn: (data: Omit<Document, 'id'>) => documentsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      onSuccess();
    },
    onError: (err: Error) => {
      setErrors({ submit: err.message });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Document>) => documentsApi.update(document!.id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document', document!.id] });
      onSuccess();
    },
    onError: (err: Error) => {
      setErrors({ submit: err.message });
    },
  });

  const handleChange = (field: keyof Document, value: string | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!formData.document_number.trim()) {
      newErrors.document_number = 'Document number is required';
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
        <h2 className="text-lg font-semibold text-gray-900">Document Information</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField label="Document Number" name="document_number" required error={errors.document_number}>
            <TextInput
              id="document_number"
              value={formData.document_number}
              onChange={(e) => handleChange('document_number', e.target.value)}
              disabled={isEdit}
              error={!!errors.document_number}
              placeholder="e.g., DOC-001"
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

          <FormField label="Title" name="title" required error={errors.title}>
            <TextInput
              id="title"
              value={formData.title}
              onChange={(e) => handleChange('title', e.target.value)}
              error={!!errors.title}
              placeholder="Document title"
            />
          </FormField>

          <FormField label="Document Type" name="document_type" required>
            <SelectInput
              id="document_type"
              value={formData.document_type}
              onChange={(e) => handleChange('document_type', e.target.value)}
              options={documentTypeOptions}
            />
          </FormField>

          <FormField label="Category" name="category">
            <TextInput
              id="category"
              value={formData.category || ''}
              onChange={(e) => handleChange('category', e.target.value || null)}
              placeholder="e.g., Technical"
            />
          </FormField>

          <FormField label="Discipline" name="discipline">
            <SelectInput
              id="discipline"
              value={formData.discipline || ''}
              onChange={(e) => handleChange('discipline', e.target.value || null)}
              options={disciplineOptions}
              placeholder="Select discipline"
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
          {isPending ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Document'}
        </button>
      </div>
    </form>
  );
}
