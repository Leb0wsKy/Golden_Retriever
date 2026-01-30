import React from 'react';
import { Navigate } from 'react-router-dom';

/**
 * Protected Route component
 * Redirects to login if user is not authenticated
 */
function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token');
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
}

export default ProtectedRoute;
