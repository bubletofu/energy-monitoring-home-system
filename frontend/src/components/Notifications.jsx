// // import React from 'react';
// // import styled from 'styled-components';

// // const NotificationCard = styled.div`
// //   background-color: white;
// //   border-radius: 10px;
// //   padding: 15px;
// //   margin-bottom: 15px;
// //   box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
// //   display: flex;
// //   justify-content: space-between;
// //   align-items: center;
// // `;

// // const NotificationText = styled.div``;

// // const NotificationTitle = styled.h4`
// //   margin: 0 0 5px 0;
// //   color: #e11d48;
// //   font-size: 16px;
// // `;

// // const NotificationTime = styled.p`
// //   color: #64748b;
// //   font-size: 12px;
// //   margin: 0;
// // `;

// // const ViewDetails = styled.a`
// //   color: #1e3a8a;
// //   text-decoration: none;
// //   font-size: 14px;
// // `;

// // function Notifications() {
// //   return (
// //     <>
// //       <NotificationCard>
// //         <NotificationText>
// //           <NotificationTitle>High usage detected in Kitchen</NotificationTitle>
// //           <NotificationTime>Today, 10:30 AM</NotificationTime>
// //         </NotificationText>
// //         <ViewDetails href="#">View Details</ViewDetails>
// //       </NotificationCard>
// //       <NotificationCard>
// //         <NotificationText>
// //           <NotificationTitle>Unusual surge in Living Room</NotificationTitle>
// //           <NotificationTime>Yesterday, 4:00 PM</NotificationTime>
// //         </NotificationText>
// //         <ViewDetails href="#">View Details</ViewDetails>
// //       </NotificationCard>
// //       <NotificationCard>
// //         <NotificationText>
// //           <NotificationTitle>Smart Thermostat updated successfully</NotificationTitle>
// //           <NotificationTime>Today, 9:00 AM</NotificationTime>
// //         </NotificationText>
// //         <ViewDetails href="#">View Details</ViewDetails>
// //       </NotificationCard>
// //     </>
// //   );
// // }

// // export default Notifications;

// import React from 'react';
// import styled from 'styled-components';

// const NotificationsContainer = styled.div`
//   background-color: #1e293b; /* Match login form background */
//   padding: 20px;
//   border-radius: 10px;
//   flex: 1;
//   min-width: 300px;
//   color: white;
// `;

// const Title = styled.h3`
//   margin: 0 0 10px 0;
//   font-size: 18px;
// `;

// const NotificationList = styled.ul`
//   list-style: none;
//   padding: 0;
//   margin: 0;
// `;

// const NotificationItem = styled.li`
//   background-color: #334155; /* Match input background */
//   padding: 10px;
//   margin-bottom: 10px;
//   border-radius: 5px;
//   font-size: 14px;
// `;

// function Notifications() {
//   return (
//     <NotificationsContainer>
//       <Title>Notifications</Title>
//       <NotificationList>
//         <NotificationItem>Device 1 reported high energy usage at 09:00.</NotificationItem>
//         <NotificationItem>Device 2 went offline at 08:30.</NotificationItem>
//         <NotificationItem>System update available.</NotificationItem>
//       </NotificationList>
//     </NotificationsContainer>
//   );
// }

// export default Notifications;

import React, { useState } from 'react'; // Add useState import
import styled from 'styled-components';

const NotificationsContainer = styled.div`
  background-color: #1e293b; /* Match login form background */
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

const Section = styled.div`
  margin-bottom: 20px;
`;

const NotificationList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 10px;
`;

const NotificationItem = styled.div`
  background-color: #334155; /* Match input background */
  padding: 10px;
  border-radius: 5px;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const NotificationText = styled.p`
  margin: 0;
  font-size: 14px;
`;

const ViewButton = styled.button`
  background-color: transparent;
  border: 1px solid #10b981; /* Green accent */
  color: #10b981;
  padding: 5px 10px;
  border-radius: 20px;
  cursor: pointer;
  &:hover {
    background-color: #10b981;
    color: white;
  }
`;

const ToggleSwitch = styled.label`
  position: relative;
  display: inline-block;
  width: 60px;
  height: 34px;
`;

const ToggleInput = styled.input`
  opacity: 0;
  width: 0;
  height: 0;
  &:checked + .slider {
    background-color: #10b981; /* Green accent */
  }
  &:checked + .slider:before {
    transform: translateX(26px);
  }
`;

const Slider = styled.span`
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #64748b;
  transition: 0.4s;
  border-radius: 34px;
  &:before {
    position: absolute;
    content: '';
    height: 26px;
    width: 26px;
    left: 4px;
    bottom: 4px;
    background-color: white;
    transition: 0.4s;
    border-radius: 50%;
  }
`;

function Notifications() {
  const [emailNotifications, setEmailNotifications] = useState(false);
  const [smsAlerts, setSmsAlerts] = useState(false);

  return (
    <NotificationsContainer>
      <Section>
        <Title>Energy Consumption Alerts</Title>
        <NotificationList>
          <NotificationItem>
            <NotificationText>⚡ High usage detected in Kitchen - Today, 10:30 AM</NotificationText>
            <ViewButton>View Details</ViewButton>
          </NotificationItem>
          <NotificationItem>
            <NotificationText>⚡ Unusual surge in Living Room - Yesterday, 4:00 PM</NotificationText>
            <ViewButton>View Details</ViewButton>
          </NotificationItem>
        </NotificationList>
      </Section>
      <Section>
        <Title>Device Status Updates</Title>
        <NotificationList>
          <NotificationItem>
            <NotificationText>✅ Smart Thermostat updated successfully - Today, 9:00 AM</NotificationText>
            <ViewButton>View Details</ViewButton>
          </NotificationItem>
        </NotificationList>
      </Section>
      <Section>
        <Title>Anomalies & Reminders</Title>
        <NotificationList>
          <NotificationItem>
            <NotificationText>⚠️ Anomaly detected in energy usage - 2 days ago, 3:45 PM</NotificationText>
            <ViewButton>View Details</ViewButton>
          </NotificationItem>
        </NotificationList>
      </Section>
      <Section>
        <Title>Manage Alert Settings</Title>
        <NotificationList>
          <NotificationItem>
            <NotificationText>Enable Email Notifications</NotificationText>
            <ToggleSwitch>
              <ToggleInput
                type="checkbox"
                checked={emailNotifications}
                onChange={() => setEmailNotifications(!emailNotifications)}
              />
              <Slider className="slider" />
            </ToggleSwitch>
          </NotificationItem>
          <NotificationItem>
            <NotificationText>Receive SMS Alerts</NotificationText>
            <ToggleSwitch>
              <ToggleInput
                type="checkbox"
                checked={smsAlerts}
                onChange={() => setSmsAlerts(!smsAlerts)}
              />
              <Slider className="slider" />
            </ToggleSwitch>
          </NotificationItem>
        </NotificationList>
      </Section>
    </NotificationsContainer>
  );
}

export default Notifications;