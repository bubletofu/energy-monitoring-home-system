import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import styled from 'styled-components';
import { register, login } from '../api/api';
import backgroundImage from '../assets/background.jpg';

// Styled Components
const SignupContainer = styled.div`
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
  background-color: rgba(30, 41, 59, 0.9);
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
  align-items: center;
  width: 100%;
`;

const Label = styled.label`
  color: #dbeafe;
  font-size: 14px;
  text-align: left;
  margin-bottom: 5px;
  width: 100%;
  max-width: 300px;
`;

const Input = styled.input`
  width: 100%;
  max-width: 300px;
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
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  max-width: 300px;
  &:hover {
    background-color: #059669;
  }
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const LinksContainer = styled.div`
  display: flex;
  justify-content: center;
  margin-top: 15px;
  width: 100%;
`;

const LinkStyled = styled(Link)`
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
  width: 100%;
  max-width: 300px;
`;

const SuccessMessage = styled.p`
  color: #10b981;
  font-size: 14px;
  margin-top: 10px;
  width: 100%;
  max-width: 300px;
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

const LoadingSpinner = styled.div`
  border: 2px solid white;
  border-top: 2px solid transparent;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;
  margin-left: 10px;

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

function Signup() {
  const [formData, setFormData] = useState({ username: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const validateForm = () => {
    if (!formData.username.trim()) {
      setError('Username is required');
      return false;
    }
    if (!formData.email.trim()) {
      setError('Email is required');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setError('Please enter a valid email address');
      return false;
    }
    if (!formData.password) {
      setError('Password is required');
      return false;
    }
    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters long');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (!validateForm()) return;

    setLoading(true);
    try {
      // Step 1: Register the user
      const signupResponse = await register(formData);
      console.log('Signup successful:', signupResponse.data);

      // Step 2: Automatically log the user in
      const loginCredentials = new URLSearchParams();
      loginCredentials.append('username', formData.username);
      loginCredentials.append('password', formData.password);

      const loginResponse = await login(loginCredentials);
      if (loginResponse.data.success) {
        localStorage.setItem('token', loginResponse.data.access_token);
        setSuccess('Signup and login successful! Redirecting...');
        setTimeout(() => navigate('/dashboard'), 2000); // Redirect after 2 seconds
      } else {
        setError('Signup succeeded, but auto-login failed. Please log in manually.');
        setTimeout(() => navigate('/login'), 2000);
      }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Signup or login failed. Please try again.';
      setError(errorMessage);
      console.error('Signup or login error:', errorMessage);
      if (error.response?.status === 400 && error.response.data.detail === "Username already registered") {
        setError('Username already registered. Please choose a different one or log in.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <SignupContainer>
      <Overlay />
      <Logo>EcoEnergy</Logo>
      <FormContainer>
        <Title>Sign Up</Title>
        <Form onSubmit={handleSubmit}>
          <Label htmlFor="username">Username</Label>
          <Input
            id="username"
            type="text"
            placeholder="Username"
            value={formData.username}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            aria-label="Enter your username"
            disabled={loading}
          />
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            placeholder="Email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            aria-label="Enter your email"
            disabled={loading}
          />
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            placeholder="Password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            aria-label="Enter your password"
            disabled={loading}
          />
          <Button type="submit" disabled={loading}>
            Sign Up {loading && <LoadingSpinner />}
          </Button>
          {error && <ErrorMessage>{error}</ErrorMessage>}
          {success && <SuccessMessage>{success}</SuccessMessage>}
        </Form>
        <LinksContainer>
          <LinkStyled to="/login">Already have an account? Log in</LinkStyled>
        </LinksContainer>
      </FormContainer>
      <Footer>
        © 2025 EcoEnergy, All Rights Reserved. <br />
        Contact us at <FooterLink href="mailto:support@ecoenergy.com">support@ecoenergy.com</FooterLink>
      </Footer>
    </SignupContainer>
  );
}

export default Signup;
