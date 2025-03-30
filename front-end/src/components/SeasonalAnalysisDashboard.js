import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Grid, 
  FormControl, 
  InputLabel,
  Select, 
  MenuItem, 
  Checkbox,
  ListItemText,
  OutlinedInput,
  CircularProgress,
  Paper,
  Divider,
  Button,
  Chip,
  useTheme,
  alpha
} from '@mui/material';
import { DateRange, Autorenew } from '@mui/icons-material';
import Chart from 'react-apexcharts';
import axios from 'axios';

const SeasonalAnalysisDashboard = () => {
  const theme = useTheme();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [salesData, setSalesData] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState(['all']); // Changed to array for multiple selections
  const [selectedYear, setSelectedYear] = useState('all');
  const [availableYears, setAvailableYears] = useState([]);

  // Fetch data from the API
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get('http://localhost:5000/api/visualization/seasonal-analysis');
      const data = response.data.monthly_demand_data || [];
      
      // Extract unique categories and years
      const uniqueCategories = [...new Set(data.map(item => item.القسم))];
      const uniqueYears = [...new Set(data.map(item => item.year))];
      
      setCategories(uniqueCategories);
      setAvailableYears(uniqueYears);
      setSalesData(data);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('فشل في جلب بيانات المبيعات الموسمية');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Handle category selection change
  const handleCategoryChange = (event) => {
    const value = event.target.value;
    
    // Handle "select all" option
    if (value.includes('all')) {
      // If "all" is being added, select only "all"
      if (!selectedCategories.includes('all')) {
        setSelectedCategories(['all']);
      } else {
        // If "all" is being removed, clear selection
        setSelectedCategories([]);
      }
    } else {
      // Regular selection handling
      setSelectedCategories(value.filter(item => item !== 'all'));
    }
  };

  // Calculate percentage-based color ranges
  const calculatePercentageBasedColorRanges = (series) => {
    // Find the maximum value in the dataset
    let maxValue = 0;
    series.forEach(seriesItem => {
      seriesItem.data.forEach(value => {
        if (value > maxValue) {
          maxValue = value;
        }
      });
    });

    // Create color ranges based on percentages of max value
    return [
      {
        from: 0,
        to: maxValue * 0.005, // 0-0.5% of max value
        name: 'منخفض',
        color: '#E9F7EF' // Very light green
      },
      {
        from: maxValue * 0.005,
        to: maxValue * 0.05, // 0.5-5% of max value
        name: 'متوسط-منخفض',
        color: '#ABEBC6' // Light green
      },
      {
        from: maxValue * 0.05,
        to: maxValue * 0.1, // 5-10% of max value
        name: 'متوسط',
        color: '#58D68D' // Medium green
      },
      {
        from: maxValue * 0.1,
        to: maxValue * 0.2, // 10-20% of max value
        name: 'متوسط-مرتفع',
        color: '#2ECC71' // Stronger green
      },
      {
        from: maxValue * 0.2,
        to: maxValue, // 20-100% of max value
        name: 'مرتفع',
        color: '#1D8348' // Dark green
      }
    ];
  };

  // Process data for heatmap based on selected categories and year
  const processHeatmapData = () => {
    if (!salesData.length) return { series: [], categories: [] };
    
    // Filter data based on selections
    let filteredData = [...salesData];
    
    // Handle category filtering
    if (!selectedCategories.includes('all') && selectedCategories.length > 0) {
      filteredData = filteredData.filter(item => selectedCategories.includes(item.القسم));
    }
    
    if (selectedYear !== 'all') {
      filteredData = filteredData.filter(item => item.year === parseInt(selectedYear));
    }
    
    // Group by category and month
    const categoriesData = {};
    const months = Array.from({ length: 12 }, (_, i) => i + 1);
    
    filteredData.forEach(item => {
      const category = item.القسم;
      const month = item.month;
      
      if (!categoriesData[category]) {
        categoriesData[category] = Array(12).fill(0);
      }
      
      categoriesData[category][month - 1] += item.total_quantity;
    });
    
    // Format for ApexCharts heatmap
    const series = Object.keys(categoriesData).map(category => ({
      name: category,
      data: categoriesData[category].map(value => value || 0)
    }));
    
    return {
      series,
      categories: months.map(month => {
        const date = new Date(2021, month - 1, 1);
        return date.toLocaleString('ar-EG', { month: 'long' });
      })
    };
  };

  // Updated heatmap options with dynamic color ranges
  const getHeatmapOptions = (heatmapData) => {
    const colorRanges = calculatePercentageBasedColorRanges(heatmapData.series);
    
    return {
      chart: {
        type: 'heatmap',
        height: 350,
        fontFamily: theme.typography.fontFamily,
      },
      dataLabels: {
        enabled: false
      },
      colors: ['#2ECC71'], // Base green color
      title: {
        text: 'تحليل المبيعات الشهرية حسب الفئة',
        align: 'center',
        style: {
          fontSize: '18px',
          fontWeight: 600,
          fontFamily: theme.typography.fontFamily
        }
      },
      plotOptions: {
        heatmap: {
          shadeIntensity: 0.8,
          radius: 0,
          useFillColorAsStroke: false,
          enableShades: true,
          distributed: false,
          colorScale: {
            ranges: colorRanges
          }
        }
      },
      xaxis: {
        categories: heatmapData.categories,
        labels: {
          style: {
            colors: theme.palette.text.secondary,
            fontFamily: theme.typography.fontFamily
          }
        }
      },
      yaxis: {
        labels: {
          style: {
            colors: theme.palette.text.secondary,
            fontFamily: theme.typography.fontFamily
          }
        }
      },
      grid: {
        padding: {
          right: 20
        }
      },
      tooltip: {
        y: {
          formatter: function (value) {
            return value;
          }
        }
      },
      legend: {
        height: 40,
        position: 'bottom'
      }
    };
  };

  // Process data for year-over-year comparison
  const processYearlyComparisonData = () => {
    if (!salesData.length) return { series: [], categories: [] };
    
    // Filter data based on selected categories
    let filteredData = [...salesData];
    
    // Handle category filtering
    if (!selectedCategories.includes('all') && selectedCategories.length > 0) {
      filteredData = filteredData.filter(item => selectedCategories.includes(item.القسم));
    }
    
    // Group by year and month
    const yearData = {};
    const months = Array.from({ length: 12 }, (_, i) => i + 1);
    
    filteredData.forEach(item => {
      const year = item.year;
      const month = item.month;
      
      if (!yearData[year]) {
        yearData[year] = Array(12).fill(0);
      }
      
      yearData[year][month - 1] += item.total_quantity;
    });
    
    // Format for ApexCharts line chart
    const series = Object.keys(yearData).map(year => ({
      name: `${year}`,
      type: 'line',
      data: yearData[year].map(value => value || 0)
    }));
    
    return {
      series,
      categories: months.map(month => {
        const date = new Date(2021, month - 1, 1);
        return date.toLocaleString('ar-EG', { month: 'short' });
      })
    };
  };

  // Process top performing categories by month
  const processTopCategoriesData = () => {
    if (!salesData.length) return { series: [], categories: [] };
    
    // Filter data based on selected year and categories
    let filteredData = [...salesData];
    
    if (selectedYear !== 'all') {
      filteredData = filteredData.filter(item => item.year === parseInt(selectedYear));
    }
    
    // For top categories, we'll use the selected categories if specified, otherwise all categories
    if (!selectedCategories.includes('all') && selectedCategories.length > 0) {
      filteredData = filteredData.filter(item => selectedCategories.includes(item.القسم));
    }
    
    // Calculate total sales by category
    const categoryTotals = {};
    
    filteredData.forEach(item => {
      const category = item.القسم;
      
      if (!categoryTotals[category]) {
        categoryTotals[category] = 0;
      }
      
      categoryTotals[category] += item.total_quantity;
    });
    
    // Sort categories by total sales and get top 5 (or all if less than 5)
    const topCategories = Object.entries(categoryTotals)
      .sort((a, b) => b[1] - a[1])
      .slice(0, Math.min(5, Object.keys(categoryTotals).length))
      .map(([category, value]) => ({ category, value }));
    
    return {
      series: [{ data: topCategories.map(item => item.value) }],
      categories: topCategories.map(item => item.category)
    };
  };

  // Process monthly sales pattern data
  const processMonthlySalesPatternData = () => {
    if (!salesData.length) return { series: [], categories: [] };
    
    // Filter data based on selected categories
    let filteredData = [...salesData];
    
    // Handle category filtering
    if (!selectedCategories.includes('all') && selectedCategories.length > 0) {
      filteredData = filteredData.filter(item => selectedCategories.includes(item.القسم));
    }
    
    // Group by month (across all years)
    const monthlyTotals = Array(12).fill(0);
    
    filteredData.forEach(item => {
      const month = item.month;
      monthlyTotals[month - 1] += item.total_quantity;
    });
    
    // Normalize the data for pattern visibility (percentage of yearly total)
    const totalSales = monthlyTotals.reduce((sum, val) => sum + val, 0);
    const normalizedData = monthlyTotals.map(val => ((totalSales > 0) ? (val / totalSales * 100).toFixed(1) : '0'));
    
    return {
      series: [{
        name: 'النسبة المئوية من المبيعات السنوية',
        data: normalizedData
      }],
      categories: Array.from({ length: 12 }, (_, i) => {
        const date = new Date(2021, i, 1);
        return date.toLocaleString('ar-EG', { month: 'short' });
      })
    };
  };

  const yearlyComparisonData = processYearlyComparisonData();
  const topCategoriesData = processTopCategoriesData();
  const monthlySalesPatternData = processMonthlySalesPatternData();

  const yearlyComparisonOptions = {
    chart: {
      height: 350,
      type: 'line',
      toolbar: {
        show: true
      },
      fontFamily: theme.typography.fontFamily
    },
    dataLabels: {
      enabled: false
    },
    stroke: {
      curve: 'smooth',
      width: 3
    },
    title: {
      text: 'مقارنة المبيعات السنوية',
      align: 'center',
      style: {
        fontSize: '18px',
        fontWeight: 600,
        fontFamily: theme.typography.fontFamily
      }
    },
    grid: {
      borderColor: '#e7e7e7',
      row: {
        colors: ['#f3f3f3', 'transparent'],
        opacity: 0.5
      },
    },
    markers: {
      size: 5
    },
    xaxis: {
      categories: yearlyComparisonData.categories,
      labels: {
        style: {
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily
        }
      }
    },
    yaxis: {
      title: {
        text: 'الكمية',
        style: {
          color: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily
        }
      },
      labels: {
        style: {
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily
        }
      }
    },
    legend: {
      position: 'top',
      horizontalAlign: 'right',
      floating: true,
      offsetY: -25,
      offsetX: -5
    },
    tooltip: {
      theme: theme.palette.mode
    }
  };

  const topCategoriesOptions = {
    chart: {
      type: 'bar',
      height: 350,
      fontFamily: theme.typography.fontFamily
    },
    plotOptions: {
      bar: {
        horizontal: true,
        borderRadius: 4,
        dataLabels: {
          position: 'top',
        },
      }
    },
    dataLabels: {
      enabled: true,
      formatter: function (val) {
        return val.toFixed(0);
      },
      offsetX: 20,
      style: {
        fontSize: '12px',
        colors: [theme.palette.text.primary],
        fontFamily: theme.typography.fontFamily
      }
    },
    stroke: {
      show: true,
      width: 1,
      colors: ['#fff']
    },
    title: {
      text: 'أعلى الفئات مبيعاً',
      align: 'center',
      style: {
        fontSize: '18px',
        fontWeight: 600,
        fontFamily: theme.typography.fontFamily
      }
    },
    xaxis: {
      categories: topCategoriesData.categories,
      labels: {
        style: {
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily
        }
      }
    },
    yaxis: {
      labels: {
        style: {
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily
        }
      }
    },
    colors: [theme.palette.primary.main],
    tooltip: {
      theme: theme.palette.mode
    }
  };

  const monthlySalesPatternOptions = {
    chart: {
      type: 'bar',
      height: 350,
      fontFamily: theme.typography.fontFamily
    },
    plotOptions: {
      bar: {
        borderRadius: 4,
        columnWidth: '70%',
      }
    },
    dataLabels: {
      enabled: true,
      formatter: function (val) {
        return val + '%';
      },
      style: {
        fontSize: '12px',
        colors: [theme.palette.getContrastText(theme.palette.info.main)],
        fontFamily: theme.typography.fontFamily
      }
    },
    title: {
      text: 'نمط المبيعات الموسمي',
      align: 'center',
      style: {
        fontSize: '18px',
        fontWeight: 600,
        fontFamily: theme.typography.fontFamily
      }
    },
    xaxis: {
      categories: monthlySalesPatternData.categories,
      labels: {
        style: {
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily
        }
      }
    },
    yaxis: {
      title: {
        text: 'النسبة المئوية من المبيعات السنوية',
        style: {
          color: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily
        }
      },
      labels: {
        formatter: function (val) {
          return val.toFixed(0) + '%';
        },
        style: {
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily
        }
      }
    },
    colors: [theme.palette.info.main],
    tooltip: {
      theme: theme.palette.mode
    }
  };

  // Find peak months
  const findPeakMonths = () => {
    if (!salesData.length) return [];
    
    const monthlyData = processMonthlySalesPatternData().series[0].data;
    const threshold = 10; // Consider months with >10% of yearly sales as peak months
    
    const peaks = monthlyData
      .map((value, index) => ({ value: parseFloat(value), month: index }))
      .filter(item => item.value > threshold)
      .sort((a, b) => b.value - a.value);
    
    return peaks.map(peak => {
      const date = new Date(2021, peak.month, 1);
      return {
        month: date.toLocaleString('ar-EG', { month: 'long' }),
        percentage: peak.value
      };
    });
  };

  const peakMonths = findPeakMonths();

  // Get category selection label for display
  const getCategorySelectionLabel = () => {
    if (selectedCategories.includes('all')) {
      return 'جميع الفئات';
    }
    
    if (selectedCategories.length <= 1) {
      return selectedCategories[0] || 'اختر الفئات';
    }
    
    return `${selectedCategories.length} فئات محددة`;
  };

  return (
    <Box sx={{ p: 3 }}>
      <Paper 
        elevation={0} 
        sx={{ 
          p: 2, 
          mb: 3, 
          borderRadius: 2, 
          background: `linear-gradient(to right, ${alpha(theme.palette.primary.main, 0.05)}, ${alpha(theme.palette.primary.light, 0.05)})`,
          border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`
        }}
      >
        <Typography variant="h5" sx={{ mb: 2, fontWeight: 'bold' }}>
          لوحة التحليل الموسمي
        </Typography>
        
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={4}>
            {/* Multiple category selection */}
            <FormControl fullWidth size="small">
              <InputLabel id="category-selection-label">الفئة</InputLabel>
              <Select
                labelId="category-selection-label"
                multiple
                value={selectedCategories}
                onChange={handleCategoryChange}
                input={<OutlinedInput label="الفئة" />}
                renderValue={getCategorySelectionLabel}
                MenuProps={{
                  PaperProps: {
                    style: {
                      maxHeight: 300
                    }
                  }
                }}
              >
                <MenuItem value="all">
                  <Checkbox checked={selectedCategories.includes('all')} />
                  <ListItemText primary="جميع الفئات" />
                </MenuItem>
                {categories.map(category => (
                  <MenuItem key={category} value={category}>
                    <Checkbox checked={selectedCategories.includes(category)} />
                    <ListItemText primary={category} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} sm={4} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>السنة</InputLabel>
              <Select
                value={selectedYear}
                onChange={(e) => setSelectedYear(e.target.value)}
                label="السنة"
              >
                <MenuItem value="all">جميع السنوات</MenuItem>
                {availableYears.map(year => (
                  <MenuItem key={year} value={year}>{year}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} sm={4} md={3}>
            <Button
              variant="outlined"
              startIcon={<Autorenew />}
              onClick={fetchData}
              fullWidth
              sx={{ height: '40px' }}
            >
              تحديث البيانات
            </Button>
          </Grid>
          
          {/* Display selected categories as chips */}
          {!selectedCategories.includes('all') && selectedCategories.length > 0 && (
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                {selectedCategories.map(category => (
                  <Chip 
                    key={category} 
                    label={category} 
                    color="primary" 
                    variant="outlined"
                    onDelete={() => setSelectedCategories(prev => prev.filter(c => c !== category))}
                    size="small"
                  />
                ))}
              </Box>
            </Grid>
          )}
        </Grid>
      </Paper>
      
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Paper sx={{ p: 3, textAlign: 'center', color: 'error.main' }}>
          <Typography>{error}</Typography>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {/* Monthly Heatmap - IMPROVED with percent-based color ranges */}
          <Grid item xs={12}>
            <Card elevation={2} sx={{ borderRadius: 2 }}>
              <CardContent>
                {/* Use dynamic options function for the heatmap */}
                <Chart 
                  options={getHeatmapOptions(processHeatmapData())} 
                  series={processHeatmapData().series} 
                  type="heatmap" 
                  height={350} 
                />
              </CardContent>
            </Card>
          </Grid>
          
          {/* Monthly Sales Pattern */}
          <Grid item xs={12} md={6}>
            <Card elevation={2} sx={{ borderRadius: 2 }}>
              <CardContent>
                <Chart 
                  options={monthlySalesPatternOptions} 
                  series={monthlySalesPatternData.series} 
                  type="bar" 
                  height={350} 
                />
              </CardContent>
            </Card>
          </Grid>
          
          {/* Top Categories */}
          <Grid item xs={12} md={6}>
            <Card elevation={2} sx={{ borderRadius: 2 }}>
              <CardContent>
                <Chart 
                  options={topCategoriesOptions} 
                  series={topCategoriesData.series} 
                  type="bar" 
                  height={350} 
                />
              </CardContent>
            </Card>
          </Grid>
          
          {/* Year over Year Comparison */}
          <Grid item xs={12}>
            <Card elevation={2} sx={{ borderRadius: 2 }}>
              <CardContent>
                <Chart 
                  options={yearlyComparisonOptions} 
                  series={yearlyComparisonData.series} 
                  type="line" 
                  height={350} 
                />
              </CardContent>
            </Card>
          </Grid>
          
          {/* Key Seasonal Insights */}
          <Grid item xs={12}>
            <Card 
              elevation={2} 
              sx={{ 
                borderRadius: 2, 
                backgroundColor: alpha(theme.palette.info.light, 0.05),
                border: `1px solid ${alpha(theme.palette.info.main, 0.1)}`
              }}
            >
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: theme.palette.info.dark }}>
                  <DateRange sx={{ verticalAlign: 'middle', mr: 1 }} />
                  أنماط موسمية بارزة
                </Typography>
                <Divider sx={{ my: 1 }} />
                <Box sx={{ mt: 2 }}>
                  <Typography paragraph>
                    <strong>• مواسم ذروة المبيعات:</strong> {peakMonths.length > 0 ? (
                      peakMonths.map(peak => `${peak.month} (${peak.percentage}%)`).join('، ')
                    ) : 'لا توجد بيانات كافية'}
                  </Typography>
                  {!selectedCategories.includes('all') && selectedCategories.length === 1 && (
                    <Typography paragraph>
                      <strong>• أداء الفئة:</strong> فئة {selectedCategories[0]} تظهر {
                        yearlyComparisonData.series.length > 1 
                          ? 'نمواً مستمراً عبر السنوات المختلفة'
                          : 'نمطاً موسمياً واضحاً'
                      }
                    </Typography>
                  )}
                  {!selectedCategories.includes('all') && selectedCategories.length > 1 && (
                    <Typography paragraph>
                      <strong>• أداء الفئات المختارة:</strong> الفئات المحددة تظهر {
                        yearlyComparisonData.series.length > 1 
                          ? 'نمواً متفاوتاً عبر السنوات المختلفة'
                          : 'أنماطاً موسمية متباينة'
                      }
                    </Typography>
                  )}
                  <Typography>
                    <strong>• توصيات التخطيط:</strong> زيادة المخزون قبل شهر من بداية مواسم الذروة المحددة
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default SeasonalAnalysisDashboard;