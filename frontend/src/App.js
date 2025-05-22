import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import Login from './components/Login';
import Signup from './components/Signup';
import styled from 'styled-components';
import { checkAuth } from './api/api';
import AdminDeviceManager from './components/AdminDeviceManager';

const AppContainer = styled.div`
  font-family: 'Roboto', sans-serif;
  background-color: #0f172a; /* Dark background */
  min-height: 100vh;
  color: white; /* Default text color */
  display: flex;
  flex-direction: column;
`;

const ContentWrapper = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
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

const NotFoundContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #0f172a;
  color: white;
  flex-direction: column;
`;

const NotFoundTitle = styled.h2`
  font-size: 24px;
  margin-bottom: 20px;
`;

const NotFoundLink = styled.a`
  color: #10b981;
  text-decoration: none;
  font-size: 16px;
  &:hover {
    text-decoration: underline;
  }
`;

// PrivateRoute component to protect Dashboard
const PrivateRoute = ({ children }) => {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const verifyAuth = async () => {
      try {
        const authResponse = await checkAuth();
        setIsAuthenticated(authResponse.data.is_authenticated);
      } catch (err) {
        console.error('Auth check failed:', err.response?.data?.detail || err.message);
        setError('Failed to verify authentication. Please try again.');
        setIsAuthenticated(false);
      }
    };
    verifyAuth();
  }, []);

  if (isAuthenticated === null) {
    return (
      <LoadingContainer>
        <LoadingSpinner />
      </LoadingContainer>
    );
  }

  if (error) {
    return (
      <NotFoundContainer>
        <NotFoundTitle>{error}</NotFoundTitle>
        <NotFoundLink href="/login">Go to Login</NotFoundLink>
      </NotFoundContainer>
    );
  }

  if (!isAuthenticated) {
    navigate('/login');
    return null;
  }

  return children;
};

// NotFound component for 404 pages
const NotFound = () => (
  <NotFoundContainer>
    <NotFoundTitle>404 - Page Not Found</NotFoundTitle>
    <NotFoundLink href="/login">Go to Login</NotFoundLink>
  </NotFoundContainer>
);

function App() {
  return (
    <AppContainer>
      <BrowserRouter>
        <ContentWrapper>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route
              path="/dashboard"
              element={
                <PrivateRoute>
                  <Dashboard />
                </PrivateRoute>
              }
            />
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <Dashboard />
                </PrivateRoute>
              }
            />
            <Route
              path="/admin"
              element={<AdminDeviceManager />}
            />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </ContentWrapper>
      </BrowserRouter>
    </AppContainer>
  );
}

export default App;
