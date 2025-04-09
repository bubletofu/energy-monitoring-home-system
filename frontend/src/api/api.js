// import axios from 'axios';

// const API = axios.create({
//   baseURL: 'http://localhost:8000',
//   headers: {
//     'Content-Type': 'application/json',
//   },
// });

// API.interceptors.request.use((config) => {
//   const token = localStorage.getItem('token');
//   if (token) {
//     config.headers.Authorization = `Bearer ${token}`;
//   }
//   return config;
// });

// // Mock data for testing without a backend
// const mockUser = {
//   id: 1,
//   username: 'mockuser',
//   email: 'mockuser@example.com',
// };

// const mockDevices = [
//   {
//     id: 1,
//     device_id: 'device1',
//     name: 'Living Room Thermostat',
//     is_online: true,
//     last_value: '72.0',
//     status_details: {
//       data_source: 'sensor_data',
//       last_data_time: '2025-04-08T10:00:00Z',
//       current_time: '2025-04-08T10:05:00Z',
//       message: 'Refreshed',
//     },
//     user_id: 1,
//   },
//   {
//     id: 2,
//     device_id: 'device2',
//     name: 'Kitchen Lights',
//     is_online: false,
//     last_value: 'N/A',
//     status_details: {
//       data_source: 'sensor_data',
//       last_data_time: '2025-04-07T15:00:00Z',
//       current_time: '2025-04-08T10:05:00Z',
//       message: 'Cached',
//     },
//     user_id: 1,
//   },
// ];

// // Mock API functions to match the API documentation

// // 1. Đăng nhập (POST /login/)
// export const login = async (credentials) => {
//   console.log('Mock login with:', credentials);
//   return {
//     data: {
//       success: true,
//       user: mockUser,
//       token: 'mock-jwt-token', // Added token to match typical auth flow
//     },
//   };
// };

// // 2. Đăng xuất (POST /logout/)
// export const logout = async () => {
//   console.log('Mock logout');
//   return { data: { message: 'Đăng xuất thành công' } };
// };

// // 3. Kiểm tra đăng nhập (GET /check-auth/)
// export const checkAuth = async () => {
//   console.log('Mock check-auth');
//   return {
//     data: {
//       is_authenticated: true,
//       user: mockUser,
//     },
//   };
// };

// // 4. Lấy trạng thái thiết bị (GET /device-status/)
// export const getDeviceStatus = async (params) => {
//   console.log('Mock getDeviceStatus with params:', params);
//   return { data: mockDevices };
// };

// // 5. Đổi tên thiết bị (POST /devices/rename/)
// export const renameDevice = async (data) => {
//   console.log('Mock renameDevice:', data);
//   return { data: { message: 'Device renamed successfully' } };
// };

// // 6. Yêu cầu sở hữu thiết bị (POST /devices/claim/)
// export const claimDevice = async (data) => {
//   console.log('Mock claimDevice:', data);
//   return { data: { message: 'Device claimed successfully' } };
// };

// // 7. Từ bỏ quyền sở hữu thiết bị (POST /devices/remove/)
// export const removeDevice = async (data) => {
//   console.log('Mock removeDevice:', data);
//   return { data: { message: 'Device removed successfully' } };
// };

// // 10. Quản lý người dùng

// // Tạo người dùng mới (POST /users/)
// export const createUser = async (data) => {
//   console.log('Mock createUser:', data);
//   return { data: { id: 2, username: data.username, email: data.email } };
// };

// // Lấy thông tin người dùng hiện tại (GET /users/me/)
// export const getCurrentUser = async () => {
//   console.log('Mock getCurrentUser');
//   return { data: mockUser };
// };

// export default API;


import axios from 'axios';

const API = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

API.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// API functions for real backend calls
export const login = (credentials) => API.post('/login/', credentials);
export const logout = () => API.post('/logout/');
export const checkAuth = () => API.get('/check-auth/');
export const getDeviceStatus = (params) => API.get('/device-status/', { params });
export const renameDevice = (data) => API.post('/devices/rename/', data);
export const claimDevice = (data) => API.post('/devices/claim/', data);
export const removeDevice = (data) => API.post('/devices/remove/', data);
export const createUser = (data) => API.post('/users/', data);
export const getCurrentUser = () => API.get('/users/me/');

export default API;