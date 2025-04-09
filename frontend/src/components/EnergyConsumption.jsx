import React from 'react';
import styled from 'styled-components';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

// Mock data for devices
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

// Mock API function
const getDeviceStatus = async (params) => {
  console.log('Mock getDeviceStatus with params:', params);
  return { data: mockDevices };
};

// Styled components (unchanged)
const EnergyContainer = styled.div`
  background-color: #1e293b;
  padding: 20px;
  border-radius: 10px;
  flex: 2;
  min-width: 500px;
  color: white;
`;

const Title = styled.h3`
  margin: 0 0 20px 0;
  font-size: 18px;
`;

const StatsContainer = styled.div`
  display: flex;
  gap: 20px;
  margin-top: 20px;
`;

const StatBox = styled.div`
  background-color: #334155;
  padding: 15px;
  border-radius: 10px;
  flex: 1;
  text-align: center;
`;

const StatTitle = styled.p`
  margin: 0 0 5px 0;
  font-size: 14px;
  color: #dbeafe;
`;

const StatValue = styled.p`
  margin: 0;
  font-size: 20px;
  color: #10b981;
`;

const ConnectedDevices = styled.div`
  margin-top: 20px;
`;

const DeviceList = styled.div`
  display: flex;
  gap: 20px;
  margin-top: 10px;
`;

const DeviceItem = styled.div`
  background-color: #334155;
  padding: 10px;
  border-radius: 5px;
  flex: 1;
  text-align: center;
`;

const DeviceStatus = styled.span`
  color: ${(props) => (props.online ? '#10b981' : '#e11d48')};
`;

function EnergyConsumption() {
  const [devices, setDevices] = React.useState([]);

  React.useEffect(() => {
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

  const chartData = [
    { time: '00:00', current: 2.0, previous: 1.8 },
    { time: '04:00', current: 3.5, previous: 2.0 },
    { time: '08:00', current: 4.8, previous: 2.5 },
    { time: '12:00', current: 5.4, previous: 2.2 },
    { time: '16:00', current: 6.0, previous: 2.0 },
    { time: '20:00', current: 5.8, previous: 1.9 },
  ];

  return (
    <EnergyContainer>
      <Title>Real-Time Energy Consumption</Title>
      <LineChart width={500} height={300} data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#64748b" />
        <XAxis dataKey="time" stroke="#dbeafe" />
        <YAxis stroke="#dbeafe" />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="current" stroke="#10b981" name="Current Period" />
        <Line type="monotone" dataKey="previous" stroke="#a855f7" name="Previous Period" />
      </LineChart>
      <StatsContainer>
        <StatBox>
          <StatTitle>Current Usage</StatTitle>
          <StatValue>5.4 kW</StatValue>
        </StatBox>
        <StatBox>
          <StatTitle>Peak Consumption</StatTitle>
          <StatValue>7.2 kW</StatValue>
        </StatBox>
        <StatBox>
          <StatTitle>Cost Savings</StatTitle>
          <StatValue>$12.50</StatValue>
        </StatBox>
      </StatsContainer>
      <ConnectedDevices>
        <Title>Connected Devices</Title>
        <DeviceList>
          {devices.map((device) => (
            <DeviceItem key={device.id}>
              {device.name} <br />
              <DeviceStatus online={device.is_online}>
                {device.is_online ? 'Online' : 'Offline'}
              </DeviceStatus>
            </DeviceItem>
          ))}
        </DeviceList>
      </ConnectedDevices>
    </EnergyContainer>
  );
}

export default EnergyConsumption;