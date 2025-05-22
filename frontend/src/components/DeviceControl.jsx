import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { renameDevice, claimDevice, removeDevice, turnDevice, listDevices, controlDevice } from '../api/api';

// Styled Components
const DeviceContainer = styled.div`
  background-color: #0f172a;
  padding: 20px;
  color: white;
`;

const DeviceList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 15px;
`;

const DeviceItem = styled.div`
  background-color: #1e293b;
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
  color: #dbeafe;
`;

const DeviceDetail = styled.p`
  margin: 5px 0 0 0;
  font-size: 14px;
  color: #dbeafe;
`;

const DeviceActions = styled.div`
  display: flex;
  gap: 10px;
`;

const ActionButton = styled.button`
  background-color: transparent;
  border: 1px solid #10b981;
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
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const TurnButton = styled(ActionButton)`
  border-color: ${(props) => (props.on ? '#e11d48' : '#10b981')};
  color: ${(props) => (props.on ? '#e11d48' : '#10b981')};
  &:hover {
    background-color: ${(props) => (props.on ? '#e11d48' : '#10b981')};
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
  background-color: #334155;
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
  background-color: #10b981;
  border: none;
  color: white;
  padding: 8px 15px;
  border-radius: 20px;
  cursor: pointer;
  text-transform: uppercase;
  font-size: 12px;
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

const RenameInput = styled.input`
  background-color: #334155;
  border: 1px solid #64748b;
  border-radius: 5px;
  padding: 5px;
  color: white;
  font-size: 14px;
  margin-right: 10px;
`;

const LoadingSpinner = styled.div`
  border: 2px solid #10b981;
  border-top: 2px solid transparent;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;
  margin-left: 10px;
  display: inline-block;

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

// Mapping các feature cho từng loại thiết bị (FE mirror backend)
const DEVICE_FEATURES = {
  'yolo-fan': [
    { feature: 'toggle_power', feed: 'yolo-fan', type: 'toggle', values: [0, 1], label: 'Bật/Tắt quạt' },
    { feature: 'switch_mode', feed: 'yolo-fan-mode-select', type: 'toggle', values: [0, 1], label: 'Chuyển chế độ Auto/Manual' },
    { feature: 'adjust_temp_threshold', feed: 'temperature-var', type: 'slider', min: 0, max: 100, step: 1, label: 'Điều chỉnh ngưỡng nhiệt độ' },
    { feature: 'adjust_fan_speed', feed: 'yolo-fan-speed', type: 'slider', min: 0, max: 100, step: 10, label: 'Điều chỉnh tốc độ quạt' },
  ],
  'yolo-light': [
    { feature: 'toggle_power', feed: 'yolo-led', type: 'toggle', values: [0, 1], label: 'Bật/Tắt đèn' },
    { feature: 'switch_mode', feed: 'yolo-led-mode-select', type: 'toggle', values: [0, 1], label: 'Chuyển chế độ Auto/Manual' },
    { feature: 'adjust_brightness_threshold', feed: 'light-var', type: 'slider', min: 0, max: 100, step: 1, label: 'Điều chỉnh ngưỡng sáng' },
    { feature: 'select_led_num', feed: 'yolo-led-num', type: 'slider', min: 1, max: 10, step: 1, label: 'Chọn số lượng đèn' },
  ],
  'yolo-device': [],
};

/**
 * DeviceControl component for managing IoT devices.
 * Fetches and displays a list of devices owned by the current user, allowing renaming, removing, claiming, and turning devices on/off.
 */
function DeviceControl() {
  const [devices, setDevices] = useState([]);
  const [newDeviceId, setNewDeviceId] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState({}); // Track loading state for each action
  const [renameState, setRenameState] = useState({ deviceId: null, newName: '' }); // Manage rename input

  // Fetch devices on mount
  useEffect(() => {
    const fetchDevices = async () => {
      setLoading((prev) => ({ ...prev, fetch: true }));
      try {
        const response = await listDevices();
        // Mock last_value since backend does not provide it
        const devicesWithState = (response.data || []).map(device => ({
          ...device,
          last_value: device.last_value || '0' // Default to 'off' if not provided
        }));
        setDevices(devicesWithState);
        setError('');
      } catch (error) {
        const errorMessage = error.response?.data?.detail || 'Failed to fetch devices';
        setError(errorMessage);
        console.error('Failed to fetch devices:', errorMessage);
        setDevices([]); // Empty list on failure
      } finally {
        setLoading((prev) => ({ ...prev, fetch: false }));
      }
    };
    fetchDevices();
  }, []);

  /**
   * Initiates the rename process for a device by showing an input field.
   * @param {Object} device - The device to rename
   */
  const startRename = (device) => {
    setRenameState({ deviceId: device.device_id, newName: device.device_id });
  };

  /**
   * Handles renaming a device by sending the new name to the backend.
   * @param {Object} device - The device to rename
   */
  const handleRename = async (device) => {
    if (!renameState.newName) {
      setError('Please enter a new device ID');
      return;
    }
    setLoading((prev) => ({ ...prev, [device.device_id]: 'rename' }));
    try {
      const response = await renameDevice({
        old_device_id: device.device_id,
        new_device_id: renameState.newName,
      });
      setDevices((prev) =>
        prev.map((d) =>
          d.device_id === device.device_id
            ? { ...d, device_id: renameState.newName }
            : d
        )
      );
      setRenameState({ deviceId: null, newName: '' });
      setSuccess(response.data.message);
      setError('');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Failed to rename device';
      setError(errorMessage);
      setSuccess('');
      console.error('Failed to rename device:', errorMessage);
    } finally {
      setLoading((prev) => ({ ...prev, [device.device_id]: undefined }));
    }
  };

  /**
   * Handles removing a device from the user's ownership.
   * @param {Object} device - The device to remove
   */
  const handleRemove = async (device) => {
    if (!window.confirm(`Are you sure you want to remove ${device.device_id}?`)) return;
    setLoading((prev) => ({ ...prev, [device.device_id]: 'remove' }));
    try {
      const response = await removeDevice(device.device_id);
      setDevices((prev) => prev.filter((d) => d.device_id !== device.device_id));
      setSuccess(response.data.message);
      setError('');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Failed to remove device';
      setError(errorMessage);
      setSuccess('');
      console.error('Failed to remove device:', errorMessage);
    } finally {
      setLoading((prev) => ({ ...prev, [device.device_id]: undefined }));
    }
  };

  /**
   * Handles claiming a new device by adding it to the user's ownership.
   */
  const handleClaim = async () => {
    if (!newDeviceId) {
      setError('Please enter a device ID');
      return;
    }
    setLoading((prev) => ({ ...prev, claim: true }));
    try {
      const response = await claimDevice(newDeviceId);
      // Refetch device list after claiming
      const updatedResponse = await listDevices();
      const devicesWithState = (updatedResponse.data || []).map(device => ({
        ...device,
        last_value: device.last_value || '0' // Default to 'off' if not provided
      }));
      setDevices(devicesWithState);
      setNewDeviceId('');
      setSuccess(response.data.message);
      setError('');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Failed to claim device';
      setError(errorMessage);
      setSuccess('');
      console.error('Failed to claim device:', errorMessage);
    } finally {
      setLoading((prev) => ({ ...prev, claim: false }));
    }
  };

  /**
   * Handles turning a device on or off.
   * @param {Object} device - The device to control
   * @param {number} value - 1 to turn on, 0 to turn off
   */
  const handleTurn = async (device, value) => {
    setLoading((prev) => ({ ...prev, [device.device_id]: `turn-${value}` }));
    try {
      const response = await turnDevice({
        device_id: device.device_id,
        value,
      });
      if (response.data.success) {
        setDevices((prev) =>
          prev.map((d) =>
            d.device_id === device.device_id ? { ...d, last_value: value.toString() } : d
          )
        );
        setSuccess(response.data.message);
        setError('');
      } else {
        setError(response.data.message);
        setSuccess('');
      }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Failed to turn device';
      setError(errorMessage);
      setSuccess('');
      console.error('Failed to turn device:', errorMessage);
    } finally {
      setLoading((prev) => ({ ...prev, [device.device_id]: undefined }));
    }
  };

  // Hàm gửi giá trị cho slider hoặc toggle (gọi đúng endpoint backend)
  const sendDeviceValue = async (device, feature, value) => {
    const payload = {
      device_id: device.device_id,
      feature: feature.feature,
      value,
    };
    setLoading((prev) => ({ ...prev, [`${device.device_id}-${feature.feature}`]: true }));
    try {
      console.log('Gửi điều khiển:', payload); // DEBUG
      const response = await controlDevice(payload);
      const data = response.data;
      console.log('Phản hồi backend:', data); // DEBUG
      if (data.success) {
        setSuccess(data.message || 'Đã gửi giá trị thành công');
        setError('');
        // Cập nhật local state cho device (slider/toggle)
        setDevices((prev) =>
          prev.map((d) =>
            d.device_id === device.device_id
              ? { ...d, [feature.feed]: value }
              : d
          )
        );
      } else {
        setError(data.message || 'Gửi giá trị thất bại');
        setSuccess('');
      }
    } catch (error) {
      setError('Gửi giá trị thất bại');
      setSuccess('');
      console.error('Lỗi gửi giá trị:', error);
    } finally {
      setLoading((prev) => ({ ...prev, [`${device.device_id}-${feature.feature}`]: false }));
    }
  };

  return (
    <DeviceContainer>
      {loading.fetch ? (
        <LoadingSpinner />
      ) : devices.length === 0 ? (
        <p>No devices found. Claim a device to get started.</p>
      ) : (
        <DeviceList>
          {devices.map((device) => (
            <DeviceItem key={device.id}>
              <DeviceInfo>
                <DeviceName>{device.device_id}</DeviceName>
                <DeviceDetail>Last Value: {device.last_value === '1' ? 'On' : 'Off'}</DeviceDetail>
              </DeviceInfo>
              <DeviceActions>
                {renameState.deviceId === device.device_id ? (
                  <>
                    <RenameInput
                      type="text"
                      value={renameState.newName}
                      onChange={(e) => setRenameState({ ...renameState, newName: e.target.value })}
                      placeholder="New Device ID"
                    />
                    <ActionButton
                      onClick={() => handleRename(device)}
                      disabled={loading[device.device_id] === 'rename'}
                      aria-label="Confirm rename device"
                    >
                      Save {loading[device.device_id] === 'rename' && <LoadingSpinner />}
                    </ActionButton>
                    <ActionButton
                      onClick={() => setRenameState({ deviceId: null, newName: '' })}
                      disabled={loading[device.device_id] === 'rename'}
                      aria-label="Cancel rename device"
                    >
                      Cancel
                    </ActionButton>
                  </>
                ) : (
                  <ActionButton
                    onClick={() => startRename(device)}
                    disabled={loading[device.device_id]}
                    aria-label={`Rename device ${device.device_id}`}
                  >
                    Rename
                  </ActionButton>
                )}
                <ActionButton
                  onClick={() => handleRemove(device)}
                  disabled={loading[device.device_id]}
                  aria-label={`Remove device ${device.device_id}`}
                >
                  Remove {loading[device.device_id] === 'remove' && <LoadingSpinner />}
                </ActionButton>
                {/* Render các feature động theo device_type */}
                {DEVICE_FEATURES[device.device_type]?.map((feature) => {
                  if (feature.type === 'toggle') {
                    // Toggle: 2 trạng thái, ví dụ Bật/Tắt
                    const isOn = device[feature.feed] === (feature.values[1] || 1);
                    return (
                      <TurnButton
                        key={feature.feed}
                        on={isOn}
                        onClick={() => sendDeviceValue(device, feature, isOn ? feature.values[0] : feature.values[1])}
                        disabled={loading[`${device.device_id}-${feature.feature}`]}
                        aria-label={feature.label}
                      >
                        {feature.label} {loading[`${device.device_id}-${feature.feature}`] && <LoadingSpinner />}
                      </TurnButton>
                    );
                  }
                  if (feature.type === 'slider') {
                    return (
                      <div key={feature.feed} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <label style={{ color: '#dbeafe', fontSize: 12 }}>{feature.label}</label>
                        <input
                          type="range"
                          min={feature.min}
                          max={feature.max}
                          step={feature.step}
                          value={device[feature.feed] || feature.min}
                          onChange={e => sendDeviceValue(device, feature, Number(e.target.value))}
                          disabled={loading[`${device.device_id}-${feature.feature}`]}
                          style={{ marginLeft: 8 }}
                        />
                        <span style={{ color: '#10b981', fontSize: 12 }}>{device[feature.feed] || feature.min}</span>
                      </div>
                    );
                  }
                  return null;
                })}
              </DeviceActions>
            </DeviceItem>
          ))}
        </DeviceList>
      )}
      <ClaimSection>
        <ClaimInput
          type="text"
          placeholder="Device ID"
          value={newDeviceId}
          onChange={(e) => setNewDeviceId(e.target.value)}
          aria-label="Enter device ID to claim"
        />
        <ClaimButton
          onClick={handleClaim}
          disabled={loading.claim}
          aria-label="Claim new device"
        >
          Claim New Device {loading.claim && <LoadingSpinner />}
        </ClaimButton>
      </ClaimSection>
      {error && <ErrorMessage>{error}</ErrorMessage>}
      {success && <SuccessMessage>{success}</SuccessMessage>}
    </DeviceContainer>
  );
}

export default DeviceControl;
