import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react';

type TextInputProps = (
  | ({ rows?: undefined } & InputHTMLAttributes<HTMLInputElement>)
  | ({ rows: number } & TextareaHTMLAttributes<HTMLTextAreaElement>)
) & {
  error?: boolean;
};

export function TextInput({ rows, error, className = '', ...props }: TextInputProps) {
  const baseClasses = `w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
    error ? 'border-red-500' : 'border-gray-300'
  } ${className}`;

  if (rows !== undefined) {
    return (
      <textarea
        rows={rows}
        className={baseClasses}
        {...(props as TextareaHTMLAttributes<HTMLTextAreaElement>)}
      />
    );
  }

  return (
    <input
      className={baseClasses}
      {...(props as InputHTMLAttributes<HTMLInputElement>)}
    />
  );
}
