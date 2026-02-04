import axios, { AxiosInstance, AxiosError } from 'axios';
import { ErrorResponse } from '@/types/api';

// Use a function to get the URL to handle SSR properly
const getBaseURL = () => {
  return process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';
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
        const token = localStorage.getItem('access_token');
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
          // Clear token and redirect to login (only for protected routes, not login attempts)
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
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

  async get<T>(url: string): Promise<T> {
    try {
      const response = await this.client.get<T>(url);
      return response.data;
    } catch (error) {
      throw this.parseError(error as AxiosError);
    }
  }

  async post<T>(url: string, data?: any): Promise<T> {
    try {
      const response = await this.client.post<T>(url, data);
      return response.data;
    } catch (error) {
      throw this.parseError(error as AxiosError);
    }
  }

  async put<T>(url: string, data?: any): Promise<T> {
    try {
      const response = await this.client.put<T>(url, data);
      return response.data;
    } catch (error) {
      throw this.parseError(error as AxiosError);
    }
  }

  async patch<T>(url: string, data?: any): Promise<T> {
    try {
      const response = await this.client.patch<T>(url, data);
      return response.data;
    } catch (error) {
      throw this.parseError(error as AxiosError);
    }
  }

  async delete<T>(url: string): Promise<T> {
    try {
      const response = await this.client.delete<T>(url);
      return response.data;
    } catch (error) {
      throw this.parseError(error as AxiosError);
    }
  }
}

export const apiClient = new APIClient();
