import axios from 'axios';

// Create an Axios instance for API requests
const API = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // Set a 10-second timeout for all requests
});

// Interceptor to add Authorization header with token from localStorage
API.interceptors.request.use(
  (config) => {
    try {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    } catch (error) {
      console.error('Error retrieving token from localStorage:', error);
      return config; // Proceed without token if retrieval fails
    }
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor to handle response errors (e.g., 401 Unauthorized)
API.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.warn('Unauthorized request - redirecting to login');
      localStorage.removeItem('token'); // Clear invalid token
      window.location.href = '/login'; // Redirect to login page
    }
    return Promise.reject(error);
  }
);

// Authentication Endpoints

/**
 * Logs in a user by sending credentials to the backend.
 * @param {Object} formData - Contains username and password (e.g., { username: 'user', password: 'pass' })
 * @returns {Promise} - Axios response with access token and user data
 */
export const login = (formData) =>
  API.post('/login/', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

/**
 * Registers a new user.
 * @param {Object} data - Contains username, email, and password (e.g., { username: 'user', email: 'user@example.com', password: 'pass' })
 * @returns {Promise} - Axios response with success message
 */
export const register = (data) => API.post('/register/', data);

/**
 * Logs out the current user by clearing the auth cookie on the backend.
 * @returns {Promise} - Axios response with success message
 */
export const logout = () => API.post('/logout/');

/**
 * Checks if the user is authenticated.
 * @returns {Promise} - Axios response with authentication status (e.g., { is_authenticated: true, user: {...} })
 */
export const checkAuth = () => API.get('/check-auth/');

/**
 * Fetches the current user's information.
 * @returns {Promise} - Axios response with user data (e.g., { id: 1, username: 'user', email: 'user@example.com' })
 */
export const getCurrentUser = () => API.get('/auth/me/');

// Device Management Endpoints

/**
 * Renames a device for the authenticated user.
 * @param {Object} data - Contains old_device_id and new_device_id (e.g., { old_device_id: 'device1', new_device_id: 'device2' })
 * @returns {Promise} - Axios response with success message
 */
export const renameDevice = (data) => API.post('/devices/rename/', data);

/**
 * Claims ownership of a device for the authenticated user.
 * @param {string} deviceId - The ID of the device to claim (e.g., 'device1')
 * @returns {Promise} - Axios response with success message
 */
export const claimDevice = (deviceId) => API.post(`/api/devices/claim/${deviceId}`);

/**
 * Removes ownership of a device for the authenticated user.
 * @param {string} deviceId - The ID of the device to remove (e.g., 'device1')
 * @returns {Promise} - Axios response with success message
 */
export const removeDevice = (deviceId) => API.post('/devices/remove/', { device_id: deviceId });

/**
 * Turns a device on or off for the authenticated user.
 * @param {Object} data - Contains device_id and value (e.g., { device_id: 'device1', value: 1 })
 * @returns {Promise} - Axios response with success message
 */
export const turnDevice = (data) => API.post('/devices/turn/', data);

export default API;