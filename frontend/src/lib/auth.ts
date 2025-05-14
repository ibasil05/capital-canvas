// Types
export interface SignUpData {
  email: string;
  password: string;
  confirm_password: string;
  redirect_to?: string;
}

export interface SignInData {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  user: {
    id: string;
    email: string;
    email_confirmed_at?: string;
  };
}

// Local storage functions

// Get auth token from localStorage
export const getAuthToken = (): string | null => {
  return localStorage.getItem('auth_token');
};

// Set auth token in localStorage
export const setAuthToken = (token: string): void => {
  localStorage.setItem('auth_token', token);
};

// Remove auth token from localStorage
export const removeAuthToken = (): void => {
  localStorage.removeItem('auth_token');
};

// Check if user is authenticated
export const isAuthenticated = (): boolean => {
  return !!getAuthToken();
};

// Sign out a user (doesn't require API)
export const signOut = (): void => {
  removeAuthToken();
  window.location.href = '/signin';
};
