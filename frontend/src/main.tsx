// In src/main.tsx (or whichever is your entry file)
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App'; // Make sure this path is correct

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App /> 
  </React.StrictMode>
);