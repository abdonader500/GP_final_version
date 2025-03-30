import React, { useState, useEffect } from 'react';
import Header from '../../components/Header'; // Update the path based on your project structure
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Button,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Chip,
  Stack,
  FormControlLabel,
  Switch,
  Divider,
  alpha,
  useTheme,
  Container
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Key as KeyIcon,
  CheckCircle as ActiveIcon,
  Cancel as InactiveIcon,
  Search as SearchIcon
} from '@mui/icons-material';
import axios from 'axios';

const UserManagement = () => {
  const theme = useTheme();
  
  // Table state
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Dialog states
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [openEditDialog, setOpenEditDialog] = useState(false);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [openPasswordDialog, setOpenPasswordDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  
  // Form states
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
    name: '',
    email: '',
    role: 'user',
    active: true
  });
  const [formErrors, setFormErrors] = useState({});
  const [formSuccess, setFormSuccess] = useState('');
  const [formLoading, setFormLoading] = useState(false);
  
  // Get token for API calls
  const getToken = () => {
    return localStorage.getItem('token');
  };
  
  // Headers with token
  const getAuthHeaders = () => {
    return {
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    };
  };
  
  // Load users on component mount
  useEffect(() => {
    fetchUsers();
  }, []);
  
  // Fetch users from API
  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await axios.get('http://localhost:5000/api/admin/users', getAuthHeaders());
      setUsers(response.data.users);
    } catch (err) {
      console.error('Error fetching users:', err);
      setError('فشل في جلب بيانات المستخدمين. يرجى المحاولة مرة أخرى.');
    } finally {
      setLoading(false);
    }
  };
  
  // Handle page change
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };
  
  // Handle rows per page change
  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };
  
  // Filter users based on search query
  const filteredUsers = users.filter(user => {
    const query = searchQuery.toLowerCase();
    return (
      user.username.toLowerCase().includes(query) ||
      (user.name && user.name.toLowerCase().includes(query)) ||
      (user.email && user.email.toLowerCase().includes(query)) ||
      user.role.toLowerCase().includes(query)
    );
  });
  
  // Handle dialog open/close
  const handleOpenAddDialog = () => {
    setFormData({
      username: '',
      password: '',
      confirmPassword: '',
      name: '',
      email: '',
      role: 'user',
      active: true
    });
    setFormErrors({});
    setFormSuccess('');
    setOpenAddDialog(true);
  };
  
  const handleOpenEditDialog = (user) => {
    setSelectedUser(user);
    setFormData({
      username: user.username,
      name: user.name || '',
      email: user.email || '',
      role: user.role,
      active: user.active
    });
    setFormErrors({});
    setFormSuccess('');
    setOpenEditDialog(true);
  };
  
  const handleOpenPasswordDialog = (user) => {
    setSelectedUser(user);
    setFormData({
      password: '',
      confirmPassword: ''
    });
    setFormErrors({});
    setFormSuccess('');
    setOpenPasswordDialog(true);
  };
  
  const handleOpenDeleteDialog = (user) => {
    setSelectedUser(user);
    setOpenDeleteDialog(true);
  };
  
  const handleCloseDialogs = () => {
    setOpenAddDialog(false);
    setOpenEditDialog(false);
    setOpenDeleteDialog(false);
    setOpenPasswordDialog(false);
    setSelectedUser(null);
  };
  
  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'active' ? checked : value
    }));
    
    // Clear specific field error when user types
    if (formErrors[name]) {
      setFormErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };
  
  // Validate form
  const validateForm = (isPasswordForm = false) => {
    const errors = {};
    
    if (!isPasswordForm) {
      if (!formData.username.trim()) {
        errors.username = 'اسم المستخدم مطلوب';
      } else if (formData.username.length < 3) {
        errors.username = 'اسم المستخدم يجب أن يكون 3 أحرف على الأقل';
      }
      
      if (formData.email && !/\S+@\S+\.\S+/.test(formData.email)) {
        errors.email = 'البريد الإلكتروني غير صالح';
      }
    }
    
    if (openAddDialog || isPasswordForm) {
      if (!formData.password) {
        errors.password = 'كلمة المرور مطلوبة';
      } else if (formData.password.length < 6) {
        errors.password = 'كلمة المرور يجب أن تكون 6 أحرف على الأقل';
      }
      
      if (formData.password !== formData.confirmPassword) {
        errors.confirmPassword = 'كلمة المرور غير متطابقة';
      }
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };
  
  // Handle form submission
  const handleAddUser = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setFormLoading(true);
    setFormSuccess('');
    
    const token = getToken();
    console.log("Using token:", token);
    console.log("Auth headers:", getAuthHeaders());
    
    try {
      const response = await axios.post(
        'http://localhost:5000/api/admin/users',
        {
          username: formData.username,
          password: formData.password,
          name: formData.name,
          email: formData.email,
          role: formData.role,
          active: formData.active
        },
        getAuthHeaders()
      );
      
      setFormSuccess('تم إنشاء المستخدم بنجاح');
      fetchUsers(); // Refresh user list
      
      // Close dialog after a short delay
      setTimeout(() => {
        handleCloseDialogs();
      }, 1500);
      
    } catch (err) {
      console.error('Error adding user:', err);
      if (err.response && err.response.data && err.response.data.message) {
        setFormErrors(prev => ({
          ...prev,
          submit: err.response.data.message
        }));
      } else {
        setFormErrors(prev => ({
          ...prev,
          submit: 'فشل في إنشاء المستخدم. يرجى المحاولة مرة أخرى.'
        }));
      }
    } finally {
      setFormLoading(false);
    }
  };
  
  const handleUpdateUser = async (e) => {
    e.preventDefault();
    
    if (!validateForm(false) || !selectedUser) return;
    
    setFormLoading(true);
    setFormSuccess('');
    
    try {
      const response = await axios.put(
        `http://localhost:5000/api/admin/users/${selectedUser._id}`,
        {
          username: formData.username,
          name: formData.name,
          email: formData.email,
          role: formData.role,
          active: formData.active
        },
        getAuthHeaders()
      );
      
      setFormSuccess('تم تحديث بيانات المستخدم بنجاح');
      fetchUsers(); // Refresh user list
      
      // Close dialog after a short delay
      setTimeout(() => {
        handleCloseDialogs();
      }, 1500);
      
    } catch (err) {
      console.error('Error updating user:', err);
      if (err.response && err.response.data && err.response.data.message) {
        setFormErrors(prev => ({
          ...prev,
          submit: err.response.data.message
        }));
      } else {
        setFormErrors(prev => ({
          ...prev,
          submit: 'فشل في تحديث بيانات المستخدم. يرجى المحاولة مرة أخرى.'
        }));
      }
    } finally {
      setFormLoading(false);
    }
  };
  
  const handleChangePassword = async (e) => {
    e.preventDefault();
    
    if (!validateForm(true) || !selectedUser) return;
    
    setFormLoading(true);
    setFormSuccess('');
    
    try {
      const response = await axios.put(
        `http://localhost:5000/api/admin/users/${selectedUser._id}/change-password`,
        {
          password: formData.password
        },
        getAuthHeaders()
      );
      
      setFormSuccess('تم تغيير كلمة المرور بنجاح');
      
      // Close dialog after a short delay
      setTimeout(() => {
        handleCloseDialogs();
      }, 1500);
      
    } catch (err) {
      console.error('Error changing password:', err);
      if (err.response && err.response.data && err.response.data.message) {
        setFormErrors(prev => ({
          ...prev,
          submit: err.response.data.message
        }));
      } else {
        setFormErrors(prev => ({
          ...prev,
          submit: 'فشل في تغيير كلمة المرور. يرجى المحاولة مرة أخرى.'
        }));
      }
    } finally {
      setFormLoading(false);
    }
  };
  
  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    
    setFormLoading(true);
    
    try {
      await axios.delete(
        `http://localhost:5000/api/admin/users/${selectedUser._id}`,
        getAuthHeaders()
      );
      
      fetchUsers(); // Refresh user list
      handleCloseDialogs();
      
    } catch (err) {
      console.error('Error deleting user:', err);
      setError('فشل في حذف المستخدم. يرجى المحاولة مرة أخرى.');
    } finally {
      setFormLoading(false);
    }
  };
  
  // Render helper functions
  const renderRoleChip = (role) => {
    const roleConfig = {
      admin: { color: 'error', label: 'مسؤول' },
      user: { color: 'primary', label: 'مستخدم' }
    };
    
    const config = roleConfig[role] || { color: 'default', label: role };
    
    return (
      <Chip 
        label={config.label}
        color={config.color}
        size="small"
        variant="outlined"
      />
    );
  };
  
  const renderStatusChip = (active) => {
    return (
      <Chip 
        icon={active ? <ActiveIcon /> : <InactiveIcon />}
        label={active ? 'نشط' : 'معطل'}
        color={active ? 'success' : 'default'}
        size="small"
        variant={active ? 'outlined' : 'outlined'}
      />
    );
  };
  
  // Render add/edit user dialog
  const renderUserFormDialog = (isEdit = false) => {
    const title = isEdit ? 'تعديل بيانات المستخدم' : 'إضافة مستخدم جديد';
    const submitText = isEdit ? 'حفظ التغييرات' : 'إضافة';
    const handleSubmit = isEdit ? handleUpdateUser : handleAddUser;
    
    return (
      <Dialog 
        open={isEdit ? openEditDialog : openAddDialog}
        onClose={handleCloseDialogs}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ pb: 1 }}>{title}</DialogTitle>
        
        <DialogContent>
          {formErrors.submit && (
            <Alert severity="error" sx={{ mt: 1, mb: 2 }}>
              {formErrors.submit}
            </Alert>
          )}
          
          {formSuccess && (
            <Alert severity="success" sx={{ mt: 1, mb: 2 }}>
              {formSuccess}
            </Alert>
          )}
          
          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
            <TextField
              margin="normal"
              fullWidth
              label="اسم المستخدم"
              name="username"
              value={formData.username}
              onChange={handleInputChange}
              error={!!formErrors.username}
              helperText={formErrors.username}
              disabled={formLoading}
              required
              autoFocus={!isEdit}
            />
            
            {!isEdit && (
              <>
                <TextField
                  margin="normal"
                  fullWidth
                  label="كلمة المرور"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  error={!!formErrors.password}
                  helperText={formErrors.password}
                  disabled={formLoading}
                  required
                />
                
                <TextField
                  margin="normal"
                  fullWidth
                  label="تأكيد كلمة المرور"
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleInputChange}
                  error={!!formErrors.confirmPassword}
                  helperText={formErrors.confirmPassword}
                  disabled={formLoading}
                  required
                />
              </>
            )}
            
            <TextField
              margin="normal"
              fullWidth
              label="الاسم"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              disabled={formLoading}
            />
            
            <TextField
              margin="normal"
              fullWidth
              label="البريد الإلكتروني"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleInputChange}
              error={!!formErrors.email}
              helperText={formErrors.email}
              disabled={formLoading}
            />
            
            <FormControl fullWidth margin="normal">
              <InputLabel>الدور</InputLabel>
              <Select
                name="role"
                value={formData.role}
                onChange={handleInputChange}
                label="الدور"
                disabled={formLoading}
              >
                <MenuItem value="user">مستخدم</MenuItem>
                <MenuItem value="admin">مسؤول</MenuItem>
              </Select>
            </FormControl>
            
            <FormControlLabel
              control={
                <Switch
                  checked={formData.active}
                  onChange={handleInputChange}
                  name="active"
                  color="primary"
                  disabled={formLoading}
                />
              }
              label="الحساب نشط"
              sx={{ mt: 1 }}
            />
          </Box>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleCloseDialogs} disabled={formLoading}>
            إلغاء
          </Button>
          <Button 
            onClick={handleSubmit}
            variant="contained" 
            color="primary"
            disabled={formLoading}
            startIcon={formLoading && <CircularProgress size={20} color="inherit" />}
          >
            {submitText}
          </Button>
        </DialogActions>
      </Dialog>
    );
  };
  
  // Render password change dialog
  const renderPasswordDialog = () => {
    return (
      <Dialog
        open={openPasswordDialog}
        onClose={handleCloseDialogs}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ pb: 1 }}>تغيير كلمة المرور</DialogTitle>
        
        <DialogContent>
          {formErrors.submit && (
            <Alert severity="error" sx={{ mt: 1, mb: 2 }}>
              {formErrors.submit}
            </Alert>
          )}
          
          {formSuccess && (
            <Alert severity="success" sx={{ mt: 1, mb: 2 }}>
              {formSuccess}
            </Alert>
          )}
          
          <Box component="form" onSubmit={handleChangePassword} sx={{ mt: 1 }}>
            <TextField
              margin="normal"
              fullWidth
              label="كلمة المرور الجديدة"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleInputChange}
              error={!!formErrors.password}
              helperText={formErrors.password}
              disabled={formLoading}
              required
              autoFocus
            />
            
            <TextField
              margin="normal"
              fullWidth
              label="تأكيد كلمة المرور الجديدة"
              name="confirmPassword"
              type="password"
              value={formData.confirmPassword}
              onChange={handleInputChange}
              error={!!formErrors.confirmPassword}
              helperText={formErrors.confirmPassword}
              disabled={formLoading}
              required
            />
          </Box>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleCloseDialogs} disabled={formLoading}>
            إلغاء
          </Button>
          <Button 
            onClick={handleChangePassword}
            variant="contained" 
            color="primary"
            disabled={formLoading}
            startIcon={formLoading && <CircularProgress size={20} color="inherit" />}
          >
            حفظ
          </Button>
        </DialogActions>
      </Dialog>
    );
  };
  
  // Render delete confirmation dialog
  const renderDeleteDialog = () => {
    return (
      <Dialog
        open={openDeleteDialog}
        onClose={handleCloseDialogs}
      >
        <DialogTitle>تأكيد الحذف</DialogTitle>
        
        <DialogContent>
          <Typography>
            هل أنت متأكد من حذف المستخدم{' '}
            <strong>{selectedUser?.username}</strong>؟
          </Typography>
          <Typography color="error" variant="body2" sx={{ mt: 1 }}>
            لا يمكن التراجع عن هذا الإجراء.
          </Typography>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleCloseDialogs} disabled={formLoading}>
            إلغاء
          </Button>
          <Button 
            onClick={handleDeleteUser}
            variant="contained" 
            color="error"
            disabled={formLoading}
            startIcon={formLoading && <CircularProgress size={20} color="inherit" />}
          >
            حذف
          </Button>
        </DialogActions>
      </Dialog>
    );
  };
  
  return (
    <>
      <Container maxWidth="xl">
        <Box sx={{ mt: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold' }}>
              إدارة المستخدمين
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField
                placeholder="بحث..."
                size="small"
                variant="outlined"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                InputProps={{
                  startAdornment: <SearchIcon fontSize="small" sx={{ mr: 1, color: 'action.active' }} />,
                }}
                sx={{ width: 250 }}
              />
              
              <Button 
                variant="outlined"
                size="small"
                startIcon={<RefreshIcon />}
                onClick={fetchUsers}
              >
                تحديث
              </Button>
              
              <Button 
                variant="contained"
                size="small"
                startIcon={<AddIcon />}
                onClick={handleOpenAddDialog}
                sx={{ mr: 1 }}
              >
                إضافة مستخدم
              </Button>
            </Box>
          </Box>
          
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}
          
          <Paper elevation={1} sx={{ borderRadius: 2, overflow: 'hidden' }}>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: alpha(theme.palette.primary.main, 0.05) }}>
                    <TableCell sx={{ fontWeight: 'bold' }}>اسم المستخدم</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>الاسم</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>البريد الإلكتروني</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>الدور</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>الحالة</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>آخر دخول</TableCell>
                    <TableCell align="center" sx={{ fontWeight: 'bold' }}>الإجراءات</TableCell>
                  </TableRow>
                </TableHead>
                
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 3 }}>
                        <CircularProgress size={24} />
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          جاري تحميل البيانات...
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : filteredUsers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 3 }}>
                        <Typography variant="body1" color="text.secondary">
                          لا توجد بيانات
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredUsers
                      .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                      .map((user) => (
                        <TableRow key={user._id} hover>
                          <TableCell>{user.username}</TableCell>
                          <TableCell>{user.name || '-'}</TableCell>
                          <TableCell>{user.email || '-'}</TableCell>
                          <TableCell>{renderRoleChip(user.role)}</TableCell>
                          <TableCell>{renderStatusChip(user.active)}</TableCell>
                          <TableCell>
                            {user.lastLogin 
                              ? new Date(user.lastLogin).toLocaleString('ar-EG')
                              : 'لم يسجل الدخول بعد'}
                          </TableCell>
                          <TableCell align="center">
                            <Stack direction="row" spacing={1} justifyContent="center">
                              <Tooltip title="تغيير كلمة المرور">
                                <IconButton 
                                  size="small"
                                  color="primary"
                                  onClick={() => handleOpenPasswordDialog(user)}
                                >
                                  <KeyIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              
                              <Tooltip title="تعديل">
                                <IconButton 
                                  size="small"
                                  color="info"
                                  onClick={() => handleOpenEditDialog(user)}
                                >
                                  <EditIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              
                              <Tooltip title="حذف">
                                <IconButton 
                                  size="small"
                                  color="error"
                                  onClick={() => handleOpenDeleteDialog(user)}
                                >
                                  <DeleteIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Stack>
                          </TableCell>
                        </TableRow>
                      ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            
            <TablePagination
              component="div"
              count={filteredUsers.length}
              page={page}
              onPageChange={handleChangePage}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={handleChangeRowsPerPage}
              labelRowsPerPage="صفوف في الصفحة:"
              labelDisplayedRows={({ from, to, count }) => `${from}-${to} من ${count}`}
            />
          </Paper>
          
          {/* Render dialogs */}
          {renderUserFormDialog(false)}
          {renderUserFormDialog(true)}
          {renderPasswordDialog()}
          {renderDeleteDialog()}
        </Box>
      </Container>
    </>
  );
};

export default UserManagement;