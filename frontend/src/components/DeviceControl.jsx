import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { listDevices, renameDevice, claimDevice, removeDevice, turnDevice } from '../api/api';

// Styled Components
const DeviceControlContainer = styled.div`
  background-color: #1e293b;
  padding: 20px;
  border-radius: 10px;
  color: white;
  flex: 1;
  min-width: 300px;
`;

const Title = styled.h3`
  margin: 0 0 20px 0;
  font-size: 18px;
`;

const DeviceList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0 0 20px 0;
`;

const DeviceItem = styled.li`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background-color: #334155;
  border-radius: 5px;
  margin-bottom: 10px;
`;

const DeviceName = styled.span`
  font-size: 16px;
`;

const DeviceActions = styled.div`
  display: flex;
  gap: 10px;
`;

const ActionButton = styled.button`
  background-color: ${(props) => (props.danger ? '#e11d48' : '#10b981')};
  color: white;
  border: none;
  padding: 5px 10px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  &:hover {
    background-color: ${(props) => (props.danger ? '#be123c' : '#059669')};
  }
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
`;

const Input = styled.input`
  padding: 10px;
  border: 1px solid #64748b;
  border-radius: 5px;
  background-color: #334155;
  color: white;
  font-size: 14px;
  &:focus {
    outline: none;
    border-color: #10b981;
  }
`;

const Button = styled.button`
  background-color: #10b981;
  color: white;
  border: none;
  padding: 10px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  &:hover {
    background-color: #059669;
  }
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const ErrorMessage = styled.p`
  color: #e11d48;
  font-size: 14px;
  margin-top: 10px;
`;

const SuccessMessage = styled.p`
  color: #10b981;
  font-size: 14px;
  margin-top: 10px;
`;

function DeviceControl() {
  const [devices, setDevices] = useState([]);
  const [claimDeviceId, setClaimDeviceId] = useState('');
  const [renameData, setRenameData] = useState({ old_device_id: '', new_device_id: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchDevices = async () => {
    setLoading(true);
    try {
      const response = await listDevices();
      setDevices(response.data);
      setError('');
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to fetch devices.');
      console.error('Fetch devices error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const handleClaimDevice = async (e) => {
    e.preventDefault();
    if (!claimDeviceId.trim()) {
      setError('Device ID is required to claim a device.');
      return;
    }
    setLoading(true);
    try {
      const response = await claimDevice(claimDeviceId);
      setSuccess(response.data.message);
      setError('');
      setClaimDeviceId('');
      fetchDevices(); // Refresh device list
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to claim device.');
      setSuccess('');
      console.error('Claim device error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRenameDevice = async (e) => {
    e.preventDefault();
    if (!renameData.old_device_id.trim() || !renameData.new_device_id.trim()) {
      setError('Both old and new device IDs are required.');
      return;
    }
    setLoading(true);
    try {
      const response = await renameDevice(renameData);
      setSuccess(response.data.message);
      setError('');
      setRenameData({ old_device_id: '', new_device_id: '' });
      fetchDevices(); // Refresh device list
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to rename device.');
      setSuccess('');
      console.error('Rename device error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveDevice = async (deviceId) => {
    setLoading(true);
    try {
      const response = await removeDevice(deviceId);
      setSuccess(response.data.message);
      setError('');
      fetchDevices(); // Refresh device list
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to remove device.');
      setSuccess('');
      console.error('Remove device error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTurnDevice = async (deviceId, value) => {
    setLoading(true);
    try {
      const response = await turnDevice({ device_id: deviceId, value });
      setSuccess(response.data.message);
      setError('');
      fetchDevices(); // Refresh device list
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to turn device.');
      setSuccess('');
      console.error('Turn device error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <DeviceControlContainer>
      <Title>Device Control</Title>
      <Form onSubmit={handleClaimDevice}>
        <Input
          type="text"
          placeholder="Enter Device ID to Claim"
          value={claimDeviceId}
          onChange={(e) => setClaimDeviceId(e.target.value)}
          disabled={loading}
        />
        <Button type="submit" disabled={loading}>Claim Device</Button>
      </Form>
      <Form onSubmit={handleRenameDevice}>
        <Input
          type="text"
          placeholder="Old Device ID"
          value={renameData.old_device_id}
          onChange={(e) => setRenameData({ ...renameData, old_device_id: e.target.value })}
          disabled={loading}
        />
        <Input
          type="text"
          placeholder="New Device ID"
          value={renameData.new_device_id}
          onChange={(e) => setRenameData({ ...renameData, new_device_id: e.target.value })}
          disabled={loading}
        />
        <Button type="submit" disabled={loading}>Rename Device</Button>
      </Form>
      {error && <ErrorMessage>{error}</ErrorMessage>}
      {success && <SuccessMessage>{success}</SuccessMessage>}
      <DeviceList>
        {devices.map((device) => (
          <DeviceItem key={device.id}>
            <DeviceName>{device.device_id}</DeviceName>
            <DeviceActions>
              <ActionButton onClick={() => handleTurnDevice(device.device_id, 1)} disabled={loading}>
                Turn On
              </ActionButton>
              <ActionButton onClick={() => handleTurnDevice(device.device_id, 0)} disabled={loading}>
                Turn Off
              </ActionButton>
              <ActionButton
                danger
                onClick={() => handleRemoveDevice(device.device_id)}
                disabled={loading}
              >
                Remove
              </ActionButton>
            </DeviceActions>
          </DeviceItem>
        ))}
      </DeviceList>
    </DeviceControlContainer>
  );
}

export default DeviceControl;
