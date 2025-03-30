import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Tabs,
  Tab,
  Paper,
  alpha,
  useTheme,
  Divider,
  Avatar,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import { 
  Dashboard as DashboardIcon, 
  People as PeopleIcon,
  Settings as SettingsIcon,
  BarChart as BarChartIcon,
  Logout as LogoutIcon,
  Person as PersonIcon,
  AccountCircle as AccountCircleIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import UserManagement from './UserManagement';
import axios from 'axios';

// Dashboard summary content
const DashboardContent = () => {
  const theme = useTheme();
  
  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h5" component="h2" sx={{ mb: 3, fontWeight: 'bold' }}>
        لوحة التحكم
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={6} lg={3}>
          <Card 
            elevation={2}
            sx={{ 
              borderRadius: 2,
              height: '100%',
              transition: 'transform 0.3s, box-shadow 0.3s',
              '&:hover': {
                transform: 'translateY(-5px)',
                boxShadow: '0 10px 20px rgba(0,0,0,0.1)'
              }
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar 
                  sx={{ 
                    bgcolor: alpha(theme.palette.primary.main, 0.1),
                    color: theme.palette.primary.main,
                    width: 48,
                    height: 48
                  }}
                >
                  <PeopleIcon />
                </Avatar>
                <Box sx={{ ml: 2 }}>
                  <Typography variant="h5" component="div" sx={{ fontWeight: 'bold' }}>
                    12
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    المستخدمين
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* You can add more summary cards here */}
      </Grid>
      
      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" component="h3" sx={{ mb: 2, fontWeight: 'bold' }}>
          آخر النشاطات
        </Typography>
        
        <Card elevation={1} sx={{ borderRadius: 2 }}>
          <CardContent>
            <Typography variant="body2" color="text.secondary">
              لا توجد نشاطات حديثة
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
};

// Settings content
const SettingsContent = () => {
  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h5" component="h2" sx={{ mb: 3, fontWeight: 'bold' }}>
        الإعدادات
      </Typography>
      
      <Card elevation={1} sx={{ borderRadius: 2 }}>
        <CardContent>
          <Typography>
            إعدادات النظام قيد التطوير
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

const AdminDashboard = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0);
  const [user, setUser] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);
  const menuOpen = Boolean(anchorEl);

  useEffect(() => {
    // Load user from localStorage
    const storedUser = sessionStorage.getItem('user');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    } else {
      // Redirect to login if user is not found
      navigate('/login');
    }
  }, [navigate]);

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const handleProfileMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    // Clear localStorage
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('user');
    
    // Redirect to login
    navigate('/login');
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 0: // Dashboard
        return <DashboardContent />;
      case 1: // User Management
        return <UserManagement />;
      case 2: // Settings
        return <SettingsContent />;
      default:
        return <DashboardContent />;
    }
  };

  if (!user) {
    return null; // Or return a loading spinner
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Header */}
      <Paper
        elevation={3}
        sx={{
          p: 2,
          background: `linear-gradient(to right, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
          color: 'white',
          borderRadius: 0,
        }}
      >
        <Container maxWidth="xl">
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h5" component="h1" fontWeight="bold">
              لوحة تحكم المسؤول
            </Typography>
            
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="body2" sx={{ mr: 1 }}>
                مرحباً، {user.username}
              </Typography>
              
              <IconButton 
                onClick={handleProfileMenuOpen}
                size="small" 
                sx={{ color: 'white' }}
              >
                <AccountCircleIcon />
              </IconButton>
              
              <Menu
                anchorEl={anchorEl}
                open={menuOpen}
                onClose={handleMenuClose}
                transformOrigin={{ horizontal: 'left', vertical: 'top' }}
                anchorOrigin={{ horizontal: 'left', vertical: 'bottom' }}
              >
                <MenuItem onClick={handleMenuClose}>
                  <ListItemIcon>
                    <PersonIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText>الملف الشخصي</ListItemText>
                </MenuItem>
                
                <Divider />
                
                <MenuItem onClick={handleLogout}>
                  <ListItemIcon>
                    <LogoutIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText>تسجيل الخروج</ListItemText>
                </MenuItem>
              </Menu>
            </Box>
          </Box>
        </Container>
      </Paper>

      {/* Main Content */}
      <Box sx={{ display: 'flex', flex: 1 }}>
        {/* Navigation Tabs */}
        <Paper 
          elevation={2} 
          sx={{ 
            width: 72, 
            display: 'flex', 
            flexDirection: 'column',
            alignItems: 'center', 
            p: 1,
            pt: 2
          }}
        >
          <Tabs
            orientation="vertical"
            value={activeTab}
            onChange={handleTabChange}
            sx={{
              '& .MuiTab-root': {
                minWidth: 'auto',
                p: 1.5,
                mb: 1,
                borderRadius: 2
              },
              '& .Mui-selected': {
                bgcolor: alpha(theme.palette.primary.main, 0.1),
                color: theme.palette.primary.main
              }
            }}
            TabIndicatorProps={{ sx: { display: 'none' } }}
          >
            <Tab 
              icon={<DashboardIcon />} 
              aria-label="لوحة التحكم" 
              title="لوحة التحكم"
            />
            <Tab 
              icon={<PeopleIcon />} 
              aria-label="إدارة المستخدمين" 
              title="إدارة المستخدمين"
            />
            <Tab 
              icon={<SettingsIcon />} 
              aria-label="الإعدادات" 
              title="الإعدادات"
            />
          </Tabs>
        </Paper>

        {/* Content Area */}
        <Container maxWidth="xl" sx={{ py: 3, flex: 1 }}>
          {renderTabContent()}
        </Container>
      </Box>
    </Box>
  );
};

export default AdminDashboard;