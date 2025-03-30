import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Button, 
  IconButton, 
  Box, 
  Drawer, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText,
  useMediaQuery,
  useTheme,
  Container,
  Menu,
  MenuItem,
  Avatar,
  Divider,
  ListItemButton
} from '@mui/material';
import { 
  Menu as MenuIcon, 
  Home as HomeIcon, 
  MonetizationOn, 
  BarChart, 
  Lightbulb,
  Close,
  People as PeopleIcon,
  AccountCircle,
  Logout,
  Person
} from '@mui/icons-material';

function Header() {
  const theme = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);
  const menuOpen = Boolean(anchorEl);

  // Load user data from localStorage when component mounts
  useEffect(() => {
    const storedUser = sessionStorage.getItem('user');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
  }, []);

  const menuItems = [
    { text: 'الرئيسية', icon: <HomeIcon />, path: '/' },
    { text: 'التسعير', icon: <MonetizationOn />, path: '/pricing' },
    { text: 'التصورات البيانية', icon: <BarChart />, path: '/visualizations' },
    { text: 'استراتيجيات المبيعات', icon: <Lightbulb />, path: '/sales-strategy' },
  ];

  // Add admin menu item conditionally
  const allMenuItems = [...menuItems];
  if (user && user.role === 'admin') {
    allMenuItems.push({ 
      text: 'إدارة المستخدمين', 
      icon: <PeopleIcon />, 
      path: '/admin/users' 
    });
  }

  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
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
    
    // Close menu
    handleMenuClose();
    
    // Force reload of the page to reset all states
    window.location.href = '/login';
  };
  
  const drawer = (
    <Box sx={{ width: 250, pt: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', px: 2, mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          أستشر بياناتك
        </Typography>
        <IconButton onClick={handleDrawerToggle}>
          <Close />
        </IconButton>
      </Box>
      <List>
        {allMenuItems.map((item) => (
          <ListItem 
            button 
            key={item.text} 
            component={Link} 
            to={item.path}
            onClick={handleDrawerToggle}
            sx={{ 
              borderRight: location.pathname === item.path ? `4px solid ${theme.palette.primary.main}` : 'none',
              backgroundColor: location.pathname === item.path ? 'rgba(25, 118, 210, 0.08)' : 'transparent',
              '&:hover': {
                backgroundColor: 'rgba(25, 118, 210, 0.04)',
              }
            }}
          >
            <ListItemIcon sx={{ color: location.pathname === item.path ? 'primary.main' : 'inherit' }}>
              {item.icon}
            </ListItemIcon>
            <ListItemText 
              primary={item.text} 
              primaryTypographyProps={{ 
                fontWeight: location.pathname === item.path ? 'bold' : 'normal'
              }}
            />
          </ListItem>
        ))}
        
        {/* Add logout option to mobile menu */}
        {user && (
          <>
            <Divider sx={{ my: 1 }} />
            <ListItem button onClick={handleLogout}>
              <ListItemIcon>
                <Logout />
              </ListItemIcon>
              <ListItemText primary="تسجيل الخروج" />
            </ListItem>
          </>
        )}
      </List>
    </Box>
  );

  return (
    <AppBar position="sticky" color="default" elevation={0} sx={{ backgroundColor: 'white' }}>
      <Container maxWidth="xl">
        <Toolbar disableGutters>
          <Typography 
            variant="h6" 
            component={Link} 
            to="/"
            sx={{ 
              flexGrow: 1, 
              color: 'primary.main', 
              fontWeight: 'bold', 
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            أستشر بياناتك
          </Typography>

          {isMobile ? (
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="end"
              onClick={handleDrawerToggle}
            >
              <MenuIcon />
            </IconButton>
          ) : (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {menuItems.map((item) => (
                <Button 
                  key={item.text}
                  color="inherit" 
                  component={Link} 
                  to={item.path}
                  sx={{ 
                    mx: 0.5,
                    fontWeight: location.pathname === item.path ? 'bold' : 'normal',
                    borderBottom: location.pathname === item.path ? `2px solid ${theme.palette.primary.main}` : '2px solid transparent',
                    borderRadius: 0,
                    color: location.pathname === item.path ? 'primary.main' : 'text.primary',
                    '&:hover': {
                      backgroundColor: 'transparent',
                      borderBottom: `2px solid ${theme.palette.primary.light}`,
                    }
                  }}
                >
                  {item.text}
                </Button>
              ))}
              
              {/* Admin button - only shown to admin users */}
              {user && user.role === 'admin' && (
                <Button 
                  color="primary"
                  variant="contained"
                  component={Link} 
                  to="/admin/users"
                  startIcon={<PeopleIcon />}
                  sx={{ 
                    ml: 2,
                    fontWeight: location.pathname === '/admin/users' ? 'bold' : 'normal',
                  }}
                >
                  إدارة المستخدمين
                </Button>
              )}
              
              {/* User profile icon and menu */}
              {user && (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', ml: 2 }}>
                    <Typography variant="body2" sx={{ mr: 1 }}>
                      مرحباً، {user.username}
                    </Typography>
                    
                    <IconButton 
                      onClick={handleProfileMenuOpen}
                      size="small" 
                      sx={{ color: theme.palette.primary.main }}
                    >
                      <AccountCircle />
                    </IconButton>
                  </Box>
                  
                  <Menu
                    anchorEl={anchorEl}
                    open={menuOpen}
                    onClose={handleMenuClose}
                    transformOrigin={{ horizontal: 'left', vertical: 'top' }}
                    anchorOrigin={{ horizontal: 'left', vertical: 'bottom' }}
                  >
                    <MenuItem onClick={handleMenuClose}>
                      <ListItemIcon>
                        <Person fontSize="small" />
                      </ListItemIcon>
                      <ListItemText>الملف الشخصي</ListItemText>
                    </MenuItem>
                    
                    <Divider />
                    
                    <MenuItem onClick={handleLogout}>
                      <ListItemIcon>
                        <Logout fontSize="small" />
                      </ListItemIcon>
                      <ListItemText>تسجيل الخروج</ListItemText>
                    </MenuItem>
                  </Menu>
                </>
              )}
            </Box>
          )}
        </Toolbar>
      </Container>

      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={handleDrawerToggle}
        ModalProps={{
          keepMounted: true,
        }}
      >
        {drawer}
      </Drawer>
    </AppBar>
  );
}

export default Header;