import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import EnergyConsumption from './EnergyConsumption';
import DeviceControl from './DeviceControl';
import Notifications from './Notifications';
import EnergyAnalytics from './EnergyAnalytics';

// Mock data for testing without a backend
const mockUser = {
  id: 1,
  username: 'mockuser',
  email: 'mockuser@example.com',
};

// Mock API functions
const checkAuth = async () => {
  console.log('Mock check-auth');
  return {
    data: {
      is_authenticated: true,
      user: mockUser,
    },
  };
};

const logout = async () => {
  console.log('Mock logout');
  return { data: { message: 'Đăng xuất thành công' } };
};

const getCurrentUser = async () => {
  console.log('Mock getCurrentUser');
  return { data: mockUser };
};

// Styled components (unchanged)
const DashboardContainer = styled.div`
  display: flex;
  flex-direction: column;
  min-height: 100vh;
`;

const Header = styled.header`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background-color: #1e293b;
  color: white;
`;

const Logo = styled.h1`
  font-size: 24px;
  margin: 0;
`;

const NavLinks = styled.div`
  display: flex;
  gap: 20px;
`;

const NavLink = styled.a`
  color: white;
  text-decoration: none;
  font-size: 16px;
  &:hover {
    color: #10b981;
  }
`;

const MainContent = styled.div`
  flex: 1;
  padding: 20px;
  background-color: #0f172a;
`;

const ContentArea = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
`;

const Footer = styled.footer`
  padding: 10px 20px;
  background-color: #1e293b;
  color: white;
  display: flex;
  justify-content: space-between;
  font-size: 12px;
`;

const FooterLink = styled.a`
  color: #10b981;
  text-decoration: none;
  &:hover {
    text-decoration: underline;
  }
`;

function Dashboard() {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const verifyAuth = async () => {
      try {
        const authResponse = await checkAuth();
        if (authResponse.data.is_authenticated) {
          setIsAuthenticated(true);
          const userResponse = await getCurrentUser();
          setUser(userResponse.data);
        } else {
          navigate('/login');
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        navigate('/login');
      }
    };
    verifyAuth();
  }, [navigate]);

  const handleLogout = async () => {
    try {
      await logout();
      localStorage.removeItem('token');
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  if (!isAuthenticated) return null;

  return (
    <DashboardContainer>
      <Header>
        <Logo>EcoEnergy</Logo>
        <NavLinks>
          <NavLink
            href="#"
            onClick={() => setActiveTab('Dashboard')}
            style={activeTab === 'Dashboard' ? { color: '#10b981' } : {}}
          >
            Dashboard
          </NavLink>
          <NavLink
            href="#"
            onClick={() => setActiveTab('Device Control')}
            style={activeTab === 'Device Control' ? { color: '#10b981' } : {}}
          >
            Device Control
          </NavLink>
          <NavLink
            href="#"
            onClick={() => setActiveTab('Energy Analytics')}
            style={activeTab === 'Energy Analytics' ? { color: '#10b981' } : {}}
          >
            Energy Analytics
          </NavLink>
          <NavLink
            href="#"
            onClick={() => setActiveTab('Notifications')}
            style={activeTab === 'Notifications' ? { color: '#10b981' } : {}}
          >
            Notifications
          </NavLink>
          <NavLink
            href="#"
            onClick={() => setActiveTab('Settings')}
            style={activeTab === 'Settings' ? { color: '#10b981' } : {}}
          >
            Settings
          </NavLink>
          <NavLink href="#" onClick={handleLogout}>
            Logout
          </NavLink>
        </NavLinks>
      </Header>
      <MainContent>
        {activeTab === 'Dashboard' && (
          <ContentArea>
            <EnergyConsumption />
            <QuickLinks />
          </ContentArea>
        )}
        {activeTab === 'Device Control' && <DeviceControl />}
        {activeTab === 'Energy Analytics' && <EnergyAnalytics />}
        {activeTab === 'Notifications' && <Notifications />}
        {activeTab === 'Settings' && <div>Settings Page (To be implemented)</div>}
      </MainContent>
      <Footer>
        <span>© 2025 EcoEnergy, All Rights Reserved.</span>
        <div>
          <FooterLink href="#">Privacy Policy</FooterLink> |{' '}
          <FooterLink href="#">Terms of Service</FooterLink> |{' '}
          <FooterLink href="mailto:support@ecoenergy.com">Contact Us</FooterLink>
        </div>
      </Footer>
    </DashboardContainer>
  );
}

// Quick Links Component (unchanged)
const QuickLinksContainer = styled.div`
  background-color: #1e293b;
  padding: 20px;
  border-radius: 10px;
  flex: 1;
  min-width: 300px;
  color: white;
`;

const QuickLinksTitle = styled.h3`
  margin: 0 0 20px 0;
  font-size: 18px;
`;

const QuickLink = styled.a`
  display: block;
  color: #dbeafe;
  text-decoration: none;
  margin-bottom: 10px;
  &:hover {
    color: #10b981;
  }
`;

function QuickLinks() {
  return (
    <QuickLinksContainer>
      <QuickLinksTitle>Quick Links</QuickLinksTitle>
      <QuickLink href="#">View Energy Reports</QuickLink>
      <QuickLink href="#">Manage Devices</QuickLink>
      <QuickLink href="#">Set Consumption Alerts</QuickLink>
      <QuickLink href="#">Billing Information</QuickLink>
    </QuickLinksContainer>
  );
}

export default Dashboard;