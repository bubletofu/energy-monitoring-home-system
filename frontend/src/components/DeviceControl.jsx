import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import axios from 'axios';

// Create axios instance
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

// Mock data for testing without a backend
const mockUser = {
  id: 1,
  username: 'mockuser',
  email: 'mockuser@example.com',
};

const mockDevices = [
  {
    id: 1,
    device_id: 'device1',
    name: 'Living Room Thermostat',
    is_online: true,
    last_value: '72.0',
    status_details: {
      data_source: 'sensor_data',
      last_data_time: '2025-04-08T10:00:00Z',
      current_time: '2025-04-08T10:05:00Z',
      message: 'Refreshed',
    },
    user_id: 1,
  },
  {
    id: 2,
    device_id: 'device2',
    name: 'Kitchen Lights',
    is_online: false,
    last_value: 'N/A',
    status_details: {
      data_source: 'sensor_data',
      last_data_time: '2025-04-07T15:00:00Z',
      current_time: '2025-04-08T10:05:00Z',
      message: 'Cached',
    },
    user_id: 1,
  },
];

// Mock API functions to match the API documentation

// 1. Đăng nhập (POST /login/)
const login = async (credentials) => {
  console.log('Mock login with:', credentials);
  return {
    data: {
      success: true,
      user: mockUser,
      token: 'mock-jwt-token',
    },
  };
};

// 2. Đăng xuất (POST /logout/)
const logout = async () => {
  console.log('Mock logout');
  return { data: { message: 'Đăng xuất thành công' } };
};

// 3. Kiểm tra đăng nhập (GET /check-auth/)
const checkAuth = async () => {
  console.log('Mock check-auth');
  return {
    data: {
      is_authenticated: true,
      user: mockUser,
    },
  };
};

// 4. Lấy trạng thái thiết bị (GET /device-status/)
const getDeviceStatus = async (params) => {
  console.log('Mock getDeviceStatus with params:', params);
  return { data: mockDevices };
};

// 5. Đổi tên thiết bị (POST /devices/rename/)
const renameDevice = async (data) => {
  console.log('Mock renameDevice:', data);
  return { data: { message: 'Device renamed successfully' } };
};

// 6. Yêu cầu sở hữu thiết bị (POST /devices/claim/)
const claimDevice = async (data) => {
  console.log('Mock claimDevice:', data);
  return { data: { message: 'Device claimed successfully' } };
};

// 7. Từ bỏ quyền sở hữu thiết bị (POST /devices/remove/)
const removeDevice = async (data) => {
  console.log('Mock removeDevice:', data);
  return { data: { message: 'Device removed successfully' } };
};

// 10. Quản lý người dùng

// Tạo người dùng mới (POST /users/)
const createUser = async (data) => {
  console.log('Mock createUser:', data);
  return { data: { id: 2, username: data.username, email: data.email } };
};

// Lấy thông tin người dùng hiện tại (GET /users/me/)
const getCurrentUser = async () => {
  console.log('Mock getCurrentUser');
  return { data: mockUser };
};

// Styled components for DeviceControl
const DeviceContainer = styled.div`
  background-color: #0f172a; /* Match dashboard background */
  padding: 20px;
  color: white;
`;

const DeviceList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 15px;
`;

const DeviceItem = styled.div`
  background-color: #1e293b; /* Match container background */
  padding: 15px;
  border-radius: 5px;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const DeviceInfo = styled.div`
  display: flex;
  flex-direction: column;
`;

const DeviceName = styled.h4`
  margin: 0;
  font-size: 16px;
  color: #dbeafe; /* Match label color */
`;

const DeviceDetail = styled.p`
  margin: 5px 0 0 0;
  font-size: 14px;
  color: #dbeafe;
`;

const DeviceStatus = styled.span`
  color: ${(props) => (props.online ? '#10b981' : '#e11d48')}; /* Green for online, red for offline */
`;

const DeviceActions = styled.div`
  display: flex;
  gap: 10px;
`;

const ActionButton = styled.button`
  background-color: transparent;
  border: 1px solid #10b981; /* Green accent */
  color: #10b981;
  padding: 5px 15px;
  border-radius: 20px;
  cursor: pointer;
  text-transform: uppercase;
  font-size: 12px;
  &:hover {
    background-color: #10b981;
    color: white;
  }
`;

const ClaimSection = styled.div`
  margin-top: 20px;
  display: flex;
  gap: 10px;
  align-items: center;
`;

const ClaimInput = styled.input`
  background-color: #334155; /* Match input background */
  border: 1px solid #64748b;
  border-radius: 5px;
  padding: 8px;
  color: white;
  font-size: 14px;
  width: 200px;
  &::placeholder {
    color: #dbeafe;
  }
`;

const ClaimButton = styled.button`
  background-color: #10b981; /* Green accent */
  border: none;
  color: white;
  padding: 8px 15px;
  border-radius: 20px;
  cursor: pointer;
  text-transform: uppercase;
  font-size: 12px;
  &:hover {
    background-color: #059669; /* Green hover */
  }
`;

function DeviceControl() {
  const [devices, setDevices] = useState([]);
  const [newDeviceId, setNewDeviceId] = useState('');

  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const response = await getDeviceStatus();
        setDevices(response.data);
      } catch (error) {
        console.error('Failed to fetch devices:', error);
      }
    };
    fetchDevices();
  }, []);

  const handleRename = async (device) => {
    const newName = prompt('Enter new device name:', device.name);
    if (newName) {
      try {
        const response = await renameDevice({
          old_device_id: device.device_id,
          new_device_id: device.device_id, // API expects device_id, not name
        });
        alert(response.data.message);
        // Update local state to reflect the new name
        setDevices((prev) =>
          prev.map((d) =>
            d.device_id === device.device_id ? { ...d, name: newName } : d
          )
        );
      } catch (error) {
        console.error('Failed to rename device:', error);
        alert('Failed to rename device');
      }
    }
  };

  const handleRemove = async (device) => {
    if (window.confirm(`Are you sure you want to remove ${device.name}?`)) {
      try {
        const response = await removeDevice({ device_id: device.device_id });
        alert(response.data.message);
        // Remove device from local state
        setDevices((prev) => prev.filter((d) => d.device_id !== device.device_id));
      } catch (error) {
        console.error('Failed to remove device:', error);
        alert('Failed to remove device');
      }
    }
  };

  const handleClaim = async () => {
    if (!newDeviceId) {
      alert('Please enter a device ID');
      return;
    }
    try {
      const response = await claimDevice({ device_id: newDeviceId });
      alert(response.data.message);
      // Simulate adding a new device (mock behavior)
      const newDevice = {
        id: devices.length + 1,
        device_id: newDeviceId,
        name: `New Device ${newDeviceId}`,
        is_online: true,
        last_value: 'N/A',
        status_details: {
          data_source: 'sensor_data',
          last_data_time: '2025-04-08T10:00:00Z',
          current_time: '2025-04-08T10:05:00Z',
          message: 'Refreshed',
        },
        user_id: 1,
      };
      setDevices((prev) => [...prev, newDevice]);
      setNewDeviceId(''); // Clear input
    } catch (error) {
      console.error('Failed to claim device:', error);
      alert('Failed to claim device');
    }
  };

  return (
    <DeviceContainer>
      <DeviceList>
        {devices.map((device) => (
          <DeviceItem key={device.id}>
            <DeviceInfo>
              <DeviceName>{device.name}</DeviceName>
              <DeviceDetail>
                Status: <DeviceStatus online={device.is_online}>
                  {device.is_online ? 'Online' : 'Offline'}
                </DeviceStatus>
              </DeviceDetail>
              <DeviceDetail>Last Value: {device.last_value}</DeviceDetail>
            </DeviceInfo>
            <DeviceActions>
              <ActionButton onClick={() => handleRename(device)}>Rename</ActionButton>
              <ActionButton onClick={() => handleRemove(device)}>Remove</ActionButton>
            </DeviceActions>
          </DeviceItem>
        ))}
      </DeviceList>
      <ClaimSection>
        <ClaimInput
          type="text"
          placeholder="Device ID"
          value={newDeviceId}
          onChange={(e) => setNewDeviceId(e.target.value)}
        />
        <ClaimButton onClick={handleClaim}>Claim New Device</ClaimButton>
      </ClaimSection>
    </DeviceContainer>
  );
}

export default DeviceControl;