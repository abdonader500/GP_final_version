import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Container, 
  Typography, 
  TextField, 
  Button, 
  CircularProgress, 
  Paper, 
  Box, 
  Fade, 
  Alert,
  Grid,
  Divider,
  Card,
  CardContent,
  Stepper,
  Step,
  StepLabel,
  useTheme,
  alpha,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import { 
  MonetizationOn, 
  Calculate,
  LocalOffer,
  ShoppingCart,
  Send
} from '@mui/icons-material';

function Pricing() {
  const theme = useTheme();
  const [category, setCategory] = useState('');
  const [categories, setCategories] = useState([]);
  const [productSpec, setProductSpec] = useState('');
  const [purchasePrice, setPurchasePrice] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingCategories, setIsFetchingCategories] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Fetch categories from API when component mounts
  useEffect(() => {
    const fetchCategories = async () => {
      setIsFetchingCategories(true);
      try {
        // Try to fetch from API first
        try {
          const response = await axios.get('http://localhost:5000/api/visualization/categories');
          if (response.data && Array.isArray(response.data)) {
            setCategories(response.data);
            return;
          }
        } catch (apiError) {
          console.error('Error fetching from API:', apiError);
          // Continue to fallback
        }

        // Fallback to a default list if API fails
        setCategories([
          'حريمي',
          'رجالي',
          'اطفال',
          'داخلي اطفال',
          'داخلي حريمي',
          'داخلي رجالي',
          'احذية حريمي',
          'احذية رجالي',
          'احذية اطفال',
          'مدارس'
        ]);
      } catch (err) {
        console.error('Error setting categories:', err);
        // Set minimum fallback
        setCategories([
          'حريمي',
          'رجالي',
          'اطفال'
        ]);
      } finally {
        setIsFetchingCategories(false);
      }
    };

    fetchCategories();
  }, []);

  const handleCategoryChange = (event) => {
    setCategory(event.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!category || !productSpec || !purchasePrice) {
      setError('يرجى ملء جميع الحقول: القسم، المواصفات، وسعر الجملة');
      return;
    }
    const price = parseFloat(purchasePrice);
    if (price <= 0) {
      setError('سعر الجملة يجب ان يكون اكبر من صفر');
      return;
    }
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post('http://localhost:5000/api/price-analysis/get-optimal-profit', {
        category,
        product_specification: productSpec,
        purchase_price: price,
      });

      const { category: resCategory, product_specification, original_price, classified_price_level, optimal_profit_percentage } = response.data;

      const purchase = parseFloat(original_price);
      const profitPercent = parseFloat(optimal_profit_percentage);
      const initialFinalPrice = purchase * (1 + profitPercent / 100);

      const m = Math.ceil(initialFinalPrice / 10) * 10;
      const adjustedFinalPrice = m - 0.01;

      const adjustedProfitPercentage = ((adjustedFinalPrice - purchase) / purchase * 100).toFixed(2);

      setResult({
        category: resCategory,
        product_specification,
        original_price: purchase.toFixed(2),
        classified_price_level,
        optimal_profit_percentage: adjustedProfitPercentage,
        final_price: adjustedFinalPrice.toFixed(2),
      });
    } catch (err) {
      if (err.response && err.response.data && err.response.data.error) {
        const backendError = err.response.data.error.toLowerCase();
        if (backendError.includes('no profit model found for the given category and specification')) {
          setError('لا يوجد نطاق سعر متاح لهذا القسم والمواصفات. يرجى التحقق من المدخلات او إضافة البيانات.');
        } else {
          setError(`فشل في الحصول على نسبة الربح المثلى: ${err.response.data.error}`);
        }
      } else {
        setError('فشل في الحصول على نسبة الربح المثلى بسبب مشكلة في الاتصال');
      }
      console.error('Error fetching optimal profit:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Price level map for display
  const priceLevelMap = {
    'low': 'منخفض',
    'moderate': 'متوسط',
    'high': 'مرتفع',
    'very_high': 'مرتفع جدا'
  };

  // Price level to color map
  const priceLevelColorMap = {
    'low': theme.palette.success.main,
    'moderate': theme.palette.info.main,
    'high': theme.palette.warning.main,
    'very_high': theme.palette.error.main
  };

  return (
    <Box 
      sx={{ 
        minHeight: 'calc(100vh - 64px)', // Account for header height
        py: 6,
        background: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)',
      }}
    >
      <Container>
        <Grid container spacing={4}>
          {/* Left Side - Form */}
          <Grid item xs={12} md={6}>
            <Paper 
              elevation={3} 
              sx={{ 
                p: 4, 
                borderRadius: 3,
                height: '100%',
                background: 'white',
                boxShadow: '0 8px 32px rgba(0, 105, 192, 0.1)',
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Box
                  sx={{
                    width: 60,
                    height: 60,
                    borderRadius: '50%',
                    backgroundColor: alpha(theme.palette.primary.main, 0.1),
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    mr: 2
                  }}
                >
                  <MonetizationOn sx={{ fontSize: 30, color: theme.palette.primary.main }} />
                </Box>
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 'bold', color: theme.palette.primary.main }}>
                    تحسين التسعير
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    احصل على افضل سعر لزيادة مبيعاتك وارباحك
                  </Typography>
                </Box>
              </Box>

              <Stepper activeStep={1} alternativeLabel sx={{ mb: 4 }}>
                <Step>
                  <StepLabel>إدخال البيانات</StepLabel>
                </Step>
                <Step>
                  <StepLabel>تحليل الاسعار</StepLabel>
                </Step>
                <Step>
                  <StepLabel>توصيات التسعير</StepLabel>
                </Step>
              </Stepper>

              <Box component="form" onSubmit={handleSubmit}>
                {/* Category Dropdown */}
                <FormControl 
                  fullWidth 
                  variant="outlined"
                  margin="normal" 
                  required
                  sx={{ mb: 3 }}
                  disabled={isFetchingCategories}
                >
                  <InputLabel>القسم</InputLabel>
                  <Select
                    value={category}
                    onChange={handleCategoryChange}
                    label="القسم"
                    disabled={isFetchingCategories}
                  >
                    {isFetchingCategories ? (
                      <MenuItem value="">
                        <CircularProgress size={20} /> جاري التحميل...
                      </MenuItem>
                    ) : (
                      [
                        <MenuItem key="default" value="" disabled>اختر القسم</MenuItem>,
                        ...categories.map((cat) => (
                          <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                        ))
                      ]
                    )}
                  </Select>
                </FormControl>
                
                <TextField
                  fullWidth
                  label="المواصفات"
                  value={productSpec}
                  onChange={(e) => setProductSpec(e.target.value)}
                  variant="outlined"
                  margin="normal"
                  required
                  sx={{ mb: 3 }}
                  placeholder="مثال: تيشرت، بنطلون، حذاء"
                  InputProps={{
                    startAdornment: <ShoppingCart sx={{ color: 'text.secondary', mr: 1 }} />
                  }}
                />
                
                <TextField
                  fullWidth
                  label="سعر الجملة"
                  type="number"
                  value={purchasePrice}
                  onChange={(e) => setPurchasePrice(e.target.value)}
                  variant="outlined"
                  margin="normal"
                  required
                  inputProps={{ min: 0, step: 0.01 }}
                  sx={{ mb: 4 }}
                  InputProps={{
                    startAdornment: <Calculate sx={{ color: 'text.secondary', mr: 1 }} />
                  }}
                />
                
                <Button
                  type="submit"
                  variant="contained"
                  color="primary"
                  fullWidth
                  disabled={isLoading || isFetchingCategories}
                  sx={{ 
                    py: 1.5, 
                    fontSize: '1.1rem', 
                    borderRadius: 2,
                    boxShadow: '0 4px 10px rgba(25, 118, 210, 0.3)',
                    '&:hover': { boxShadow: '0 6px 12px rgba(25, 118, 210, 0.4)' }
                  }}
                  endIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <Send />}
                >
                  {isLoading ? 'جاري الحساب...' : 'احسب الربح الامثل'}
                </Button>

                {error && (
                  <Alert 
                    severity="error" 
                    sx={{ 
                      mt: 3, 
                      borderRadius: 2,
                      backgroundColor: alpha(theme.palette.error.main, 0.1),
                      color: theme.palette.error.dark
                    }}
                  >
                    {error}
                  </Alert>
                )}
              </Box>
            </Paper>
          </Grid>

          {/* Right Side - Results or Info */}
          <Grid item xs={12} md={6}>
            {result ? (
              <Fade in={true}>
                <Paper 
                  elevation={3} 
                  sx={{ 
                    p: 4, 
                    borderRadius: 3, 
                    height: '100%',
                    background: 'white',
                    boxShadow: '0 8px 32px rgba(0, 105, 192, 0.1)',
                  }}
                >
                  <Typography 
                    variant="h5" 
                    gutterBottom 
                    sx={{ 
                      color: theme.palette.primary.main, 
                      fontWeight: 'bold',
                      mb: 3
                    }}
                  >
                    نتائج التحليل والتوصيات
                  </Typography>
                  
                  <Grid container spacing={3}>
                    <Grid item xs={12}>
                      <Card 
                        sx={{ 
                          borderRadius: 2, 
                          boxShadow: 'none',
                          backgroundColor: alpha(theme.palette.primary.main, 0.05)
                        }}
                      >
                        <CardContent>
                          <Typography variant="subtitle2" color="text.secondary">
                            معلومات المنتج
                          </Typography>
                          <Grid container spacing={2} sx={{ mt: 1 }}>
                            <Grid item xs={6}>
                              <Typography variant="body2" color="text.secondary">القسم</Typography>
                              <Typography variant="body1" fontWeight="medium">{result.category}</Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography variant="body2" color="text.secondary">المواصفات</Typography>
                              <Typography variant="body1" fontWeight="medium">{result.product_specification}</Typography>
                            </Grid>
                          </Grid>
                        </CardContent>
                      </Card>
                    </Grid>

                    <Grid item xs={12} sm={4}>
                      <Card 
                        sx={{ 
                          borderRadius: 2, 
                          boxShadow: 'none',
                          height: '100%',
                          backgroundColor: alpha(theme.palette.info.main, 0.05)
                        }}
                      >
                        <CardContent sx={{ textAlign: 'center', py: 3 }}>
                          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                            سعر الجملة
                          </Typography>
                          <Typography variant="h5" color="text.primary" fontWeight="bold">
                            {result.original_price}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>

                    <Grid item xs={12} sm={4}>
                      <Card 
                        sx={{ 
                          borderRadius: 2, 
                          boxShadow: 'none',
                          height: '100%',
                          backgroundColor: alpha(theme.palette.success.main, 0.05)
                        }}
                      >
                        <CardContent sx={{ textAlign: 'center', py: 3 }}>
                          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                            نسبة الربح الامثل
                          </Typography>
                          <Typography 
                            variant="h5" 
                            fontWeight="bold"
                            color={theme.palette.success.dark}
                          >
                            %{result.optimal_profit_percentage}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>

                    <Grid item xs={12} sm={4}>
                      <Card 
                        sx={{ 
                          borderRadius: 2, 
                          boxShadow: 'none',
                          height: '100%',
                          backgroundColor: alpha(theme.palette.primary.main, 0.08)
                        }}
                      >
                        <CardContent sx={{ textAlign: 'center', py: 3 }}>
                          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                            السعر النهائي
                          </Typography>
                          <Typography 
                            variant="h5" 
                            fontWeight="bold"
                            color={theme.palette.primary.dark}
                          >
                            {result.final_price}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>

                    <Grid item xs={12}>
                      <Card 
                        sx={{ 
                          borderRadius: 2, 
                          boxShadow: 'none',
                          backgroundColor: alpha(
                            priceLevelColorMap[result.classified_price_level] || theme.palette.info.main, 
                            0.1
                          ),
                          border: `1px solid ${alpha(
                            priceLevelColorMap[result.classified_price_level] || theme.palette.info.main, 
                            0.3
                          )}`
                        }}
                      >
                        <CardContent>
                          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                            مستوى سعر المنتج 
                          </Typography>
                          <Typography 
                            variant="h6" 
                            sx={{ 
                              color: priceLevelColorMap[result.classified_price_level] || theme.palette.info.main,
                              fontWeight: 'bold'
                            }}
                          >
                            {priceLevelMap[result.classified_price_level] || 'غير محدد'}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>

                    <Grid item xs={12}>
                      <Card 
                        sx={{ 
                          borderRadius: 2, 
                          boxShadow: 'none',
                          background: 'linear-gradient(90deg, rgba(25, 118, 210, 0.05) 0%, rgba(66, 165, 245, 0.1) 100%)',
                        }}
                      >
                        <CardContent>
                          <Typography variant="subtitle2" gutterBottom sx={{ color: theme.palette.primary.main }}>
                            توصيات إضافية
                          </Typography>
                          <Typography variant="body2" paragraph>
                            بناءً على تحليل الاسعار، نوصي بالتالي:
                          </Typography>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            • استخدم السعر النهائي المقترح لتحقيق اقصى ربح مع الحفاظ على المنافسة.
                          </Typography>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            • قم بمراقبة اسعار المنافسين بشكل دوري وتعديل السعر عند الضرورة.
                          </Typography>
                          <Typography variant="body2">
                            • استخدم استراتيجيات التسويق المناسبة لتبرير مستوى السعر للعملاء.
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                </Paper>
              </Fade>
            ) : (
              <Paper 
                elevation={3} 
                sx={{ 
                  p: 4, 
                  borderRadius: 3,
                  height: '100%',
                  background: 'white',
                  boxShadow: '0 8px 32px rgba(0, 105, 192, 0.1)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                }}
              >
                <Box 
                  sx={{ 
                    width: 80,
                    height: 80,
                    borderRadius: '50%',
                    backgroundColor: alpha(theme.palette.primary.main, 0.1),
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    mx: 'auto',
                    mb: 3
                  }}
                >
                  <MonetizationOn sx={{ fontSize: 40, color: theme.palette.primary.main }} />
                </Box>
                
                <Typography 
                  variant="h5" 
                  align="center" 
                  gutterBottom 
                  sx={{ fontWeight: 'bold', color: theme.palette.primary.main }}
                >
                  كيف يعمل نظام التسعير الذكي؟
                </Typography>
                
                <Typography variant="body1" align="center" paragraph sx={{ mb: 4 }}>
                  يستخدم نظامنا تقنيات الذكاء الاصطناعي لتحليل بيانات السوق وتحديد افضل سعر لمنتجاتك.
                </Typography>
                
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box
                      sx={{
                        minWidth: 36,
                        height: 36,
                        borderRadius: '50%',
                        backgroundColor: alpha(theme.palette.primary.main, 0.1),
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        mr: 2
                      }}
                    >
                      <Typography sx={{ fontWeight: 'bold', color: theme.palette.primary.main }}>1</Typography>
                    </Box>
                    <Typography>ادخل بيانات المنتج بما في ذلك القسم والمواصفات وسعر الجملة.</Typography>
                  </Box>
                  
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box
                      sx={{
                        minWidth: 36,
                        height: 36,
                        borderRadius: '50%',
                        backgroundColor: alpha(theme.palette.primary.main, 0.1),
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        mr: 2
                      }}
                    >
                      <Typography sx={{ fontWeight: 'bold', color: theme.palette.primary.main }}>2</Typography>
                    </Box>
                    <Typography>يقوم النظام بتحليل الاسعار وتصنيف مستوى السعر في السوق.</Typography>
                  </Box>
                  
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box
                      sx={{
                        minWidth: 36,
                        height: 36,
                        borderRadius: '50%',
                        backgroundColor: alpha(theme.palette.primary.main, 0.1),
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        mr: 2
                      }}
                    >
                      <Typography sx={{ fontWeight: 'bold', color: theme.palette.primary.main }}>3</Typography>
                    </Box>
                    <Typography>يقترح النظام نسبة الربح المثلى والسعر النهائي الموصى به.</Typography>
                  </Box>
                </Box>
                
                <Divider sx={{ my: 4 }} />
                
                <Typography variant="body2" align="center" color="text.secondary">
                  قم بملء النموذج على اليمين للحصول على تحليل مخصص لمنتجك
                </Typography>
              </Paper>
            )}
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}

export default Pricing;