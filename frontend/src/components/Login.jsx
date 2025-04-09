import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom'; // Add Link import
import styled from 'styled-components';
import { login } from '../api/api';
import backgroundImage from '../assets/background.jpg';

const LoginContainer = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  min-height: 100vh;
  background-image: url(${backgroundImage});
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  position: relative;
`;

const Overlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
`;

const Logo = styled.h1`
  color: white;
  font-size: 24px;
  margin: 20px 0;
  z-index: 1;
`;

const FormContainer = styled.div`
  background-color: #1e293b;
  opacity: 0.9;
  padding: 30px;
  border-radius: 10px;
  width: 350px;
  text-align: center;
  z-index: 1;
`;

const Title = styled.h2`
  color: white;
  font-size: 24px;
  margin-bottom: 20px;
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
`;

const Label = styled.label`
  color: #dbeafe;
  font-size: 14px;
  text-align: left;
  margin-bottom: 5px;
`;

const Input = styled.input`
  width: 100%;
  padding: 10px;
  margin-bottom: 15px;
  border: 1px solid #64748b;
  border-radius: 20px;
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
  border-radius: 20px;
  cursor: pointer;
  font-size: 16px;
  margin-top: 10px;
  &:hover {
    background-color: #059669;
  }
`;

const LinksContainer = styled.div`
  display: flex;
  justify-content: space-between;
  margin-top: 15px;
`;

const LinkStyled = styled(Link)` // Changed from 'a' to 'Link'
  color: #10b981;
  font-size: 12px;
  text-decoration: none;
  &:hover {
    text-decoration: underline;
  }
`;

const ErrorMessage = styled.p`
  color: #e11d48;
  font-size: 14px;
  margin-top: 10px;
`;

const Footer = styled.footer`
  color: white;
  font-size: 12px;
  text-align: center;
  padding: 10px;
  z-index: 1;
`;

const FooterLink = styled.a`
  color: #10b981;
  text-decoration: none;
  &:hover {
    text-decoration: underline;
  }
`;

function Login() {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await login(credentials);
      if (response.data.success) {
        localStorage.setItem('token', response.data.token);
        setError('');
        navigate('/');
      } else {
        setError('Login failed. Check your credentials.');
      }
    } catch (error) {
      setError('Login failed. Check server status or credentials.');
      console.error('Login error:', error);
    }
  };

  return (
    <LoginContainer>
      <Overlay />
      <Logo>EcoEnergy</Logo>
      <FormContainer>
        <Title>Welcome Back</Title>
        <Form onSubmit={handleSubmit}>
          <Label>Email</Label>
          <Input
            type="text"
            placeholder="Email"
            value={credentials.username}
            onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
          />
          <Label>Password</Label>
          <Input
            type="password"
            placeholder="Password"
            value={credentials.password}
            onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
          />
          <Button type="submit">Login</Button>
          {error && <ErrorMessage>{error}</ErrorMessage>}
        </Form>
        <LinksContainer>
          <LinkStyled to="#">Forgot Password?</LinkStyled>
          <LinkStyled to="/signup">Create Account</LinkStyled> {/* Updated to navigate */}
        </LinksContainer>
      </FormContainer>
      <Footer>
        © 2025 EcoEnergy, All Rights Reserved. <br />
        Contact us at <FooterLink href="mailto:support@ecoenergy.com">support@ecoenergy.com</FooterLink>
      </Footer>
    </LoginContainer>
  );
}

export default Login;