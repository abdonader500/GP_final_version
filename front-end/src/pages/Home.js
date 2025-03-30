import React from 'react';
import { 
  Typography, 
  Container, 
  Grid, 
  Card, 
  CardContent, 
  CardActions, 
  Button, 
  Box,
  Paper,
  Divider,
  useTheme
} from '@mui/material';
import { 
  MonetizationOn, 
  BarChart, 
  Lightbulb,
  ArrowBack
} from '@mui/icons-material';

function Home() {
  const theme = useTheme();

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        overflow: 'hidden',
      }}
    >
      {/* Hero Section with Background */}
      <Box 
        sx={{
          background: 'linear-gradient(120deg, #0a4d8c 0%, #1976d2 100%)',
          color: 'white',
          py: 6,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <Container maxWidth="lg">
          <Box sx={{ position: 'relative', zIndex: 2 }}>
            <Typography
              variant="h2"
              align="center"
              gutterBottom
              sx={{ 
                fontWeight: 800, 
                mb: 2,
                textShadow: '0px 2px 4px rgba(0,0,0,0.3)'
              }}
            >
              مرحبا بك في أستشر بياناتك
            </Typography>
            <Typography
              variant="h5"
              align="center"
              sx={{ 
                mb: 4, 
                maxWidth: '800px',
                mx: 'auto',
                fontWeight: 300
              }}
            >
              نظام ذكي لتحسين التسعير، عرض البيانات، واستراتيجيات المبيعات لزيادة أرباحك.
            </Typography>
            
            {/* Quick Access Buttons */}
            <Box 
              sx={{ 
                display: 'flex', 
                justifyContent: 'center', 
                gap: 2,
                flexWrap: 'wrap',
                mb: 2
              }}
            >
              <Button 
                variant="contained" 
                color="secondary" 
                size="large"
                href="/pricing"
                sx={{ 
                  py: 1.5, 
                  px: 4, 
                  borderRadius: 2,
                  backgroundColor: 'white',
                  color: '#1976d2',
                  '&:hover': {
                    backgroundColor: '#f5f5f5',
                  }
                }}
              >
                ابدأ بالتسعير
              </Button>
              <Button 
                variant="outlined" 
                color="inherit" 
                size="large"
                href="/visualizations"
                sx={{ 
                  py: 1.5, 
                  px: 4, 
                  borderRadius: 2,
                  borderColor: 'white',
                  '&:hover': {
                    borderColor: 'white',
                    backgroundColor: 'rgba(255,255,255,0.1)',
                  }
                }}
              >
                استكشف البيانات
              </Button>
            </Box>
          </Box>
        </Container>
        
        {/* Abstract Background Elements */}
        <Box sx={{ 
          position: 'absolute', 
          top: '10%', 
          left: '5%', 
          width: '200px', 
          height: '200px', 
          borderRadius: '50%', 
          background: 'rgba(255,255,255,0.1)',
          zIndex: 1
        }} />
        <Box sx={{ 
          position: 'absolute', 
          bottom: '15%', 
          right: '8%', 
          width: '150px', 
          height: '150px', 
          borderRadius: '50%', 
          background: 'rgba(255,255,255,0.1)',
          zIndex: 1
        }} />
      </Box>

      {/* Services Section */}
      <Container sx={{ py: 6 }}>
        <Typography
          variant="h4"
          align="center"
          gutterBottom
          sx={{ fontWeight: 'bold', mb: 1 }}
        >
          خدماتنا
        </Typography>
        <Typography
          variant="body1"
          align="center"
          color="text.secondary"
          sx={{ mb: 5, maxWidth: '700px', mx: 'auto' }}
        >
          حلول مبتكرة تجمع بين التحليلات المتقدمة والذكاء الاصطناعي لمساعدتك في تحقيق أقصى استفادة من بياناتك
        </Typography>

        <Grid container spacing={4} justifyContent="center">
          {/* Pricing Card */}
          <Grid item xs={12} sm={6} md={4}>
            <Card 
              sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                borderRadius: 3,
                transition: 'transform 0.3s, box-shadow 0.3s',
                '&:hover': {
                  transform: 'translateY(-8px)',
                  boxShadow: `0 12px 20px -10px ${theme.palette.primary.main}40`,
                },
                overflow: 'visible'
              }}
              elevation={4}
            >
              <Box 
                sx={{ 
                  backgroundColor: theme.palette.primary.main,
                  color: 'white',
                  p: 2,
                  borderTopLeftRadius: 12,
                  borderTopRightRadius: 12,
                  position: 'relative'
                }}
              >
                <Box 
                  sx={{ 
                    position: 'absolute',
                    top: -30,
                    right: 25,
                    backgroundColor: theme.palette.primary.main,
                    borderRadius: '50%',
                    width: 60,
                    height: 60,
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    boxShadow: 3
                  }}
                >
                  <MonetizationOn sx={{ fontSize: 35, color: 'white' }} />
                </Box>
                <Typography variant="h5" sx={{ mt: 1, fontWeight: 'bold' }}>التسعير</Typography>
              </Box>
              <CardContent sx={{ flexGrow: 1, pt: 3 }}>
                <Typography variant="body1" paragraph>
                  احصل على نسبة الربح المثلى وسعر البيع المثالي لمنتجاتك باستخدام خوارزميات متطورة.
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • تحليل أسعار المنافسين
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • توصيات مخصصة حسب فئة المنتج
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • تعديل مستمر حسب حالة السوق
                </Typography>
              </CardContent>
              <CardActions sx={{ p: 2, pt: 0 }}>
                <Button 
                  variant="outlined" 
                  color="primary" 
                  href="/pricing"
                  fullWidth
                  sx={{ 
                    borderRadius: 2,
                    py: 1,
                    '&:hover': {
                      backgroundColor: theme.palette.primary.main,
                      color: 'white'
                    }
                  }}
                  endIcon={<ArrowBack />}
                >
                  ابدأ الآن
                </Button>
              </CardActions>
            </Card>
          </Grid>

          {/* Visualizations Card */}
          <Grid item xs={12} sm={6} md={4}>
            <Card 
              sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                borderRadius: 3,
                transition: 'transform 0.3s, box-shadow 0.3s',
                '&:hover': {
                  transform: 'translateY(-8px)',
                  boxShadow: `0 12px 20px -10px ${theme.palette.info.main}40`,
                },
                overflow: 'visible'
              }}
              elevation={4}
            >
              <Box 
                sx={{ 
                  backgroundColor: theme.palette.info.main,
                  color: 'white',
                  p: 2,
                  borderTopLeftRadius: 12,
                  borderTopRightRadius: 12,
                  position: 'relative'
                }}
              >
                <Box 
                  sx={{ 
                    position: 'absolute',
                    top: -30,
                    right: 25,
                    backgroundColor: theme.palette.info.main,
                    borderRadius: '50%',
                    width: 60,
                    height: 60,
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    boxShadow: 3
                  }}
                >
                  <BarChart sx={{ fontSize: 35, color: 'white' }} />
                </Box>
                <Typography variant="h5" sx={{ mt: 1, fontWeight: 'bold' }}>التصورات البيانية</Typography>
              </Box>
              <CardContent sx={{ flexGrow: 1, pt: 3 }}>
                <Typography variant="body1" paragraph>
                  استكشف بياناتك من خلال رسوم بيانية تفاعلية تساعدك على اتخاذ قرارات استراتيجية أفضل.
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • تحليل الاتجاهات الموسمية
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • مقارنة أداء المنتجات المختلفة
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • تصدير التقارير بتنسيقات متعددة
                </Typography>
              </CardContent>
              <CardActions sx={{ p: 2, pt: 0 }}>
                <Button 
                  variant="outlined" 
                  color="info" 
                  href="/visualizations"
                  fullWidth
                  sx={{ 
                    borderRadius: 2,
                    py: 1,
                    '&:hover': {
                      backgroundColor: theme.palette.info.main,
                      color: 'white'
                    }
                  }}
                  endIcon={<ArrowBack />}
                >
                  استكشف الآن
                </Button>
              </CardActions>
            </Card>
          </Grid>

          {/* Sales Strategies Card */}
          <Grid item xs={12} sm={6} md={4}>
            <Card 
              sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                borderRadius: 3,
                transition: 'transform 0.3s, box-shadow 0.3s',
                '&:hover': {
                  transform: 'translateY(-8px)',
                  boxShadow: `0 12px 20px -10px ${theme.palette.success.main}40`,
                },
                overflow: 'visible'
              }}
              elevation={4}
            >
              <Box 
                sx={{ 
                  backgroundColor: theme.palette.success.main,
                  color: 'white',
                  p: 2,
                  borderTopLeftRadius: 12,
                  borderTopRightRadius: 12,
                  position: 'relative'
                }}
              >
                <Box 
                  sx={{ 
                    position: 'absolute',
                    top: -30,
                    right: 25,
                    backgroundColor: theme.palette.success.main,
                    borderRadius: '50%',
                    width: 60,
                    height: 60,
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    boxShadow: 3
                  }}
                >
                  <Lightbulb sx={{ fontSize: 35, color: 'white' }} />
                </Box>
                <Typography variant="h5" sx={{ mt: 1, fontWeight: 'bold' }}>استراتيجيات المبيعات</Typography>
              </Box>
              <CardContent sx={{ flexGrow: 1, pt: 3 }}>
                <Typography variant="body1" paragraph>
                  توصيات مخصصة لتعزيز مبيعاتك باستخدام التحليلات المتقدمة وأنماط سلوك المستهلك.
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • تحديد فرص النمو
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • استراتيجيات للمنتجات الجديدة
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • تقنيات تحسين معدلات التحويل
                </Typography>
              </CardContent>
              <CardActions sx={{ p: 2, pt: 0 }}>
                <Button 
                  variant="outlined" 
                  color="success" 
                  href="/sales-strategy"
                  fullWidth
                  sx={{ 
                    borderRadius: 2,
                    py: 1,
                    '&:hover': {
                      backgroundColor: theme.palette.success.main,
                      color: 'white'
                    }
                  }}
                  endIcon={<ArrowBack />}
                >
                  اكتشف الآن
                </Button>
              </CardActions>
            </Card>
          </Grid>
        </Grid>
      </Container>

      {/* Benefits Section */}
      <Box sx={{ py: 6, backgroundColor: 'rgba(25, 118, 210, 0.05)' }}>
        <Container>
          <Typography
            variant="h4"
            align="center"
            gutterBottom
            sx={{ fontWeight: 'bold', mb: 4 }}
          >
            لماذا أستشر بياناتك؟
          </Typography>

          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Paper 
                elevation={0} 
                sx={{ 
                  p: 3, 
                  textAlign: 'center', 
                  height: '100%',
                  backgroundColor: 'transparent',
                  borderRadius: 3
                }}
              >
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: theme.palette.primary.main }}>
                  تحليلات متقدمة
                </Typography>
                <Typography>
                  استفد من خوارزميات الذكاء الاصطناعي لتحليل البيانات واستخراج رؤى قيمة لأعمالك
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper 
                elevation={0} 
                sx={{ 
                  p: 3, 
                  textAlign: 'center', 
                  height: '100%',
                  backgroundColor: 'transparent',
                  borderRadius: 3
                }}
              >
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: theme.palette.primary.main }}>
                  سهولة الاستخدام
                </Typography>
                <Typography>
                  واجهة بسيطة تتيح لك الوصول إلى معلومات معقدة دون الحاجة إلى خبرة تقنية
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper 
                elevation={0} 
                sx={{ 
                  p: 3, 
                  textAlign: 'center', 
                  height: '100%',
                  backgroundColor: 'transparent',
                  borderRadius: 3
                }}
              >
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: theme.palette.primary.main }}>
                  تحديثات مستمرة
                </Typography>
                <Typography>
                  نظام يتطور مع احتياجات عملك ويتكيف مع تغيرات السوق لضمان دقة النتائج
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        </Container>
      </Box>
    </Box>
  );
}

export default Home;