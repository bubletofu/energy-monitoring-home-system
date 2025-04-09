import React from 'react';
import styled from 'styled-components';

const HeaderStyled = styled.header`
  background-color: #1e3a8a;
  color: white;
  padding: 15px 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
`;

const Logo = styled.h1`
  font-size: 24px;
  margin: 0;
`;

const ContactLink = styled.a`
  color: #dbeafe;
  text-decoration: none;
  font-size: 14px;
`;

const LogoutButton = styled.button`
  background-color: #e11d48;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 5px;
  cursor: pointer;
  &:hover {
    background-color: #c81b3f;
  }
`;

function Header({ onLogout }) {
  return (
    <HeaderStyled>
      <Logo>EcoEnergy</Logo>
      <div>
        <ContactLink href="mailto:support@ecoenergy.com">Contact Us</ContactLink>
        <LogoutButton onClick={onLogout} style={{ marginLeft: '20px' }}>
          Logout
        </LogoutButton>
      </div>
    </HeaderStyled>
  );
}

export default Header;