/**
 * Utility functions for handling exports and downloads
 */

export const downloadFile = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const getFileExtension = (filename: string): string => {
  return filename.split('.').pop() || '';
};

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export const generateFilename = (productName: string, type: string, extension: string): string => {
  const sanitizedName = productName.replace(/[^a-z0-9]/gi, '_').toLowerCase();
  const timestamp = new Date().toISOString().slice(0, 10);
  return `${type}_${sanitizedName}_${timestamp}.${extension}`;
};

export const validateExportData = (data: any): boolean => {
  return data && typeof data === 'object' && !Array.isArray(data);
};

export const createExportNotification = (filename: string, type: string): string => {
  return `${type} exported successfully as ${filename}`;
};
