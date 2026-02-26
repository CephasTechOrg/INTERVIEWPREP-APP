import axios, { AxiosInstance, AxiosError } from 'axios';
import { ErrorResponse } from '@/types/api';
import { useAuthStore } from '@/lib/stores/authStore';

const DEFAULT_API_URL = 'https://interviq-backend.onrender.com/api/v1';

// Use a function to get the URL to handle SSR properly
const getBaseURL = () => {
  const envUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE;
  if (envUrl) return envUrl;

  if (typeof window !== 'undefined') {
    const host = window.location.hostname || '';
    if (host.endsWith('onrender.com')) {
      return DEFAULT_API_URL;
    }
  }

  return 'http://127.0.0.1:8000/api/v1';
};

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: getBaseURL(),
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000, // 30 second timeout
    });

    // Attach token to requests
    this.client.interceptors.request.use((config) => {
      if (typeof window !== 'undefined') {
        const token = useAuthStore.getState().token;
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
      return config;
    });

    // Handle errors globally
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        // Only redirect on 401 if NOT on login-related endpoints
        const isAuthEndpoint = error.config?.url?.includes('/auth/');
        if (error.response?.status === 401 && typeof window !== 'undefined' && !isAuthEndpoint) {
          const path = window.location.pathname || '';
          const isAuthRoute =
            path.startsWith('/login') ||
            path.startsWith('/signup') ||
            path.startsWith('/verify') ||
            path.startsWith('/forgot-password') ||
            path.startsWith('/reset-password');

          // Clear auth state centrally to avoid login/logout loops.
          try {
            useAuthStore.getState().logout();
          } catch {
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
          }

          if (!isAuthRoute) {
            window.location.href = '/login';
          }
        }
        // Return rejected promise with error (don't throw here, let caller handle)
        return Promise.reject(error);
      }
    );
  }

  private parseError(error: AxiosError): ErrorResponse {
    if (error.response) {
      const data = error.response.data as any;
      let message = 'An error occurred';
      
      if (typeof data.detail === 'string') {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        message = data.detail.map((d: any) => d.msg).join(', ');
      } else if (data.message) {
        message = data.message;
      }
      
      return {
        message,
        status: error.response.status,
        details: data,
      };
    }
    
    if (error.request) {
      const baseUrl = getBaseURL();
      return {
        message: `Network error: Unable to reach the server. Make sure the backend is running on ${baseUrl}`,
        status: 0,
      };
    }
    
    return {
      message: error.message || 'An unexpected error occurred',
      status: 0,
    };
  }

  private toError(error: AxiosError): Error & ErrorResponse {
    const parsed = this.parseError(error);
    const err = new Error(parsed.message) as Error & ErrorResponse;
    err.status = parsed.status;
    err.details = parsed.details;
    return err;
  }

  async get<T>(url: string): Promise<T> {
    try {
      const response = await this.client.get<T>(url);
      return response.data;
    } catch (error) {
      throw this.toError(error as AxiosError);
    }
  }

  async post<T>(url: string, data?: any): Promise<T> {
    try {
      const response = await this.client.post<T>(url, data);
      return response.data;
    } catch (error) {
      throw this.toError(error as AxiosError);
    }
  }

  async put<T>(url: string, data?: any): Promise<T> {
    try {
      const response = await this.client.put<T>(url, data);
      return response.data;
    } catch (error) {
      throw this.toError(error as AxiosError);
    }
  }

  async patch<T>(url: string, data?: any): Promise<T> {
    try {
      const response = await this.client.patch<T>(url, data);
      return response.data;
    } catch (error) {
      throw this.toError(error as AxiosError);
    }
  }

  async delete<T>(url: string): Promise<T> {
    try {
      const response = await this.client.delete<T>(url);
      return response.data;
    } catch (error) {
      throw this.toError(error as AxiosError);
    }
  }

  async postMultipart<T>(url: string, formData: FormData): Promise<T> {
    try {
      const response = await this.client.post<T>(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    } catch (error) {
      throw this.toError(error as AxiosError);
    }
  }
}

export const apiClient = new APIClient();
