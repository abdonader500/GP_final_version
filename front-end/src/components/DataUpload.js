import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  CircularProgress,
  Alert,
  FormControl,
  RadioGroup,
  FormControlLabel,
  Radio,
  Card,
  CardContent,
  Stack,
  Divider,
  Stepper,
  Step,
  StepLabel,
  Grid,
  alpha,
  useTheme,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress
} from '@mui/material';
import {
  CloudUpload,
  Check,
  Error,
  Refresh,
  PlayArrow,
  Info,
  UploadFile,
  ShoppingCart,
  Store,
  Autorenew
} from '@mui/icons-material';
import axios from 'axios';

const DataUpload = () => {
  const theme = useTheme();
  const [file, setFile] = useState(null);
  const [dataType, setDataType] = useState('sales');
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [processStatus, setProcessStatus] = useState(null);
  const [error, setError] = useState(null);
  const [activeStep, setActiveStep] = useState(0);
  const [collectionStats, setCollectionStats] = useState({ sales: 0, purchases: 0 });
  const [statusCheckInterval, setStatusCheckInterval] = useState(null);
  const [processingComplete, setProcessingComplete] = useState(false);

  const steps = ['تحديد الملف', 'رفع البيانات', 'معالجة البيانات'];

  // Get token for API calls
  const getToken = () => {
    return sessionStorage.getItem('token');
  };

  // Headers with token
  const getAuthHeaders = () => {
    return {
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    };
  };

  // Fetch collection stats on component mount
  useEffect(() => {
    fetchCollectionStats();
    return () => {
      // Clear interval on component unmount
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
      }
    };
  }, []);

  // Fetch collection stats
  const fetchCollectionStats = async () => {
    try {
      const response = await axios.get(
        'http://localhost:5000/api/upload/admin/collection-stats',
        getAuthHeaders()
      );

      if (response.data && response.data.success) {
        setCollectionStats(response.data.stats);
      }
    } catch (err) {
      console.error('Error fetching collection stats:', err);
    }
  };

  // Handle file selection
  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    
    // Reset states
    setUploadResult(null);
    setProcessStatus(null);
    setError(null);
    setProcessingComplete(false);
    
    if (selectedFile) {
      // Check file extension
      if (!selectedFile.name.endsWith('.csv')) {
        setError('يجب أن يكون الملف بتنسيق CSV');
        setFile(null);
        return;
      }
      
      setFile(selectedFile);
      setActiveStep(1);
    }
  };

  // Handle data type change
  const handleDataTypeChange = (event) => {
    setDataType(event.target.value);
  };

  // Handle file upload
  const handleUpload = async () => {
    if (!file) {
      setError('الرجاء اختيار ملف أولاً');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('dataType', dataType);

      const response = await axios.post(
        'http://localhost:5000/api/upload/admin/upload-data',
        formData,
        getAuthHeaders()
      );

      if (response.data && response.data.success) {
        setUploadResult(response.data);
        setActiveStep(2);
        // Refresh stats after successful upload
        fetchCollectionStats();
      } else {
        setError('حدث خطأ غير معروف أثناء رفع الملف');
      }
    } catch (err) {
      console.error('Error uploading file:', err);
      
      if (err.response && err.response.data && err.response.data.message) {
        setError(err.response.data.message);
      } else {
        setError('فشل في رفع الملف. يرجى التحقق من الاتصال بالخادم.');
      }
    } finally {
      setUploading(false);
    }
  };

  // Start data processing
  const handleProcessData = async () => {
    setProcessing(true);
    setError(null);
    setProcessingComplete(false);
    setProcessStatus({
      price_classification: { status: "pending", message: "في انتظار البدء..." },
      profit_optimizer: { status: "pending", message: "في انتظار البدء..." },
      aggregate_historical_demand: { status: "pending", message: "في انتظار البدء..." },
      predict_demand_2025: { status: "pending", message: "في انتظار البدء..." }
    });

    try {
      const response = await axios.post(
        'http://localhost:5000/api/upload/admin/process-data',
        {},
        getAuthHeaders()
      );

      if (response.data && response.data.success) {
        // Start periodic status check
        const interval = setInterval(checkProcessStatus, 2000);
        setStatusCheckInterval(interval);
      } else {
        setError('حدث خطأ غير معروف أثناء بدء المعالجة');
        setProcessing(false);
      }
    } catch (err) {
      console.error('Error starting data processing:', err);
      
      if (err.response && err.response.data && err.response.data.message) {
        setError(err.response.data.message);
      } else {
        setError('فشل في بدء معالجة البيانات. يرجى التحقق من الاتصال بالخادم.');
      }
      setProcessing(false);
    }
  };

  // Check process status
  const checkProcessStatus = useCallback(async () => {
    try {
      const response = await axios.get(
        'http://localhost:5000/api/upload/admin/process-status',
        getAuthHeaders()
      );

      if (response.data && response.data.success) {
        setProcessStatus(response.data.processes);
        
        // Check if all processes are complete or have errors
        const allComplete = Object.values(response.data.processes).every(
          process => process.status === 'complete' || process.status === 'error'
        );
        
        if (allComplete) {
          // Stop checking
          if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
            setStatusCheckInterval(null);
          }
          setProcessing(false);
          setProcessingComplete(true);
          
          // Refresh collection stats after processing
          fetchCollectionStats();
        }
      }
    } catch (err) {
      console.error('Error checking process status:', err);
      // Continue checking even if there's an error
    }
  }, [statusCheckInterval]);

  // Reset state and start over
  const handleReset = () => {
    setFile(null);
    setDataType('sales');
    setUploading(false);
    setProcessing(false);
    setUploadResult(null);
    setProcessStatus(null);
    setError(null);
    setActiveStep(0);
    setProcessingComplete(false);
    
    // Clear interval if it exists
    if (statusCheckInterval) {
      clearInterval(statusCheckInterval);
      setStatusCheckInterval(null);
    }
    
    // Refresh stats
    fetchCollectionStats();
  };

  // Process status indicator
  const getProcessStatusIcon = (status) => {
    switch (status) {
      case 'complete':
        return <Check sx={{ color: theme.palette.success.main }} />;
      case 'error':
        return <Error sx={{ color: theme.palette.error.main }} />;
      case 'processing':
        return <CircularProgress size={20} />;
      default:
        return <Info sx={{ color: theme.palette.text.secondary }} />;
    }
  };

  // Get process status color
  const getProcessStatusColor = (status) => {
    switch (status) {
      case 'complete':
        return theme.palette.success.main;
      case 'error':
        return theme.palette.error.main;
      case 'processing':
        return theme.palette.primary.main;
      default:
        return theme.palette.text.secondary;
    }
  };

  // Get overall processing progress percentage
  const getOverallProgress = () => {
    if (!processStatus) return 0;
    
    const statusValues = {
      'pending': 0,
      'processing': 50,
      'complete': 100,
      'error': 100
    };
    
    const processes = Object.values(processStatus);
    const totalProgress = processes.reduce((acc, process) => acc + statusValues[process.status], 0);
    return (totalProgress / (processes.length * 100)) * 100;
  };

  // Get process display name
  const getProcessDisplayName = (processKey) => {
    const processNames = {
      'price_classification': 'تصنيف الأسعار',
      'profit_optimizer': 'تحسين الربح',
      'aggregate_historical_demand': 'تجميع بيانات الطلب التاريخية',
      'predict_demand_2025': 'توقع الطلب لعام 2025'
    };
    
    return processNames[processKey] || processKey;
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" component="h1" gutterBottom sx={{ fontWeight: 'bold', mb: 3 }}>
        رفع ومعالجة البيانات
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }}>
            <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 4 }}>
              {steps.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
            
            {error && (
              <Alert 
                severity="error" 
                sx={{ mb: 3 }}
                onClose={() => setError(null)}
              >
                {error}
              </Alert>
            )}
            
            {activeStep === 0 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  اختر نوع البيانات والملف المراد رفعه
                </Typography>
                
                <FormControl component="fieldset" sx={{ mb: 3 }}>
                  <RadioGroup
                    row
                    name="dataType"
                    value={dataType}
                    onChange={handleDataTypeChange}
                  >
                    <FormControlLabel 
                      value="sales" 
                      control={<Radio />} 
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <ShoppingCart sx={{ mr: 1, fontSize: 20 }} />
                          <span>بيانات المبيعات</span>
                        </Box>
                      }
                    />
                    <FormControlLabel 
                      value="purchases" 
                      control={<Radio />} 
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Store sx={{ mr: 1, fontSize: 20 }} />
                          <span>بيانات المشتريات</span>
                        </Box>
                      }
                    />
                  </RadioGroup>
                </FormControl>
                
                <Divider sx={{ my: 2 }} />
                
                <Box 
                  sx={{
                    border: `2px dashed ${alpha(theme.palette.primary.main, 0.3)}`,
                    borderRadius: 2,
                    p: 3,
                    textAlign: 'center',
                    backgroundColor: alpha(theme.palette.primary.main, 0.05)
                  }}
                >
                  <input
                    accept=".csv"
                    id="file-upload"
                    type="file"
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                  />
                  <label htmlFor="file-upload">
                    <Button
                      variant="contained"
                      component="span"
                      startIcon={<UploadFile />}
                      sx={{ mb: 2 }}
                    >
                      اختر ملف CSV
                    </Button>
                  </label>
                  
                  <Typography variant="body2" color="text.secondary">
                    {file 
                      ? `تم اختيار الملف: ${file.name} (${(file.size / 1024).toFixed(2)} KB)`
                      : 'يرجى اختيار ملف CSV يحتوي على بيانات المبيعات أو المشتريات'
                    }
                  </Typography>
                </Box>
                
                <Box sx={{ mt: 3, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    يجب أن يحتوي الملف على الأعمدة التالية:
                  </Typography>
                  <Box 
                    sx={{ 
                      display: 'flex', 
                      flexWrap: 'wrap', 
                      gap: 1, 
                      justifyContent: 'center',
                      maxWidth: '600px',
                      mx: 'auto'
                    }}
                  >
                    {[
                      'التاريخ', 'باركود', 'اسم الصنف', 'المورد', 'القسم', 
                      'سعر المستهلك', 'الكمية', 'الرصيد', 'القيمة', 
                      'الخصم', 'الصافي', 'سعر الجملة', 'الربح', 'نسبة الربح'
                    ].map(column => (
                      <Chip 
                        key={column} 
                        label={column} 
                        size="small" 
                        variant="outlined"
                        sx={{ fontSize: '0.75rem' }}
                      />
                    ))}
                  </Box>
                </Box>
              </Box>
            )}
            
            {activeStep === 1 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  رفع البيانات إلى قاعدة البيانات
                </Typography>
                
                <Box sx={{ mb: 3 }}>
                  <Typography variant="body1" gutterBottom>
                    تفاصيل الملف:
                  </Typography>
                  <Stack spacing={1} sx={{ pl: 2 }}>
                    <Typography variant="body2">
                      <strong>اسم الملف:</strong> {file?.name}
                    </Typography>
                    <Typography variant="body2">
                      <strong>حجم الملف:</strong> {(file?.size / 1024).toFixed(2)} KB
                    </Typography>
                    <Typography variant="body2">
                      <strong>نوع البيانات:</strong> {dataType === 'sales' ? 'بيانات المبيعات' : 'بيانات المشتريات'}
                    </Typography>
                  </Stack>
                </Box>
                
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  سيتم إضافة البيانات الجديدة إلى البيانات الموجودة حالياً في قاعدة البيانات.
                </Typography>
                
                <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
                  <Button
                    variant="outlined"
                    onClick={handleReset}
                    disabled={uploading}
                  >
                    عودة
                  </Button>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={handleUpload}
                    disabled={uploading}
                    startIcon={uploading ? <CircularProgress size={20} color="inherit" /> : <CloudUpload />}
                  >
                    {uploading ? 'جاري الرفع...' : 'رفع البيانات'}
                  </Button>
                </Box>
              </Box>
            )}
            
            {activeStep === 2 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  معالجة البيانات
                </Typography>
                
                {uploadResult && (
                  <Alert severity="success" sx={{ mb: 3 }}>
                    تم رفع الملف بنجاح. تمت إضافة {uploadResult.rows_count} سجل جديد إلى قاعدة البيانات.
                  </Alert>
                )}
                
                <Typography variant="body2" sx={{ mb: 3 }}>
                  الخطوة التالية هي معالجة البيانات لتحديث النماذج وتصنيف البيانات. هذه العملية قد تستغرق بضع دقائق.
                </Typography>
                
                {/* Overall progress indicator */}
                {processStatus && (
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="body2" gutterBottom sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>التقدم الكلي للمعالجة</span>
                      <span>{Math.round(getOverallProgress())}%</span>
                    </Typography>
                    <LinearProgress 
                      variant="determinate" 
                      value={getOverallProgress()} 
                      color={processingComplete ? "success" : "primary"}
                      sx={{ 
                        height: 10, 
                        borderRadius: 5,
                        mb: 3
                      }}
                    />
                  </Box>
                )}
                
                <Box sx={{ mb: 3 }}>
                  {processStatus ? (
                    <Card variant="outlined" sx={{ mb: 3, borderRadius: 2 }}>
                      <CardContent sx={{ p: 2 }}>
                        <Typography variant="subtitle1" gutterBottom fontWeight="medium">
                          حالة العمليات
                        </Typography>
                        
                        {/* Process steps with status indicators */}
                        {Object.entries(processStatus).map(([process, status], index) => (
                          <Box key={process} sx={{ mb: index < Object.keys(processStatus).length - 1 ? 2 : 0 }}>
                            <Box sx={{ 
                              display: 'flex', 
                              alignItems: 'center',
                              p: 1,
                              borderRadius: 1,
                              bgcolor: alpha(getProcessStatusColor(status.status), 0.1)
                            }}>
                              <Box sx={{ mr: 2, display: 'flex' }}>
                                {getProcessStatusIcon(status.status)}
                              </Box>
                              
                              <Box sx={{ flexGrow: 1 }}>
                                <Typography variant="body2" fontWeight="medium">
                                  {getProcessDisplayName(process)}
                                </Typography>
                                
                                <Typography variant="caption" color="text.secondary">
                                  {status.message || 'جاري التحميل...'}
                                </Typography>
                                
                                {status.status === 'processing' && (
                                  <LinearProgress 
                                    sx={{ 
                                      mt: 1, 
                                      height: 4, 
                                      borderRadius: 2,
                                    }}
                                  />
                                )}
                              </Box>
                              
                              <Box>
                                <Chip 
                                  size="small"
                                  label={
                                    status.status === 'pending' ? 'في الانتظار' :
                                    status.status === 'processing' ? 'جاري المعالجة' :
                                    status.status === 'complete' ? 'مكتمل' : 'خطأ'
                                  }
                                  color={
                                    status.status === 'complete' ? 'success' :
                                    status.status === 'error' ? 'error' :
                                    status.status === 'processing' ? 'primary' : 'default'
                                  }
                                  variant={status.status === 'pending' ? 'outlined' : 'filled'}
                                />
                              </Box>
                            </Box>
                          </Box>
                        ))}
                      </CardContent>
                    </Card>
                  ) : (
                    <Box sx={{ textAlign: 'center', py: 2 }}>
                      <Button
                        variant="contained"
                        color="primary"
                        onClick={handleProcessData}
                        disabled={processing}
                        startIcon={processing ? <CircularProgress size={20} color="inherit" /> : <PlayArrow />}
                        sx={{ py: 1.5, px: 4 }}
                      >
                        {processing ? 'جاري المعالجة...' : 'بدء معالجة البيانات'}
                      </Button>
                    </Box>
                  )}
                </Box>
                
                {processingComplete && (
                  <Alert 
                    severity="success" 
                    sx={{ mb: 3 }}
                  >
                    <Typography variant="subtitle2" fontWeight="bold">
                      اكتملت معالجة البيانات بنجاح!
                    </Typography>
                    <Typography variant="body2">
                      تم تحديث النماذج والتصنيفات وتوقعات الطلب. يمكنك الآن تصفح الموقع واستخدام البيانات المحدثة.
                    </Typography>
                  </Alert>
                )}
                
                <Divider sx={{ my: 2 }} />
                
                <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                  <Button
                    variant="outlined"
                    startIcon={<Refresh />}
                    onClick={handleReset}
                    disabled={processing}
                  >
                    البدء من جديد
                  </Button>
                </Box>
              </Box>
            )}
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Card elevation={3} sx={{ borderRadius: 2, height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                إحصائيات قاعدة البيانات
              </Typography>
              
              <Divider sx={{ mb: 2 }} />
              
              <Box sx={{ mb: 4 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <ShoppingCart sx={{ color: theme.palette.primary.main, mr: 1 }} />
                  <Typography variant="subtitle1">بيانات المبيعات</Typography>
                </Box>
                <Typography variant="h4" sx={{ ml: 4, color: theme.palette.primary.main }}>
                  {collectionStats.sales.toLocaleString()} <Typography component="span" variant="body2" color="text.secondary">سجل</Typography>
                </Typography>
              </Box>
              
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Store sx={{ color: theme.palette.secondary.main, mr: 1 }} />
                  <Typography variant="subtitle1">بيانات المشتريات</Typography>
                </Box>
                <Typography variant="h4" sx={{ ml: 4, color: theme.palette.secondary.main }}>
                  {collectionStats.purchases.toLocaleString()} <Typography component="span" variant="body2" color="text.secondary">سجل</Typography>
                </Typography>
              </Box>
              
              <Divider sx={{ my: 3 }} />
              
              <Typography variant="body2" color="text.secondary">
                يتم تحديث هذه الإحصائيات تلقائياً عند رفع بيانات جديدة. يمكنك أيضاً النقر على زر "تحديث" لتحديث الإحصائيات يدوياً.
              </Typography>
              
              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Autorenew />}
                  onClick={fetchCollectionStats}
                >
                  تحديث الإحصائيات
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DataUpload;