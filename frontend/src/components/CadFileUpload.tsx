import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, FileType, FileText, File } from 'lucide-react';
import { api } from '../lib/api';

interface CadFileUploadProps {
  partId: string;
  currentFiles?: {
    model_file?: string | null;
    drawing_file?: string | null;
    spec_file?: string | null;
  };
  disabled?: boolean;
}

type FileType = 'model' | 'drawing' | 'spec';

const FILE_TYPE_CONFIG = {
  model: {
    label: '3D Model',
    icon: FileType,
    accept: '.3dm,.skp,.rvt,.ifc,.dwg,.dxf,.step,.stp,.iges,.igs',
    description: 'Upload 3D model file',
  },
  drawing: {
    label: '2D Drawing',
    icon: FileText,
    accept: '.pdf,.dwg,.dxf',
    description: 'Upload 2D drawing file',
  },
  spec: {
    label: 'Specification',
    icon: File,
    accept: '.pdf,.doc,.docx,.txt',
    description: 'Upload specification document',
  },
};

export function CadFileUpload({ partId, currentFiles, disabled }: CadFileUploadProps) {
  const [uploading, setUploading] = useState<FileType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async ({ file, fileType }: { file: File; fileType: FileType }) => {
      const formData = new FormData();
      formData.append('file', file);

      return api.post(`/parts/${partId}/upload-cad`, formData, {
        params: { file_type: fileType, user_id: 'current-user' },
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['part', partId] });
      setError(null);
    },
    onError: (err: Error) => {
      setError(err.message || 'Upload failed');
    },
    onSettled: () => {
      setUploading(null);
    },
  });

  const handleFileSelect = (fileType: FileType, event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(fileType);
    setError(null);
    uploadMutation.mutate({ file, fileType });

    // Reset input
    event.target.value = '';
  };

  const getFileName = (path?: string | null) => {
    if (!path) return null;
    return path.split('/').pop() || path;
  };

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-lg font-medium text-gray-900 mb-4">CAD Files</h3>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
          {error}
        </div>
      )}

      <div className="space-y-4">
        {(Object.entries(FILE_TYPE_CONFIG) as [FileType, typeof FILE_TYPE_CONFIG.model][]).map(
          ([fileType, config]) => {
            const currentPath = currentFiles?.[`${fileType}_file` as keyof typeof currentFiles];
            const currentFileName = getFileName(currentPath);
            const isUploading = uploading === fileType;
            const Icon = config.icon;

            return (
              <div
                key={fileType}
                className="flex items-center justify-between p-3 border rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{config.label}</p>
                    {currentFileName ? (
                      <p className="text-xs text-green-600">{currentFileName}</p>
                    ) : (
                      <p className="text-xs text-gray-500">No file uploaded</p>
                    )}
                  </div>
                </div>

                <label
                  className={`
                    inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium
                    ${disabled || isUploading
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-blue-50 text-blue-700 hover:bg-blue-100 cursor-pointer'
                    }
                  `}
                >
                  {isUploading ? (
                    <>
                      <span className="animate-spin">...</span>
                      Uploading
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4" />
                      {currentFileName ? 'Replace' : 'Upload'}
                    </>
                  )}
                  <input
                    type="file"
                    accept={config.accept}
                    onChange={(e) => handleFileSelect(fileType, e)}
                    disabled={disabled || isUploading}
                    className="sr-only"
                  />
                </label>
              </div>
            );
          }
        )}
      </div>

      <p className="mt-4 text-xs text-gray-500">
        Supported formats: 3D (.3dm, .skp, .rvt, .ifc, .dwg, .dxf, .step, .iges) |
        2D (.pdf, .dwg, .dxf) | Spec (.pdf, .doc, .docx)
      </p>
    </div>
  );
}
