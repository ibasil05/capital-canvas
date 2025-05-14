import axios from 'axios';
import { getAuthToken } from './auth';
import type { SignUpData, SignInData, AuthResponse } from './auth';

// Create axios instance with base URL
const api = axios.create({
  baseURL: 'http://127.0.0.1:9000',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Add request interceptor to inject auth token
api.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle 401 Unauthorized errors (token expired or invalid)
    if (error.response && error.response.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('auth_token');
      window.location.href = '/signin';
    }
    return Promise.reject(error);
  }
);

// Auth API functions
export const authAPI = {
  // Sign up a new user
  signUp: async (data: SignUpData): Promise<any> => {
    try {
      const response = await api.post('/auth/signup', data);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Sign in a user
  signIn: async (data: SignInData): Promise<AuthResponse> => {
    try {
      const response = await api.post('/auth/signin', data);
      const { access_token } = response.data;
      
      // Store the token in localStorage
      if (access_token) {
        localStorage.setItem('auth_token', access_token);
      }
      
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get current user
  getCurrentUser: async (): Promise<any> => {
    try {
      const response = await api.get('/auth/me');
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Reset password
  resetPassword: async (email: string, redirect_to?: string): Promise<any> => {
    try {
      const response = await api.post('/auth/reset-password', { email, redirect_to });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Update password with token
  updatePassword: async (token: string, new_password: string, confirm_password: string): Promise<any> => {
    try {
      const response = await api.post('/auth/update-password', { token, new_password, confirm_password });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Change password when logged in
  changePassword: async (current_password: string, new_password: string, confirm_password: string): Promise<any> => {
    try {
      const response = await api.post('/auth/change-password', { current_password, new_password, confirm_password });
      return response.data;
    } catch (error) {
      throw error;
    }
  },
};

export default api;
