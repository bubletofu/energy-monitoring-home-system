import React from 'react';
import styled from 'styled-components';
import EnergyConsumption from './EnergyConsumption';
import DeviceControl from './DeviceControl';
import Notifications from './Notifications';

const MainStyled = styled.main`
  display: grid;
  gap: 20px;
`;

const SectionTitle = styled.h2`
  color: #1e3a8a;
  font-size: 20px;
  margin-bottom: 15px;
`;

function MainContent() {
  return (
    <MainStyled>
      <div>
        <SectionTitle>Real-Time Energy Consumption</SectionTitle>
        <EnergyConsumption />
      </div>
      <div>
        <SectionTitle>Control Your Devices</SectionTitle>
        <DeviceControl />
      </div>
      <div>
        <SectionTitle>Notifications</SectionTitle>
        <Notifications />
      </div>
    </MainStyled>
  );
}

export default MainContent;