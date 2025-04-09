// import React, { useState } from 'react';
// import { useNavigate, Link } from 'react-router-dom';
// import styled from 'styled-components';
// import { createUser, login } from '../api/api'; // Add login import
// import backgroundImage from '../assets/background.jpg';

// const SignupContainer = styled.div`
//   display: flex;
//   flex-direction: column;
//   justify-content: space-between;
//   align-items: center;
//   min-height: 100vh;
//   background-image: url(${backgroundImage});
//   background-size: cover;
//   background-position: center;
//   background-repeat: no-repeat;
//   position: relative;
// `;

// const Overlay = styled.div`
//   position: absolute;
//   top: 0;
//   left: 0;
//   width: 100%;
//   height: 100%;
//   background-color: rgba(0, 0, 0, 0.5);
// `;

// const Logo = styled.h1`
//   color: white;
//   font-size: 24px;
//   margin: 20px 0;
//   z-index: 1;
// `;

// const FormContainer = styled.div`
//   background-color: #1e293b;
//   opacity: 0.9;
//   padding: 30px;
//   border-radius: 10px;
//   width: 350px;
//   text-align: center;
//   z-index: 1;
// `;

// const Title = styled.h2`
//   color: white;
//   font-size: 24px;
//   margin-bottom: 20px;
// `;

// const Form = styled.form`
//   display: flex;
//   flex-direction: column;
// `;

// const Label = styled.label`
//   color: #dbeafe;
//   font-size: 14px;
//   text-align: left;
//   margin-bottom: 5px;
// `;

// const Input = styled.input`
//   width: 100%;
//   padding: 10px;
//   margin-bottom: 15px;
//   border: 1px solid #64748b;
//   border-radius: 20px;
//   background-color: #334155;
//   color: white;
//   font-size: 14px;
//   &:focus {
//     outline: none;
//     border-color: #10b981;
//   }
// `;

// const Button = styled.button`
//   background-color: #10b981;
//   color: white;
//   border: none;
//   padding: 10px;
//   border-radius: 20px;
//   cursor: pointer;
//   font-size: 16px;
//   margin-top: 10px;
//   &:hover {
//     background-color: #059669;
//   }
// `;

// const LinksContainer = styled.div`
//   display: flex;
//   justify-content: center;
//   margin-top: 15px;
// `;

// const LinkStyled = styled(Link)`
//   color: #10b981;
//   font-size: 12px;
//   text-decoration: none;
//   &:hover {
//     text-decoration: underline;
//   }
// `;

// const ErrorMessage = styled.p`
//   color: #e11d48;
//   font-size: 14px;
//   margin-top: 10px;
// `;

// const Footer = styled.footer`
//   color: white;
//   font-size: 12px;
//   text-align: center;
//   padding: 10px;
//   z-index: 1;
// `;

// const FooterLink = styled.a`
//   color: #10b981;
//   text-decoration: none;
//   &:hover {
//     text-decoration: underline;
//   }
// `;

// function Signup() {
//   const [formData, setFormData] = useState({ username: '', email: '', password: '' });
//   const [error, setError] = useState('');
//   const navigate = useNavigate();

//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     try {
//       // Step 1: Create the user
//       const signupResponse = await createUser(formData);
//       console.log('Signup successful:', signupResponse.data);

//       // Step 2: Automatically log the user in
//       const loginCredentials = {
//         username: formData.username,
//         password: formData.password,
//       };
//       const loginResponse = await login(loginCredentials);
//       if (loginResponse.data.success) {
//         localStorage.setItem('token', loginResponse.data.token);
//         setError('');
//         // Step 3: Redirect to dashboard
//         navigate('/');
//       } else {
//         setError('Auto-login failed. Please log in manually.');
//         navigate('/login');
//       }
//     } catch (error) {
//       if (error.response && error.response.data.error) {
//         setError(error.response.data.error);
//       } else {
//         setError('Signup failed. Check server status.');
//       }
//       console.error('Signup error:', error);
//     }
//   };

//   return (
//     <SignupContainer>
//       <Overlay />
//       <Logo>EcoEnergy</Logo>
//       <FormContainer>
//         <Title>Sign Up</Title>
//         <Form onSubmit={handleSubmit}>
//           <Label>Username</Label>
//           <Input
//             type="text"
//             placeholder="Username"
//             value={formData.username}
//             onChange={(e) => setFormData({ ...formData, username: e.target.value })}
//             required
//           />
//           <Label>Email</Label>
//           <Input
//             type="email"
//             placeholder="Email"
//             value={formData.email}
//             onChange={(e) => setFormData({ ...formData, email: e.target.value })}
//             required
//           />
//           <Label>Password</Label>
//           <Input
//             type="password"
//             placeholder="Password"
//             value={formData.password}
//             onChange={(e) => setFormData({ ...formData, password: e.target.value })}
//             required
//           />
//           <Button type="submit">Sign Up</Button>
//           {error && <ErrorMessage>{error}</ErrorMessage>}
//         </Form>
//         <LinksContainer>
//           <LinkStyled to="/login">Already have an account? Log in</LinkStyled>
//         </LinksContainer>
//       </FormContainer>
//       <Footer>
//         © 2025 EcoEnergy, All Rights Reserved. <br />
//         Contact us at <FooterLink href="mailto:support@ecoenergy.com">support@ecoenergy.com</FooterLink>
//       </Footer>
//     </SignupContainer>
//   );
// }

// export default Signup;

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import styled from 'styled-components';
import { createUser, login } from '../api/api'; // Add login import
import backgroundImage from '../assets/background.jpg';

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
  justify-content: center;
  margin-top: 15px;
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

function Signup() {
  const [formData, setFormData] = useState({ username: '', email: '', password: '' });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // Step 1: Create the user
      const signupResponse = await createUser(formData);
      console.log('Signup successful:', signupResponse.data);

      // Step 2: Automatically log the user in
      const loginCredentials = {
        username: formData.username,
        password: formData.password,
      };
      const loginResponse = await login(loginCredentials);
      if (loginResponse.data.success) {
        localStorage.setItem('token', loginResponse.data.token);
        setError('');
        // Step 3: Redirect to dashboard
        navigate('/');
      } else {
        setError('Auto-login failed. Please log in manually.');
        navigate('/login');
      }
    } catch (error) {
      if (error.response && error.response.data.error) {
        setError(error.response.data.error);
      } else {
        setError('Signup failed. Check server status.');
      }
      console.error('Signup error:', error);
    }
  };

  return (
    <SignupContainer>
      <Overlay />
      <Logo>EcoEnergy</Logo>
      <FormContainer>
        <Title>Sign Up</Title>
        <Form onSubmit={handleSubmit}>
          <Label>Username</Label>
          <Input
            type="text"
            placeholder="Username"
            value={formData.username}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            required
          />
          <Label>Email</Label>
          <Input
            type="email"
            placeholder="Email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
          />
          <Label>Password</Label>
          <Input
            type="password"
            placeholder="Password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required
          />
          <Button type="submit">Sign Up</Button>
          {error && <ErrorMessage>{error}</ErrorMessage>}
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