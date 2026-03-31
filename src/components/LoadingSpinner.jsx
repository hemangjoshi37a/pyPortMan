import React from 'react';

/**
 * LoadingSpinner component
 * Displays a loading spinner with optional text
 */
export default function LoadingSpinner({ size = 'medium', text = 'Loading...' }) {
  const sizeClasses = {
    small: 'w-4 h-4',
    medium: 'w-8 h-8',
    large: 'w-12 h-12',
  };

  return (
    <div className="flex flex-col items-center justify-center gap-2">
      <div
        className={`animate-spin rounded-full border-2 border-gray-600 border-t-blue-500 ${sizeClasses[size]}`}
      />
      {text && <span className="text-gray-400 text-sm">{text}</span>}
    </div>
  );
}
