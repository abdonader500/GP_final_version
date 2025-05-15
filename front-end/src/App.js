import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Box, CssBaseline, CircularProgress } from '@mui/material';
import Header from './components/Header';
import Home from './pages/Home';
import Pricing from './pages/Pricing';
import Visualizations from './pages/Visualizations';
import SalesStrategy from './pages/SalesStrategy';
import Login from './pages/Login';
import UserDashboard from './pages/UserDashboard.js';
import ProtectedRoute from './components/ProtectedRoute';
import UserManagement from './pages/Admin/UserManagement.js';
import DataUpload from './components/DataUpload'; // Import the DataUpload component

function App() {
  const [authChecked, setAuthChecked] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check authentication status on mount
  useEffect(() => {
    const token = sessionStorage.getItem('token');
    setIsAuthenticated(!!token);
    setAuthChecked(true);
  }, []);

  // Show loading while checking authentication
  if (!authChecked) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Router>
      <CssBaseline />
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
          bgcolor: 'background.default',
        }}
      >
        {/* Only show header when authenticated */}
        {isAuthenticated && (
          <Routes>
            <Route path="/login" element={null} />
            <Route path="*" element={<Header />} />
          </Routes>
        )}

        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Routes>
            {/* Root path - home if authenticated, login if not */}
            <Route 
              path="/" 
              element={
                isAuthenticated ? 
                  <Home /> : 
                  <Navigate to="/login" replace />
              } 
            />
            
            {/* Login route */}
            <Route 
              path="/login" 
              element={
                isAuthenticated ? 
                  <Navigate to="/" replace /> : 
                  <Login setIsAuthenticated={setIsAuthenticated} />
              } 
            />
            
            {/* Protected Routes */}
            <Route 
              path="/admin/users" 
              element={
                <ProtectedRoute role="admin">
                  <UserManagement />
                </ProtectedRoute>
              } 
            />
            
            {/* Data Upload Route */}
            <Route 
              path="/admin/upload" 
              element={
                <ProtectedRoute role="admin">
                  <DataUpload />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/pricing" 
              element={
                <ProtectedRoute>
                  <Pricing />
                </ProtectedRoute>
              }
            />
            
            <Route 
              path="/visualizations" 
              element={
                <ProtectedRoute>
                  <Visualizations />
                </ProtectedRoute>
              }
            />
            
            {/* Sales Strategy Route */}
            <Route 
              path="/sales-strategy" 
              element={
                <ProtectedRoute>
                  <SalesStrategy />
                </ProtectedRoute>
              }
            />
            
            {/* Fallback redirect */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Box>
      </Box>
    </Router>
  );
}

export default App;