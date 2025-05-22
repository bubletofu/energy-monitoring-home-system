import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { getCurrentUser, addDevice, deleteDevice, compressDeviceData, listDevices, removeDevice, decompressDeviceData, claimDevice } from '../api/api';

const Container = styled.div`
  padding: 40px;
  max-width: 700px;
  margin: 0 auto;
  color: white;
`;
const Section = styled.div`
  margin-bottom: 32px;
`;
const Input = styled.input`
  padding: 8px;
  margin-right: 10px;
  border-radius: 5px;
  border: 1px solid #64748b;
  background: #1e293b;
  color: white;
`;
const Select = styled.select`
  padding: 8px;
  margin-right: 10px;
  border-radius: 5px;
  border: 1px solid #64748b;
  background: #1e293b;
  color: white;
`;
const Button = styled.button`
  padding: 8px 16px;
  border-radius: 20px;
  border: none;
  background: #10b981;
  color: white;
  font-weight: bold;
  cursor: pointer;
  &:hover { background: #059669; }
`;
const DeviceList = styled.ul`
  list-style: none;
  padding: 0;
`;
const DeviceItem = styled.li`
  margin-bottom: 10px;
  background: #334155;
  padding: 10px;
  border-radius: 5px;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

function AdminDeviceManager() {
  const [user, setUser] = useState(null);
  const [devices, setDevices] = useState([]);
  const [newDeviceId, setNewDeviceId] = useState('');
  const [newDeviceType, setNewDeviceType] = useState('yolo-fan');
  const [compressId, setCompressId] = useState('');
  const [deleteId, setDeleteId] = useState('');
  const [message, setMessage] = useState('');
  const [removeMessage, setRemoveMessage] = useState('');
  const [decompressId, setDecompressId] = useState('');
  const [decompressData, setDecompressData] = useState(null);
  const [decompressError, setDecompressError] = useState('');
  const [claimDeviceId, setClaimDeviceId] = useState('');
  const [claimMessage, setClaimMessage] = useState('');
  const [claimLoading, setClaimLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    getCurrentUser().then(res => {
      if (!res.data.role || res.data.role !== 'admin') {
        navigate('/login');
      } else {
        setUser(res.data);
        fetchDevices();
      }
    }).catch(() => navigate('/login'));
    // eslint-disable-next-line
  }, []);

  const fetchDevices = async () => {
    try {
      const res = await listDevices();
      setDevices(res.data);
    } catch (e) {
      setMessage('Không thể tải danh sách thiết bị');
    }
  };

  const handleAddDevice = async () => {
    if (!newDeviceId) return setMessage('Vui lòng nhập Device ID');
    try {
      await addDevice({ device_id: newDeviceId, device_type: newDeviceType });
      setMessage('Thêm thiết bị thành công!');
      setNewDeviceId('');
      fetchDevices();
    } catch (e) {
      setMessage('Lỗi khi thêm thiết bị');
    }
  };

  const handleDeleteDevice = async () => {
    if (!deleteId) return setMessage('Vui lòng nhập Device ID để xóa');
    if (!window.confirm(`Bạn chắc chắn muốn XÓA thiết bị ${deleteId} khỏi hệ thống?`)) return;
    try {
      await deleteDevice(deleteId);
      setMessage('Xóa thiết bị thành công!');
      setDeleteId('');
      fetchDevices();
    } catch (e) {
      setMessage('Lỗi khi xóa thiết bị');
    }
  };

  const handleCompress = async () => {
    if (!compressId) return setMessage('Vui lòng nhập Device ID để nén');
    try {
      await compressDeviceData(compressId);
      setMessage('Đã nén dữ liệu và lưu vào database!');
      setCompressId('');
    } catch (e) {
      setMessage('Lỗi khi nén dữ liệu');
    }
  };

  const handleRemoveDevice = async (device_id) => {
    try {
      await removeDevice(device_id);
      setRemoveMessage('Đã từ bỏ quyền sở hữu thiết bị!');
      fetchDevices();
    } catch (e) {
      setRemoveMessage('Lỗi khi từ bỏ quyền sở hữu thiết bị');
    }
  };

  const handleDecompress = async () => {
    setDecompressError('');
    setDecompressData(null);
    if (!decompressId) return setDecompressError('Vui lòng nhập Device ID');
    try {
      const res = await decompressDeviceData(decompressId);
      setDecompressData(res.data.data);
    } catch (e) {
      setDecompressError('Không tìm thấy hoặc lỗi khi giải nén dữ liệu');
    }
  };

  const handleClaimDevice = async () => {
    if (!claimDeviceId) {
      setClaimMessage('Vui lòng nhập Device ID để claim');
      return;
    }
    setClaimLoading(true);
    setClaimMessage('');
    try {
      const response = await claimDevice(claimDeviceId);
      await fetchDevices();
      setClaimMessage(response.data.message || 'Claim thành công!');
      setClaimDeviceId('');
    } catch (e) {
      setClaimMessage(e.response?.data?.detail || 'Claim thất bại');
    } finally {
      setClaimLoading(false);
    }
  };

  return (
    <Container>
      <h2>Admin Device Manager</h2>
      <Section>
        <h3>Claim quyền sở hữu thiết bị</h3>
        <Input value={claimDeviceId} onChange={e => setClaimDeviceId(e.target.value)} placeholder="Device ID để claim" />
        <Button onClick={handleClaimDevice} disabled={claimLoading}>{claimLoading ? 'Đang claim...' : 'Claim Device'}</Button>
        {claimMessage && <div style={{ color: claimMessage.includes('thành công') ? '#10b981' : '#e11d48', marginTop: 10 }}>{claimMessage}</div>}
      </Section>
      <Section>
        <h3>Thêm thiết bị mới</h3>
        <Input value={newDeviceId} onChange={e => setNewDeviceId(e.target.value)} placeholder="Device ID" />
        <Select value={newDeviceType} onChange={e => setNewDeviceType(e.target.value)}>
          <option value="yolo-fan">Yolo Fan</option>
          <option value="yolo-light">Yolo Light</option>
          <option value="yolo-device">Yolo Device</option>
        </Select>
        <Button onClick={handleAddDevice}>Add Device</Button>
      </Section>
      <Section>
        <h3>Danh sách thiết bị bạn sở hữu (Remove quyền sở hữu)</h3>
        <DeviceList>
          {devices.map(d => (
            <DeviceItem key={d.device_id}>
              <span>{d.device_id} ({d.device_type})</span>
              <Button onClick={() => handleRemoveDevice(d.device_id)}>Remove</Button>
            </DeviceItem>
          ))}
        </DeviceList>
        {removeMessage && <div style={{ color: '#e11d48', marginTop: 10 }}>{removeMessage}</div>}
      </Section>
      <Section>
        <h3>Delete Device (XÓA hoàn toàn khỏi hệ thống)</h3>
        <Input value={deleteId} onChange={e => setDeleteId(e.target.value)} placeholder="Device ID để xóa" />
        <Button onClick={handleDeleteDevice}>Delete Device</Button>
      </Section>
      <Section>
        <h3>Nén & lưu dữ liệu thiết bị</h3>
        <Input value={compressId} onChange={e => setCompressId(e.target.value)} placeholder="Device ID" />
        <Button onClick={handleCompress}>Save Data</Button>
      </Section>
      <Section>
        <h3>Xem dữ liệu JSON đã nén</h3>
        <Input value={decompressId} onChange={e => setDecompressId(e.target.value)} placeholder="Device ID" />
        <Button onClick={handleDecompress}>Giải nén & xem dữ liệu</Button>
        {decompressError && <div style={{ color: '#e11d48', marginTop: 10 }}>{decompressError}</div>}
        {decompressData && (
          <pre style={{ background: '#222', color: '#10b981', maxHeight: 300, overflow: 'auto', marginTop: 10 }}>
            {JSON.stringify(decompressData, null, 2)}
          </pre>
        )}
      </Section>
      {message && <div style={{ color: '#10b981', marginTop: 20 }}>{message}</div>}
    </Container>
  );
}

export default AdminDeviceManager; 