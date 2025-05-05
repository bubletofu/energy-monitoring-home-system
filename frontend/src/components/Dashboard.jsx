import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import EnergyConsumption from './EnergyConsumption';
import DeviceControl from './DeviceControl';
import Notifications from './Notifications';
import EnergyAnalytics from './EnergyAnalytics';
import { checkAuth, logout, getCurrentUser } from '../api/api';

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

const LoadingContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #0f172a;
  color: white;
`;

const LoadingSpinner = styled.div`
  border: 4px solid #10b981;
  border-top: 4px solid transparent;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

function Dashboard() {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const verifyAuth = async () => {
      setLoading(true);
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
        console.error('Auth check failed:', error.response?.data?.detail || error.message);
        navigate('/login');
      } finally {
        setLoading(false);
      }
    };
    verifyAuth();
  }, [navigate]);

  const handleLogout = async () => {
    try {
      const response = await logout();
      console.log(response.data.message);
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token'); // Remove refresh token if exists
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error.response?.data?.detail || error.message);
      // Proceed with logout even if API call fails
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      navigate('/login');
    }
  };

  if (loading) {
    return (
      <LoadingContainer>
        <LoadingSpinner />
      </LoadingContainer>
    );
  }

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
