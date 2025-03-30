import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Container,
  Divider,
  FormControlLabel,
  Radio,
  RadioGroup,
  FormControl,
  FormLabel,
  InputAdornment,
  IconButton,
  Alert,
  Collapse,
  CircularProgress,
  useTheme,
  alpha
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Person,
  Lock,
  AdminPanelSettings,
  PersonOutline
} from '@mui/icons-material';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const Login = ({ setIsAuthenticated }) => {
  const theme = useTheme();
  const navigate = useNavigate();
  
  // Form state
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('user');
  const [showPassword, setShowPassword] = useState(false);
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showError, setShowError] = useState(false);

  const handleTogglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  const handleRoleChange = (event) => {
    setRole(event.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!username.trim() || !password.trim()) {
      setError('يرجى إدخال اسم المستخدم وكلمة المرور');
      setShowError(true);
      return;
    }
    
    setLoading(true);
    setError('');
    setShowError(false);
    
    try {
      console.log('Attempting login with:', { username, password, role });
      const response = await axios.post('http://localhost:5000/api/auth/login', {
        username,
        password,
        role
      });
      
      console.log('Login response:', response.data);
      
      // Store token and user info in sessionStorage
      sessionStorage.setItem('token', response.data.token);
      sessionStorage.setItem('user', JSON.stringify({
        id: response.data.user._id,
        username: response.data.user.username,
        role: response.data.user.role
      }));
      
      console.log('User info stored in sessionStorage');
      
      // Update authentication state in parent component
      setIsAuthenticated(true);
      
      // Use React Router's navigate instead of window.location
      navigate('/');
    } catch (err) {
      console.error('Login error:', err);
      if (err.response && err.response.data && err.response.data.message) {
        setError(err.response.data.message);
      } else {
        setError('فشل تسجيل الدخول. يرجى التحقق من اسم المستخدم وكلمة المرور.');
      }
      setShowError(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)} 0%, ${alpha(theme.palette.primary.light, 0.2)} 100%)`,
        py: 4,
      }}
    >
      <Container maxWidth="sm">
        <Card
          elevation={6}
          sx={{
            borderRadius: 3,
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <Box
            sx={{
              p: 3,
              background: `linear-gradient(to right, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
              color: 'white',
              textAlign: 'center',
            }}
          >
            <Typography variant="h5" fontWeight="bold">
              أستشر بياناتك
            </Typography>
            <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
              يرجى تسجيل الدخول للوصول إلى لوحة التحكم
            </Typography>
          </Box>
          
          {/* Form */}
          <CardContent sx={{ p: 4 }}>
            <Collapse in={showError}>
              <Alert 
                severity="error" 
                sx={{ mb: 3, borderRadius: 2 }}
                onClose={() => setShowError(false)}
              >
                {error}
              </Alert>
            </Collapse>
            
            <Box component="form" onSubmit={handleSubmit} noValidate>
              {/* Role Selection */}
              <FormControl component="fieldset" sx={{ mb: 3, width: '100%' }}>
                <FormLabel component="legend" sx={{ mb: 1, color: 'text.primary', fontWeight: 'medium' }}>
                  نوع الحساب
                </FormLabel>
                <RadioGroup
                  row
                  aria-label="role"
                  name="role"
                  value={role}
                  onChange={handleRoleChange}
                >
                  <FormControlLabel 
                    value="user" 
                    control={<Radio color="primary" />} 
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <PersonOutline fontSize="small" />
                        <span>مستخدم</span>
                      </Box>
                    } 
                  />
                  <FormControlLabel 
                    value="admin" 
                    control={<Radio color="secondary" />} 
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <AdminPanelSettings fontSize="small" />
                        <span>مسؤول</span>
                      </Box>
                    }
                  />
                </RadioGroup>
              </FormControl>
              
              <Divider sx={{ my: 2 }} />
              
              {/* Username */}
              <TextField
                margin="normal"
                required
                fullWidth
                id="username"
                label="اسم المستخدم"
                name="username"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Person color="action" />
                    </InputAdornment>
                  ),
                }}
                sx={{ mb: 2 }}
              />
              
              {/* Password */}
              <TextField
                margin="normal"
                required
                fullWidth
                name="password"
                label="كلمة المرور"
                type={showPassword ? 'text' : 'password'}
                id="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Lock color="action" />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle password visibility"
                        onClick={handleTogglePasswordVisibility}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
                sx={{ mb: 3 }}
              />
              
              {/* Submit Button */}
              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loading}
                sx={{
                  mt: 3,
                  mb: 2,
                  height: 54,
                  borderRadius: 2,
                  fontWeight: 'bold',
                  boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.3)}`,
                }}
              >
                {loading ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  "تسجيل الدخول"
                )}
              </Button>
            </Box>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
};

export default Login;