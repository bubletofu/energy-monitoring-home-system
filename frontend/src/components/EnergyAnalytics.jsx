import React from 'react';
import styled from 'styled-components';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';

const AnalyticsContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 20px;
  color: white;
`;

const Row = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
`;

const Section = styled.div`
  background-color: #1e293b; /* Match login form background */
  padding: 20px;
  border-radius: 10px;
  flex: 1;
  min-width: 300px;
`;

const Title = styled.h3`
  margin: 0 0 20px 0;
  font-size: 18px;
`;

const StatList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 10px;
`;

const StatItem = styled.div`
  display: flex;
  justify-content: space-between;
  font-size: 14px;
`;

const StatLabel = styled.span`
  color: #dbeafe; /* Match label color */
`;

const StatValue = styled.span`
  color: #10b981; /* Green accent */
`;

const SuggestionsList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 14px;
  color: #dbeafe; /* Match label color */
`;

const SuggestionItem = styled.li`
  margin-bottom: 10px;
`;

const PieChartContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center; /* Center the pie chart */
`;

const COLORS = ['#10b981', '#a855f7', '#4ade80'];

// Custom label renderer for external labels with lines
const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index }) => {
  const RADIAN = Math.PI / 180;
  const radius = outerRadius + 20; // Position labels outside the pie chart
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="#dbeafe" // Match dashboard text color
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
      fontSize={12}
    >
      {`${(percent * 100).toFixed(0)}`}
    </text>
  );
};

function EnergyAnalytics() {
  // Mock data for charts
  const usageTrendsData = [
    { time: 'Mon', current: 30, previous: 25 },
    { time: 'Tue', current: 35, previous: 28 },
    { time: 'Wed', current: 40, previous: 30 },
    { time: 'Thu', current: 45, previous: 32 },
    { time: 'Fri', current: 42, previous: 29 },
  ];

  const comparativeData = [
    { name: 'Living Room', current: 20, previous: 15 },
    { name: 'Kitchen', current: 15, previous: 10 },
    { name: 'Bedroom', current: 10, previous: 8 },
  ];

  const energyDistributionData = [
    { name: 'Lighting', value: 40 },
    { name: 'Heating', value: 30 },
    { name: 'Appliances', value: 30 },
  ];

  return (
    <AnalyticsContainer>
      {/* Top Row: Energy Usage, Usage Trends, Optimization Suggestions */}
      <Row>
        <Section>
          <Title>Energy Usage</Title>
          <StatList>
            <StatItem>
              <StatLabel>Daily</StatLabel>
              <StatValue>45 kWh</StatValue>
            </StatItem>
            <StatItem>
              <StatLabel>Weekly</StatLabel>
              <StatValue>310 kWh</StatValue>
            </StatItem>
            <StatItem>
              <StatLabel>Monthly</StatLabel>
              <StatValue>1240 kWh</StatValue>
            </StatItem>
            <StatItem>
              <StatLabel>Total Consumption</StatLabel>
              <StatValue>1240 kWh</StatValue>
            </StatItem>
            <StatItem>
              <StatLabel>Peak Usage</StatLabel>
              <StatValue>60 kWh</StatValue>
            </StatItem>
            <StatItem>
              <StatLabel>Cost</StatLabel>
              <StatValue>$150</StatValue>
            </StatItem>
          </StatList>
        </Section>
        <Section>
          <Title>Usage Trends</Title>
          <LineChart width={300} height={200} data={usageTrendsData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#64748b" />
            <XAxis dataKey="time" stroke="#dbeafe" />
            <YAxis stroke="#dbeafe" />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="current" stroke="#10b981" name="Current" />
            <Line type="monotone" dataKey="previous" stroke="#a855f7" name="Previous" />
          </LineChart>
        </Section>
        <Section>
          <Title>Optimization Suggestions</Title>
          <SuggestionsList>
            <SuggestionItem>Consider switching to LED lighting to reduce consumption.</SuggestionItem>
            <SuggestionItem>Optimize heating schedule to balance comfort and efficiency.</SuggestionItem>
            <SuggestionItem>Monitor standby power usage of devices.</SuggestionItem>
          </SuggestionsList>
        </Section>
      </Row>

      {/* Bottom Row: Energy Distribution, Comparative Analysis */}
      <Row>
        <Section>
          <Title>Energy Distribution</Title>
          <PieChartContainer>
            <PieChart width={250} height={250}>
              <Pie
                data={energyDistributionData}
                cx={125}
                cy={140} // Move the pie chart down by increasing cy
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
                label={renderCustomizedLabel} // Use custom label renderer
                labelLine={true} // Show connecting lines
              >
                {energyDistributionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value, name) => [`${value}%`, name]} />
            </PieChart>
          </PieChartContainer>
        </Section>
        <Section>
          <Title>Comparative Analysis</Title>
          <BarChart width={300} height={200} data={comparativeData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#64748b" />
            <XAxis dataKey="name" stroke="#dbeafe" />
            <YAxis stroke="#dbeafe" />
            <Tooltip />
            <Legend />
            <Bar dataKey="current" fill="#10b981" name="Current" />
            <Bar dataKey="previous" fill="#a855f7" name="Previous" />
          </BarChart>
        </Section>
      </Row>
    </AnalyticsContainer>
  );
}

export default EnergyAnalytics;