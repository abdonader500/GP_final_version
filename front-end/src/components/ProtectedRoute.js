import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { CircularProgress, Box } from '@mui/material';

// Protected route component that checks if user is authenticated and has required role
const ProtectedRoute = ({ children, role = null }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [hasRequiredRole, setHasRequiredRole] = useState(false);

  useEffect(() => {
    // Check for authentication and user role
    const checkAuth = () => {
      // Get token and user from localStorage
      const token = sessionStorage.getItem('token');
      const userStr = sessionStorage.getItem('user');
      
      // Set auth state based on token existence
      const authenticated = !!token;
      setIsAuthenticated(authenticated);
      
      // Check role if role restriction is specified
      if (authenticated && role) {
        try {
          const user = JSON.parse(userStr);
          setHasRequiredRole(user.role === role);
        } catch (error) {
          console.error('Error parsing user data:', error);
          setHasRequiredRole(false);
        }
      } else {
        // No role restriction or not authenticated
        setHasRequiredRole(true); // Changed from !role to true
      }
      
      setIsLoading(false);
    };
    
    checkAuth();
  }, [role]);

  // Show loading indicator while checking authentication
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  // Redirect to home page if authenticated but doesn't have required role
  if (role && !hasRequiredRole) {
    return <Navigate to="/" replace />; // Changed from /dashboard to /
  }

  // Render child components if authenticated and has required role
  return children;
};

export default ProtectedRoute;