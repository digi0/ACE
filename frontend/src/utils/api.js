import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

// Create axios instance with interceptors
const api = axios.create({
  baseURL: API,
});

// Add auth token to all requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ace_session_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('ace_session_token');
      localStorage.removeItem('ace_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth functions
export const setAuth = (sessionToken, user) => {
  localStorage.setItem('ace_session_token', sessionToken);
  localStorage.setItem('ace_user', JSON.stringify(user));
};

export const clearAuth = () => {
  localStorage.removeItem('ace_session_token');
  localStorage.removeItem('ace_user');
};

export const getStoredUser = () => {
  const userStr = localStorage.getItem('ace_user');
  return userStr ? JSON.parse(userStr) : null;
};

export const isAuthenticated = () => {
  return !!localStorage.getItem('ace_session_token');
};

export default api;
