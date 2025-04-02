import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  CircularProgress,
  Alert,
  Switch,
  FormControlLabel,
  Tabs,
  Tab,
  Chip,
  alpha,
  useTheme,
  Button
} from '@mui/material';
import { DateRange, ShowChart, TrendingUp, Category, Inventory2 } from '@mui/icons-material';
import axios from 'axios';
import Chart from 'react-apexcharts';

const ItemDemandForecast = () => {
  const theme = useTheme();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [itemData, setItemData] = useState({});
  const [categories, setCategories] = useState([]);
  const [specifications, setSpecifications] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedSpecification, setSelectedSpecification] = useState('');
  const [selectedMonth, setSelectedMonth] = useState('');
  const [showQuantity, setShowQuantity] = useState(true);
  const [showSales, setShowSales] = useState(true);
  
  // Month names in Arabic
  const monthNames = [
    'يناير',
    'فبراير',
    'مارس',
    'أبريل',
    'مايو',
    'يونيو',
    'يوليو',
    'أغسطس',
    'سبتمبر',
    'أكتوبر',
    'نوفمبر',
    'ديسمبر'
  ];

  // Fetch item forecast data on component mount
  useEffect(() => {
    fetchItemForecastData();
  }, []);

  // Update specifications when category changes
  useEffect(() => {
    if (selectedCategory && itemData[selectedCategory]) {
      const specs = Object.keys(itemData[selectedCategory]);
      setSpecifications(specs);
      if (specs.length > 0 && !specs.includes(selectedSpecification)) {
        setSelectedSpecification(specs[0]);
      }
    } else {
      setSpecifications([]);
      setSelectedSpecification('');
    }
  }, [selectedCategory, itemData]);

  const fetchItemForecastData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get('http://localhost:5000/api/visualization/item-demand-forecasting');
      
      if (!response.data.item_demand_data || Object.keys(response.data.item_demand_data).length === 0) {
        setError('لا توجد بيانات متاحة للتوقعات على مستوى المنتجات. يرجى تشغيل نظام التنبؤ الذكي أولاً.');
        setItemData({});
        setCategories([]);
      } else {
        setItemData(response.data.item_demand_data);
        
        // Extract categories
        const cats = Object.keys(response.data.item_demand_data);
        setCategories(cats);
        if (cats.length > 0 && !selectedCategory) {
          setSelectedCategory(cats[0]);
        }
      }
    } catch (err) {
      console.error('Error fetching item forecast data:', err);
      setError('فشل في جلب بيانات التوقعات على مستوى المنتجات.');
    } finally {
      setLoading(false);
    }
  };

  const runAIForecast = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // This would call your backend to run the AI forecast
      await axios.post('http://localhost:5000/api/demand-forecasting/run-ai-forecast');
      
      // Reload data
      fetchItemForecastData();
      
    } catch (err) {
      console.error('Error running AI forecast:', err);
      setError('فشل في تشغيل نظام التنبؤ الذكي.');
    } finally {
      setLoading(false);
    }
  };

  // Process data for quantity chart
  const processQuantityData = () => {
    if (!selectedCategory || !selectedSpecification || 
        !itemData[selectedCategory] || !itemData[selectedCategory][selectedSpecification]) {
      return [];
    }
    
    const specData = itemData[selectedCategory][selectedSpecification];
    const months = Array.from({ length: 12 }, (_, i) => (i + 1).toString());
    
    // Create series in the format required by ApexCharts
    const quantityData = months.map(month => {
      return {
        x: monthNames[parseInt(month) - 1],
        y: Math.round(specData[month]?.quantity || 0)
      };
    });
    
    return [{
      name: 'الكمية المتوقعة',
      data: quantityData
    }];
  };

  // Process data for sales chart
  const processSalesData = () => {
    if (!selectedCategory || !selectedSpecification || 
        !itemData[selectedCategory] || !itemData[selectedCategory][selectedSpecification]) {
      return [];
    }
    
    const specData = itemData[selectedCategory][selectedSpecification];
    const months = Array.from({ length: 12 }, (_, i) => (i + 1).toString());
    
    // Create series in the format required by ApexCharts
    const salesData = months.map(month => {
      return {
        x: monthNames[parseInt(month) - 1],
        y: Math.round(specData[month]?.money_sold || 0)
      };
    });
    
    return [{
      name: 'المبيعات المتوقعة',
      data: salesData
    }];
  };

  // Process data for comparison chart (compare different items in the same category)
  const processComparisonData = () => {
    if (!selectedCategory || !itemData[selectedCategory]) {
      return [];
    }
    
    const categorySpecs = itemData[selectedCategory];
    const months = Array.from({ length: 12 }, (_, i) => (i + 1).toString());
    
    // Get top 5 items by total predicted quantity
    const itemTotals = Object.entries(categorySpecs).map(([spec, data]) => {
      const total = Object.values(data).reduce((sum, month) => sum + (month.quantity || 0), 0);
      return { spec, total };
    }).sort((a, b) => b.total - a.total).slice(0, 5);
    
    // Create series for each top item
    return itemTotals.map(item => {
      const specData = categorySpecs[item.spec];
      
      return {
        name: item.spec,
        data: months.map(month => Math.round(specData[month]?.quantity || 0))
      };
    });
  };

  const quantitySeries = processQuantityData();
  const salesSeries = processSalesData();
  const comparisonSeries = processComparisonData();

  // Quantity chart options
  const quantityChartOptions = {
    chart: {
      type: 'bar',
      height: 350,
      fontFamily: theme.typography.fontFamily,
      toolbar: {
        show: true
      }
    },
    title: {
      text: 'توقعات الكمية الشهرية',
      align: 'center',
      style: {
        fontSize: '18px',
        fontWeight: 600,
        fontFamily: theme.typography.fontFamily
      }
    },
    xaxis: {
      categories: monthNames,
      labels: {
        style: {
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
        }
      }
    },
    yaxis: {
      title: {
        text: 'الكمية',
        style: { 
          color: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
          fontWeight: 500
        },
      },
      labels: {
        style: { 
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily
        },
        formatter: (value) => Math.round(value),
      },
    },
    colors: [theme.palette.primary.main],
    plotOptions: {
      bar: {
        columnWidth: '60%',
        borderRadius: 4,
      }
    },
    dataLabels: {
      enabled: false,
    },
    tooltip: {
      theme: theme.palette.mode,
      y: {
        formatter: (value) => Math.round(value),
      },
      style: {
        fontFamily: theme.typography.fontFamily
      }
    }
  };

  // Sales chart options
  const salesChartOptions = {
    chart: {
      type: 'bar',
      height: 350,
      fontFamily: theme.typography.fontFamily,
      toolbar: {
        show: true
      }
    },
    title: {
      text: 'توقعات المبيعات الشهرية',
      align: 'center',
      style: {
        fontSize: '18px',
        fontWeight: 600,
        fontFamily: theme.typography.fontFamily
      }
    },
    xaxis: {
      categories: monthNames,
      labels: {
        style: { 
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
        }
      }
    },
    yaxis: {
      title: {
        text: 'المبيعات (جنيه)',
        style: { 
          color: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
          fontWeight: 500
        },
      },
      labels: {
        style: { 
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily
        },
        formatter: (value) => Math.round(value),
      },
    },
    colors: [theme.palette.success.main],
    plotOptions: {
      bar: {
        columnWidth: '60%',
        borderRadius: 4,
      }
    },
    dataLabels: {
      enabled: false,
    },
    tooltip: {
      theme: theme.palette.mode,
      y: {
        formatter: (value) => `${Math.round(value)} جنيه`,
      },
      style: {
        fontFamily: theme.typography.fontFamily
      }
    }
  };

  // Comparison chart options
  const comparisonChartOptions = {
    chart: {
      type: 'line',
      height: 350,
      fontFamily: theme.typography.fontFamily,
      toolbar: {
        show: true
      }
    },
    title: {
      text: 'مقارنة توقعات أعلى 5 منتجات',
      align: 'center',
      style: {
        fontSize: '18px',
        fontWeight: 600,
        fontFamily: theme.typography.fontFamily
      }
    },
    xaxis: {
      categories: monthNames,
      labels: {
        style: { 
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
        }
      }
    },
    yaxis: {
      title: {
        text: 'الكمية',
        style: { 
          color: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
          fontWeight: 500
        },
      },
      labels: {
        style: { 
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily
        },
        formatter: (value) => Math.round(value),
      },
    },
    colors: [
      theme.palette.primary.main,
      theme.palette.secondary.main,
      theme.palette.success.main,
      theme.palette.info.main,
      theme.palette.warning.main
    ],
    stroke: {
      width: 3,
      curve: 'smooth',
    },
    markers: {
      size: 4,
      hover: {
        size: 6
      }
    },
    tooltip: {
      theme: theme.palette.mode,
      y: {
        formatter: (value) => Math.round(value),
      },
      style: {
        fontFamily: theme.typography.fontFamily
      }
    },
    legend: {
      position: 'top',
      horizontalAlign: 'right',
      fontFamily: theme.typography.fontFamily
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Card elevation={0} sx={{ mb: 3, p: 2, borderRadius: 3, bgcolor: alpha(theme.palette.primary.main, 0.05) }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>القسم</InputLabel>
              <Select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                label="القسم"
              >
                {categories.map(category => (
                  <MenuItem key={category} value={category}>{category}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>المنتج</InputLabel>
              <Select
                value={selectedSpecification}
                onChange={(e) => setSelectedSpecification(e.target.value)}
                label="المنتج"
                disabled={!selectedCategory || specifications.length === 0}
              >
                {specifications.map(spec => (
                  <MenuItem key={spec} value={spec}>{spec}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={6} md={3}>
            <FormControlLabel
              control={
                <Switch
                  checked={showQuantity}
                  onChange={(e) => setShowQuantity(e.target.checked)}
                  color="primary"
                />
              }
              label="عرض الكمية"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={showSales}
                  onChange={(e) => setShowSales(e.target.checked)}
                  color="success"
                />
              }
              label="عرض المبيعات"
            />
          </Grid>
          
          <Grid item xs={6} md={3}>
            <Button
              fullWidth
              variant="contained"
              color="primary"
              onClick={runAIForecast}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <ShowChart />}
            >
              تشغيل نظام التنبؤ الذكي
            </Button>
          </Grid>
        </Grid>
      </Card>
      
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="warning" sx={{ mb: 3 }}>{error}</Alert>
      ) : (
        <Grid container spacing={3}>
          {showQuantity && selectedCategory && selectedSpecification && (
            <Grid item xs={12} md={6}>
              <Card elevation={2} sx={{ p: 2, borderRadius: 3 }}>
                <Chart
                  options={quantityChartOptions}
                  series={quantitySeries}
                  type="bar"
                  height={350}
                />
              </Card>
            </Grid>
          )}
          
          {showSales && selectedCategory && selectedSpecification && (
            <Grid item xs={12} md={6}>
              <Card elevation={2} sx={{ p: 2, borderRadius: 3 }}>
                <Chart
                  options={salesChartOptions}
                  series={salesSeries}
                  type="bar"
                  height={350}
                />
              </Card>
            </Grid>
          )}
          
          {selectedCategory && (
            <Grid item xs={12}>
              <Card elevation={2} sx={{ p: 2, borderRadius: 3 }}>
                <Chart
                  options={comparisonChartOptions}
                  series={comparisonSeries}
                  type="line"
                  height={400}
                />
              </Card>
            </Grid>
          )}
          
          {/* Item Analysis Panel */}
          {selectedCategory && selectedSpecification && (
            <Grid item xs={12}>
              <Card elevation={2} sx={{ p: 3, borderRadius: 3 }}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
                  تحليل توقعات المنتج
                </Typography>
                
                <Grid container spacing={3} sx={{ mt: 1 }}>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ p: 2, borderRadius: 2, bgcolor: alpha(theme.palette.info.main, 0.1) }}>
                      <Typography variant="subtitle1" color="info.main" fontWeight="bold" gutterBottom>
                        إجمالي الكمية المتوقعة للعام
                      </Typography>
                      
                      {quantitySeries.length > 0 && quantitySeries[0].data && (
                        <Typography variant="h4" sx={{ mt: 2, mb: 1 }}>
                          {Math.round(quantitySeries[0].data.reduce((sum, item) => sum + item.y, 0)).toLocaleString()}
                        </Typography>
                      )}
                      
                      <Typography variant="body2" color="text.secondary">
                        قطعة / وحدة
                      </Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} md={4}>
                    <Box sx={{ p: 2, borderRadius: 2, bgcolor: alpha(theme.palette.success.main, 0.1) }}>
                      <Typography variant="subtitle1" color="success.main" fontWeight="bold" gutterBottom>
                        إجمالي المبيعات المتوقعة للعام
                      </Typography>
                      
                      {salesSeries.length > 0 && salesSeries[0].data && (
                        <Typography variant="h4" sx={{ mt: 2, mb: 1 }}>
                          {Math.round(salesSeries[0].data.reduce((sum, item) => sum + item.y, 0)).toLocaleString()}
                        </Typography>
                      )}
                      
                      <Typography variant="body2" color="text.secondary">
                        جنيه مصري
                      </Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} md={4}>
                    <Box sx={{ p: 2, borderRadius: 2, bgcolor: alpha(theme.palette.warning.main, 0.1) }}>
                      <Typography variant="subtitle1" color="warning.main" fontWeight="bold" gutterBottom>
                        متوسط سعر البيع
                      </Typography>
                      
                      {salesSeries.length > 0 && salesSeries[0].data && quantitySeries.length > 0 && quantitySeries[0].data && (
                        <Typography variant="h4" sx={{ mt: 2, mb: 1 }}>
                          {Math.round(
                            salesSeries[0].data.reduce((sum, item) => sum + item.y, 0) / 
                            Math.max(1, quantitySeries[0].data.reduce((sum, item) => sum + item.y, 0))
                          ).toLocaleString()}
                        </Typography>
                      )}
                      
                      <Typography variant="body2" color="text.secondary">
                        جنيه مصري / وحدة
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
                
                {/* Peak Months Analysis */}
                <Box sx={{ mt: 3 }}>
                  <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                    أشهر الذروة المتوقعة
                  </Typography>
                  
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 2 }}>
                    {quantitySeries.length > 0 && quantitySeries[0].data && (
                      quantitySeries[0].data
                        .map((item, index) => ({ month: item.x, value: item.y, index }))
                        .sort((a, b) => b.value - a.value)
                        .slice(0, 3)
                        .map(peak => (
                          <Chip
                            key={peak.index}
                            label={peak.month}
                            color="primary"
                            variant="outlined"
                            size="medium"
                            sx={{ px: 1 }}
                          />
                        ))
                    )}
                  </Box>
                  
                  <Typography variant="body2" sx={{ mt: 2 }}>
                    يجب التخطيط للمخزون بشكل مسبق قبل هذه الأشهر لتجنب نفاد المخزون خلال فترات الذروة المتوقعة.
                  </Typography>
                </Box>
              </Card>
            </Grid>
          )}
        </Grid>
      )}
    </Box>
  );
};

export default ItemDemandForecast;