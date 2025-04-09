import React from 'react';
import styled from 'styled-components';

const SidebarStyled = styled.aside`
  width: 220px;
  background-color: #1e293b;
  color: white;
  padding: 20px;
  height: calc(100vh - 60px);
`;

const NavList = styled.ul`
  list-style: none;
  padding: 0;
`;

const NavItem = styled.li`
  padding: 15px 10px;
  cursor: pointer;
  font-size: 16px;
  &:hover {
    background-color: #334155;
    border-radius: 5px;
  }
`;

function Sidebar() {
  return (
    <SidebarStyled>
      <NavList>
        <NavItem>Dashboard</NavItem>
        <NavItem>Device Control</NavItem>
        <NavItem>Energy Analytics</NavItem>
        <NavItem>Notifications</NavItem>
        <NavItem>Settings</NavItem>
      </NavList>
    </SidebarStyled>
  );
}

export default Sidebar;