// // // import React from 'react';
// // // import { BrowserRouter, Routes, Route } from 'react-router-dom';
// // // import Dashboard from './components/Dashboard';
// // // import Login from './components/Login';
// // // import styled from 'styled-components';

// // // const AppContainer = styled.div`
// // //   font-family: 'Roboto', sans-serif;
// // //   background-color: #eef2f5;
// // //   min-height: 100vh;
// // // `;

// // // function App() {
// // //   return (
// // //     <AppContainer>
// // //       <BrowserRouter>
// // //         <Routes>
// // //           <Route path="/login" element={<Login />} />
// // //           <Route path="/" element={<Dashboard />} />
// // //         </Routes>
// // //       </BrowserRouter>
// // //     </AppContainer>
// // //   );
// // // }

// // // export default App;

// // import React from 'react';
// // import { BrowserRouter, Routes, Route } from 'react-router-dom';
// // import Dashboard from './components/Dashboard';
// // import Login from './components/Login';
// // import Signup from './components/Signup'; // New import
// // import styled from 'styled-components';

// // const AppContainer = styled.div`
// //   font-family: 'Roboto', sans-serif;
// //   background-color: #eef2f5;
// //   min-height: 100vh;
// // `;

// // function App() {
// //   return (
// //     <AppContainer>
// //       <BrowserRouter>
// //         <Routes>
// //           <Route path="/login" element={<Login />} />
// //           <Route path="/signup" element={<Signup />} /> {/* New route */}
// //           <Route path="/" element={<Dashboard />} />
// //         </Routes>
// //       </BrowserRouter>
// //     </AppContainer>
// //   );
// // }

// // export default App;

// import React from 'react';
// import { BrowserRouter, Routes, Route } from 'react-router-dom';
// import Dashboard from './components/Dashboard';
// import Login from './components/Login';
// import Signup from './components/Signup';
// import styled from 'styled-components';

// const AppContainer = styled.div`
//   font-family: 'Roboto', sans-serif;
//   background-color: #0f172a; /* Dark background to match login */
//   min-height: 100vh;
//   color: white; /* Default text color */
// `;

// function App() {
//   return (
//     <AppContainer>
//       <BrowserRouter>
//         <Routes>
//           <Route path="/login" element={<Login />} />
//           <Route path="/signup" element={<Signup />} />
//           <Route path="/" element={<Dashboard />} />
//         </Routes>
//       </BrowserRouter>
//     </AppContainer>
//   );
// }

// export default App;

import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import Login from './components/Login';
import Signup from './components/Signup';
import styled from 'styled-components';

const AppContainer = styled.div`
  font-family: 'Roboto', sans-serif;
  background-color: #0f172a; /* Dark background */
  min-height: 100vh;
  color: white; /* Default text color */
`;

function App() {
  return (
    <AppContainer>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </AppContainer>
  );
}

export default App;