import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  ListItemText,
  Chip,
  Divider,
  alpha,
  useTheme,
  Stack,
  Switch,
  FormControlLabel,
  OutlinedInput,
  RadioGroup,
  Radio,
  FormLabel
} from '@mui/material';
import { 
  BarChart as BarChartIcon, 
  TrendingUp, 
  PieChart as PieChartIcon, 
  ShowChart,
  QueryStats,
  DateRange,
  MonetizationOn,
  LocalAtm,
  ProductionQuantityLimits
} from '@mui/icons-material';
import Chart from 'react-apexcharts';
import axios from 'axios';
import _ from 'lodash';

const CategoryPerformanceDashboard = () => {
  const theme = useTheme();
  
  // State management
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [categories, setCategories] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [selectedTab, setSelectedTab] = useState(0); // 0: Comparison, 1: Sales Share, 2: Growth, 3: Performance
  const [timeframe, setTimeframe] = useState('monthly');
  const [startYear, setStartYear] = useState('');
  const [endYear, setEndYear] = useState('');
  const [showGrowthRate, setShowGrowthRate] = useState(true);
  const [allCategoriesSelected, setAllCategoriesSelected] = useState(true);
  const [salesShareData, setSalesShareData] = useState([]);
  const [quantitySalesShareData, setQuantitySalesShareData] = useState([]);  // New state for quantity-based sales share
  const [growthRates, setGrowthRates] = useState([]);
  
  // New state for data metric selection
  const [dataMetric, setDataMetric] = useState('money'); // 'money' or 'quantity'
  
  // Define a consistent color mapping for categories
  const getColorPalette = () => {
    return [
      '#1976D2', // Blue - حريمى
      '#E91E63', // Pink - رجالى
      '#4CAF50', // Green - مدارس
      '#2196F3', // Light Blue - اطفال
      '#FF9800', // Orange - احذية حريمى
      '#F44336', // Red - داخلى حريمى
      '#9C27B0', // Purple - احذية رجالى
      '#00BCD4', // Cyan - داخلى رجالى
      '#8BC34A', // Light Green - داخلى اطفال
      '#FF5722', // Deep Orange
      '#607D8B', // Blue Grey
      '#3F51B5', // Indigo
      '#009688', // Teal
      '#CDDC39', // Lime
      '#FFC107', // Amber
      '#795548', // Brown
      '#673AB7', // Deep Purple
      '#FFEB3B', // Yellow
      '#03A9F4', // Light Blue
      '#9E9E9E', // Grey
    ];
  };

  // Function to get consistent color index for a category
  const getCategoryColorIndex = (categoryName) => {
    // Create a map of categories to consistent color indices
    const categoryMap = {
      'حريمى': 0,
      'رجالى': 1,
      'مدارس': 2,
      'اطفال': 3,
      'احذية حريمى': 4,
      'داخلى حريمى': 5,
      'احذية رجالى': 6,
      'داخلى رجالى': 7,
      'داخلى اطفال': 8
    };
    
    // If the category is known, return its index, otherwise return a hash-based index
    if (categoryName in categoryMap) {
      return categoryMap[categoryName];
    }
    
    // Fallback - use string hash as backup for unknown categories
    let hash = 0;
    for (let i = 0; i < categoryName.length; i++) {
      hash = ((hash << 5) - hash) + categoryName.charCodeAt(i);
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash) % getColorPalette().length;
  };

  // Set current year for year pickers
  useEffect(() => {
    const today = new Date();
    const currentYear = today.getFullYear();
    
    // Set end year to current year
    setEndYear(currentYear.toString());
    
    // Set start year to 3 years ago
    setStartYear((currentYear - 3).toString());
  }, []);

  // Fetch data from API
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // First, try fetching from real API
      let response;
      try {
        // Build the URL with query parameters
        let url = `http://localhost:5000/api/visualization/category-performance?group_by=${timeframe}`;
        
        if (selectedCategories.length > 0 && !allCategoriesSelected) {
          url += `&categories=${selectedCategories.join(',')}`;
        }
        
        if (startYear) {
          url += `&start_year=${startYear}`;
        }
        
        if (endYear) {
          url += `&end_year=${endYear}`;
        }
        
        // Add data metric parameter
        url += `&metric=${dataMetric}`;
        
        console.log('Fetching data from:', url);
        response = await axios.get(url);
        
        // Process the data
        if (response.data.status === 'success') {
          setData(response.data.performance_data || []);
          setSalesShareData(response.data.market_share || []);
          setGrowthRates(response.data.growth_rates || []);
          
          // Extract unique categories
          const uniqueCategories = [...new Set(response.data.performance_data.map(item => item.Category))];
          setCategories(prevCategories => {
            return [...new Set([...prevCategories, ...uniqueCategories])];
          });
          
          if (selectedCategories.length === 0 || allCategoriesSelected) {
            setSelectedCategories(uniqueCategories);
          }
        } else {
          throw new Error(response.data.message || 'Failed to fetch data');
        }
      } catch (apiError) {
        console.warn('Could not load from API, using sample data instead:', apiError);
        // Fallback to sample data
        generateAndUseSampleData();
      }
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('فشل في جلب بيانات أداء الفئات');
    } finally {
      setLoading(false);
    }
  };

  // Generate sample data for demonstration
  const generateAndUseSampleData = () => {
    const sampleCategories = ['حريمى', 'رجالى', 'مدارس', 'اطفال', 'احذية حريمى', 'داخلى حريمى', 'احذية رجالى', 'داخلى رجالى', 'داخلى اطفال'];
    const startDate = new Date(2021, 0, 1);
    const endDate = new Date(2023, 11, 31);
    const sampleData = [];
    const sampleSalesShare = [];
    const sampleQuantityShare = [];
    const sampleGrowthRates = [];
    
    // First generate totals for sales share calculation
    const categoryTotals = {};
    const categoryQuantities = {};
    
    sampleCategories.forEach((category, index) => {
      let baseValue;
      let baseQuantity;
      
      // Make first categories have higher values
      if (index === 0) {
        baseValue = 25000000 + Math.random() * 5000000;
        baseQuantity = 120000 + Math.random() * 30000;
      }
      else if (index === 1) {
        baseValue = 15000000 + Math.random() * 2000000;
        baseQuantity = 90000 + Math.random() * 20000;
      }
      else if (index === 2) {
        baseValue = 10000000 + Math.random() * 2000000;
        baseQuantity = 60000 + Math.random() * 15000;
      }
      else {
        baseValue = 7000000 - (index * 1000000) + Math.random() * 1000000;
        baseQuantity = 40000 - (index * 5000) + Math.random() * 10000;
      }
      
      categoryTotals[category] = baseValue;
      categoryQuantities[category] = baseQuantity;
      
      sampleSalesShare.push({
        name: category,
        value: Math.round(baseValue)
      });
      
      sampleQuantityShare.push({
        name: category,
        value: Math.round(baseQuantity)
      });
    });
    
    // Generate monthly data for each category
    for (let category of sampleCategories) {
      let currentDate = new Date(startDate);
      let baseSales = categoryTotals[category] / 24; // Distribute across months
      let baseQuantity = categoryQuantities[category] / 24;
      
      while (currentDate <= endDate) {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth() + 1;
        
        // Add seasonality pattern
        const seasonalFactor = 1 + 0.3 * Math.sin((month / 12) * 2 * Math.PI);
        // Add growth trend
        const daysSinceStart = (currentDate - startDate) / (1000 * 60 * 60 * 24);
        const growthFactor = 1 + (daysSinceStart / 365) * 0.15;
        // Add some randomness
        const randomFactor = 0.85 + Math.random() * 0.3;
        
        const sales = baseSales * seasonalFactor * growthFactor * randomFactor;
        const quantity = baseQuantity * seasonalFactor * growthFactor * randomFactor;
        
        sampleData.push({
          year: year,
          month: month,
          Category: category,
          Date: `${year}-${String(month).padStart(2, '0')}-01`,
          Sales: Math.round(sales * 100) / 100,
          Quantity: Math.round(quantity)
        });
        
        // Move to next month
        currentDate.setMonth(currentDate.getMonth() + 1);
      }
      
      // Add growth rates data
      sampleGrowthRates.push({
        Category: category,
        year: 2023,
        previousYear: 2022,
        growthRate: Math.round((Math.random() * 40 - 10) * 10) / 10, // -10% to +30%
        currentSales: Math.round(baseSales * 12 * 1.2),
        previousSales: Math.round(baseSales * 12),
        currentQuantity: Math.round(baseQuantity * 12 * 1.2),
        previousQuantity: Math.round(baseQuantity * 12)
      });
    }
    
    // Update state with sample data
    setData(sampleData);
    setSalesShareData(sampleSalesShare);
    setQuantitySalesShareData(sampleQuantityShare);
    setGrowthRates(sampleGrowthRates);
    setCategories(sampleCategories);
    if (selectedCategories.length === 0 || allCategoriesSelected) {
      setSelectedCategories(sampleCategories);
    }
  };

  // Process sales and quantity share data from raw data
  const processShareData = () => {
    if (!data.length) return { salesShare: [], quantityShare: [] };
    
    // Filter data for selected categories
    const filteredData = data.filter(item => selectedCategories.includes(item.Category));
    
    // Group by category and calculate totals
    const categorySales = {};
    const categoryQuantities = {};
    
    filteredData.forEach(item => {
      const category = item.Category;
      
      if (!categorySales[category]) {
        categorySales[category] = 0;
        categoryQuantities[category] = 0;
      }
      
      categorySales[category] += item.Sales || 0;
      categoryQuantities[category] += item.Quantity || 0;
    });
    
    // Format for pie chart
    const salesShare = Object.keys(categorySales).map(category => ({
      name: category,
      value: Math.round(categorySales[category])
    }));
    
    const quantityShare = Object.keys(categoryQuantities).map(category => ({
      name: category,
      value: Math.round(categoryQuantities[category])
    }));
    
    return { salesShare, quantityShare };
  };

  // Initial data fetch
  useEffect(() => {
    fetchData();
  }, []);

  // Refetch data when metric changes
  useEffect(() => {
    if (data.length > 0) {
      fetchData();
    }
  }, [dataMetric]);

  // Process and update sales share data when raw data or selected categories change
  useEffect(() => {
    if (data.length > 0) {
      const { salesShare, quantityShare } = processShareData();
      setSalesShareData(salesShare);
      setQuantitySalesShareData(quantityShare);
    }
  }, [data, selectedCategories]);

  // Handle category selection change
  const handleCategoryChange = (event) => {
    const value = event.target.value;
    if (value[value.length - 1] === 'all') {
      setSelectedCategories(categories.length === selectedCategories.length ? [] : [...categories]);
      setAllCategoriesSelected(!allCategoriesSelected);
      return;
    }
    setSelectedCategories(value);
    setAllCategoriesSelected(false);
  };

  // Handle data metric change
  const handleDataMetricChange = (event) => {
    setDataMetric(event.target.value);
  };

  // Process data for category comparison
  const processCategoryComparisonData = () => {
    if (!data.length || !selectedCategories.length) return [];
    
    const filteredData = data.filter(item => selectedCategories.includes(item.Category));
    
    // Group by date
    const groupedByDate = {};
    filteredData.forEach(item => {
      if (!groupedByDate[item.Date]) {
        groupedByDate[item.Date] = { date: item.Date };
      }
      // Use the appropriate metric based on user selection
      const value = dataMetric === 'money' ? item.Sales : item.Quantity;
      groupedByDate[item.Date][item.Category] = value;
    });
    
    // Convert to array and sort by date
    return Object.values(groupedByDate).sort((a, b) => new Date(a.date) - new Date(b.date));
  };

  // Process data for growth trends
  const processGrowthTrendsData = () => {
    if (!data.length || !selectedCategories.length) return [];
    
    // Group data by category and year
    const categoryYearData = {};
    
    // Get all years in the data
    const years = [...new Set(data.map(item => item.year))].sort();
    
    // Use selected years from filter if available
    const startYearNum = parseInt(startYear);
    const endYearNum = parseInt(endYear);
    
    // Get actual earliest and latest years in our filtered dataset
    const filteredData = data.filter(item => selectedCategories.includes(item.Category));
    const filteredYears = [...new Set(filteredData.map(item => item.year))].sort();
    const firstYear = filteredYears[0];
    const lastYear = filteredYears[filteredYears.length - 1];
    
    // Calculate total sales/quantity per category per year
    filteredData.forEach(item => {
      const category = item.Category;
      const year = item.year;
      
      if (!categoryYearData[category]) {
        categoryYearData[category] = {};
      }
      
      if (!categoryYearData[category][year]) {
        categoryYearData[category][year] = 0;
      }
      
      // Use appropriate metric
      const value = dataMetric === 'money' ? item.Sales : item.Quantity;
      categoryYearData[category][year] += value;
    });
    
    // Calculate growth rates
    const growthResults = [];
    
    selectedCategories.forEach(category => {
      if (!categoryYearData[category]) return;
      
      // Get first and last year values for each category
      const firstYearValue = categoryYearData[category][firstYear] || 0;
      const lastYearValue = categoryYearData[category][lastYear] || 0;
      
      // Skip if no data for either year
      if (firstYearValue === 0) return;
      
      // Calculate total growth percentage
      const totalGrowth = ((lastYearValue - firstYearValue) / firstYearValue) * 100;
      
      // Calculate CAGR for multi-year ranges
      const yearDiff = lastYear - firstYear;
      let growthRate;
      
      if (yearDiff > 1) {
        // Use CAGR formula: (lastValue/firstValue)^(1/years) - 1
        growthRate = (Math.pow(lastYearValue / firstYearValue, 1 / yearDiff) - 1) * 100;
      } else {
        // For single year difference, use simple percentage change
        growthRate = totalGrowth;
      }

      // Collect all years' values for this category
      const yearValues = {};
      filteredYears.forEach(year => {
        yearValues[year] = categoryYearData[category][year] || 0;
      });
      
      // Use appropriate field names based on the data metric
      const metricFields = dataMetric === 'money' 
        ? {
            currentValue: lastYearValue,
            previousValue: firstYearValue,
            displayName: 'مبيعات'
          }
        : {
            currentValue: lastYearValue,
            previousValue: firstYearValue,
            displayName: 'كمية'
          };
      
      growthResults.push({
        Category: category,
        year: lastYear,
        previousYear: firstYear,
        growthRate: Math.round(growthRate * 10) / 10, // Round to 1 decimal place
        currentValue: metricFields.currentValue,
        previousValue: metricFields.previousValue,
        displayName: metricFields.displayName,
        yearValues: yearValues,
        allYears: filteredYears
      });
    });
    
    return growthResults;
  };

  // Calculate seasonal trends
  const calculateSeasonalTrends = () => {
    if (!data.length) return [];
    
    // Filter data for selected categories
    const filteredData = data.filter(item => selectedCategories.includes(item.Category));
    
    // Group data by month across all years
    const monthlyData = filteredData.reduce((acc, item) => {
      const month = new Date(item.Date).getMonth() + 1;
      
      if (!acc[month]) {
        acc[month] = { month, total: 0, count: 0 };
      }
      
      // Use appropriate metric
      const value = dataMetric === 'money' ? item.Sales : item.Quantity;
      acc[month].total += value;
      acc[month].count += 1;
      
      return acc;
    }, {});
    
    // Calculate average for each month
    const monthlyAverages = Object.values(monthlyData).map(item => ({
      month: item.month,
      avgValue: item.total / item.count
    }));
    
    // Sort by month
    return monthlyAverages.sort((a, b) => a.month - b.month);
  };

  // Process data for performance matrix
  const processPerformanceMatrix = () => {
    if (!data.length) return [];
    
    const categoryMetrics = {};
    
    // Calculate metrics for each category
    selectedCategories.forEach(category => {
      const categoryData = data.filter(item => item.Category === category);
      
      if (categoryData.length === 0) return;
      
      // Calculate average sales/quantity
      const valueField = dataMetric === 'money' ? 'Sales' : 'Quantity';
      const avgValue = _.meanBy(categoryData, valueField);
      
      // Calculate growth rate using the same method as in processGrowthTrendsData
      const yearlyData = {};
      categoryData.forEach(item => {
        const year = item.year;
        if (!yearlyData[year]) {
          yearlyData[year] = 0;
        }
        yearlyData[year] += dataMetric === 'money' ? item.Sales : item.Quantity;
      });
      
      const years = Object.keys(yearlyData).map(Number).sort();
      const firstYear = years[0];
      const lastYear = years[years.length - 1];
      
      let growthRate = 0;
      if (years.length >= 2 && yearlyData[firstYear] > 0) {
        const firstYearValue = yearlyData[firstYear];
        const lastYearValue = yearlyData[lastYear];
        const yearDiff = lastYear - firstYear;
        
        if (yearDiff > 1) {
          // Use CAGR formula for multi-year periods
          growthRate = (Math.pow(lastYearValue / firstYearValue, 1 / yearDiff) - 1) * 100;
        } else {
          // Use simple percentage change for single year
          growthRate = ((lastYearValue - firstYearValue) / firstYearValue) * 100;
        }
      }
      
      // Calculate consistency (lower standard deviation = more consistent)
      const values = categoryData.map(item => dataMetric === 'money' ? item.Sales : item.Quantity);
      const mean = _.mean(values);
      const squaredDiffs = values.map(value => Math.pow(value - mean, 2));
      const variance = squaredDiffs.length > 0 ? _.mean(squaredDiffs) : 0;
      const stdDev = Math.sqrt(variance);
      const consistency = mean > 0 ? (1 - (stdDev / mean)) * 100 : 0; // Normalize to percentage
      
      categoryMetrics[category] = {
        category,
        avgValue,
        growthRate: Math.round(growthRate * 10) / 10, // Round to 1 decimal
        consistency: Math.max(0, Math.min(100, consistency)) // Clamp between 0-100
      };
    });
    
    return Object.values(categoryMetrics);
  };

  // Handle tab change
  const handleTabChange = (newValue) => {
    setSelectedTab(newValue);
  };

  // Get value label based on selected data metric
  const getValueLabel = () => {
    return dataMetric === 'money' ? 'المبيعات (جنيه)' : 'الكمية';
  };

  // Chart options for category comparison
  const comparisonChartOptions = {
    chart: {
      type: 'line',
      height: 350,
      background: 'transparent',
      toolbar: { 
        show: true,
        tools: {
          download: true,
          selection: true,
          zoom: true,
          zoomin: true,
          zoomout: true,
          pan: true,
          reset: true
        }
      },
      fontFamily: theme.typography.fontFamily,
    },
    title: {
      text: `مقارنة ${dataMetric === 'money' ? 'المبيعات' : 'الكميات'} حسب الفئة`,
      align: 'center',
      style: { 
        fontSize: '18px',
        fontWeight: 600,
        fontFamily: theme.typography.fontFamily,
        color: theme.palette.text.primary 
      },
    },
    xaxis: {
      type: 'datetime',
      categories: processCategoryComparisonData().map(item => item.date),
      labels: { 
        style: { 
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
        },
        datetimeFormatter: {
          year: 'yyyy',
          month: 'MMM yyyy',
        }
      },
    },
    yaxis: {
      title: {
        text: getValueLabel(),
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
    colors: selectedCategories.map(category => getColorPalette()[getCategoryColorIndex(category)]),
    stroke: {
      width: 3,
      curve: 'smooth',
      lineCap: 'round',
    },
    grid: { 
      borderColor: theme.palette.divider,
      strokeDashArray: 3,
      opacity: 0.5
    },
    tooltip: {
      theme: theme.palette.mode,
      x: {
        format: 'MMM yyyy'
      },
      y: {
        formatter: (value) => {
          if (dataMetric === 'money') {
            return `${Math.round(value)} جنيه`;
          }
          return `${Math.round(value)} قطعة`;
        },
      },
      style: {
        fontFamily: theme.typography.fontFamily
      }
    },
    legend: {
      position: 'top',
      horizontalAlign: 'right',
      fontSize: '14px',
      fontFamily: theme.typography.fontFamily,
      markers: {
        width: 12,
        height: 12,
        radius: 6
      },
      itemMargin: {
        horizontal: 10,
        vertical: 10
      }
    },
    dataLabels: {
      enabled: false, 
    },
    markers: {
      size: 4,
      shape: 'circle',
      strokeWidth: 0,
      hover: {
        size: 7,
      }
    },
  };

  // Sales share pie chart options
  const salesShareChartOptions = {
    chart: {
      type: 'pie',
      height: 350,
      background: 'transparent',
      fontFamily: theme.typography.fontFamily,
    },
    title: {
      text: `توزيع حصة ${dataMetric === 'money' ? 'المبيعات' : 'الكميات'}`,
      align: 'center',
      style: { 
        fontSize: '18px',
        fontWeight: 600,
        fontFamily: theme.typography.fontFamily,
        color: theme.palette.text.primary 
      },
    },
    labels: dataMetric === 'money' 
      ? salesShareData.map(item => item.name)
      : quantitySalesShareData.map(item => item.name),
    colors: (dataMetric === 'money' ? salesShareData : quantitySalesShareData)
      .map(item => getColorPalette()[getCategoryColorIndex(item.name)]),
    dataLabels: {
      enabled: true,
      formatter: function (val, opts) {
        return `${Math.round(val)}%`;
      },
      style: {
        fontSize: '14px',
        fontFamily: theme.typography.fontFamily,
        fontWeight: 400,
      },
      dropShadow: {
        enabled: false
      }
    },
    legend: {
      position: 'bottom',
      fontSize: '14px',
      fontFamily: theme.typography.fontFamily,
      markers: {
        width: 12,
        height: 12,
        radius: 6
      },
      itemMargin: {
        horizontal: 10,
        vertical: 5
      }
    },
    tooltip: {
      y: {
        formatter: function(value) {
          if (dataMetric === 'money') {
            return `${Math.round(value)} جنيه`;
          }
          return `${Math.round(value)} قطعة`;
        }
      }
    },
    responsive: [{
      breakpoint: 480,
      options: {
        chart: {
          width: 300
        },
        legend: {
          position: 'bottom'
        }
      }
    }]
  };

  // Growth trends chart options
  const growthTrendsChartOptions = {
    chart: {
      type: 'bar',
      height: 350,
      background: 'transparent',
      toolbar: { 
        show: true,
      },
      fontFamily: theme.typography.fontFamily,
    },
    title: {
      text: `معدلات نمو ${dataMetric === 'money' ? 'المبيعات' : 'الكميات'} حسب الفئة`,
      align: 'center',
      style: { 
        fontSize: '18px',
        fontWeight: 600,
        fontFamily: theme.typography.fontFamily,
        color: theme.palette.text.primary 
      },
    },
    plotOptions: {
      bar: {
        horizontal: false,
        columnWidth: '60%',
        borderRadius: 4,
      },
    },
    dataLabels: {
      enabled: true,
      formatter: function(val) {
        return `${val.toFixed(1)}%`;
      },
      style: {
        fontSize: '12px',
        fontFamily: theme.typography.fontFamily,
        colors: ['#fff'],
      },
      background: {
        enabled: false
      }
    },
    xaxis: {
      categories: processGrowthTrendsData().map(item => item.Category),
      labels: { 
        style: { 
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
        }
      },
    },
    yaxis: {
      title: {
        text: 'معدل النمو (%)',
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
        formatter: (value) => `${value.toFixed(1)}%`,
      },
    },
    colors: processGrowthTrendsData().map(item => getColorPalette()[getCategoryColorIndex(item.Category)]),
    tooltip: {
      y: {
        formatter: function(val) {
          return `${val.toFixed(1)}%`;
        }
      }
    }
  };

  // Seasonal trends chart options
  const seasonalTrendsChartOptions = {
    chart: {
      type: 'bar',
      height: 280,
      background: 'transparent',
      toolbar: { 
        show: false
      },
      fontFamily: theme.typography.fontFamily,
    },
    title: {
      text: `الأنماط الموسمية لـ${dataMetric === 'money' ? 'لمبيعات' : 'لكميات'}`,
      align: 'center',
      style: { 
        fontSize: '18px',
        fontWeight: 600,
        fontFamily: theme.typography.fontFamily,
        color: theme.palette.text.primary 
      },
    },
    plotOptions: {
      bar: {
        borderRadius: 4,
        columnWidth: '70%',
      }
    },
    xaxis: {
      categories: calculateSeasonalTrends().map((item) => {
        const monthNames = [
          'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
          'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
        ];
        return monthNames[item.month - 1];
      }),
      labels: { 
        style: { 
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
        }
      },
    },
    yaxis: {
      title: {
        text: `متوسط ${dataMetric === 'money' ? 'المبيعات (جنيه)' : 'الكميات (قطعة)'}`,
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
    colors: [theme.palette.info.main],
    dataLabels: {
      enabled: false,
    },
    grid: { 
      borderColor: theme.palette.divider,
      strokeDashArray: 3,
      opacity: 0.5
    },
    tooltip: {
      y: {
        formatter: (value) => {
          if (dataMetric === 'money') {
            return `${Math.round(value)} جنيه`;
          }
          return `${Math.round(value)} قطعة`;
        },
      },
      style: {
        fontFamily: theme.typography.fontFamily
      }
    },
  };

  // Find peak months
  const findPeakMonths = () => {
    if (!data.length) return [];
    
    const seasonalData = calculateSeasonalTrends();
    // Find average value across all months
    const avgValueTotal = _.meanBy(seasonalData, 'avgValue');
    // Consider peak months those that are at least 20% above average
    const threshold = avgValueTotal * 1.2;
    
    const peaks = seasonalData
      .filter(item => item.avgValue >= threshold)
      .sort((a, b) => b.avgValue - a.avgValue);
    
    return peaks.map(peak => {
      const monthNames = [
        'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
        'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
      ];
      return {
        month: monthNames[peak.month - 1],
        percentage: Math.round((peak.avgValue / avgValueTotal - 1) * 100)
      };
    });
  };

  // Create series data for each chart
  const comparisonSeries = () => {
    const data = processCategoryComparisonData();
    
    return selectedCategories.map(category => ({
      name: category,
      data: data.map(item => item[category] || null)
    }));
  };

  // Get the appropriate sales share data based on the selected metric
  const salesShareSeries = dataMetric === 'money' 
    ? salesShareData.map(item => item.value) 
    : quantitySalesShareData.map(item => item.value);

  const growthTrendsSeries = [{
    name: 'معدل النمو',
    data: processGrowthTrendsData().map(item => item.growthRate)
  }];

  const seasonalTrendsSeries = [{
    name: dataMetric === 'money' ? 'متوسط المبيعات' : 'متوسط الكميات',
    data: calculateSeasonalTrends().map(item => item.avgValue)
  }];

  const peakMonths = findPeakMonths();

  // Handle form submission
  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    fetchData();
  };

  // Render filter panel
  const renderFilterPanel = () => {
    return (
      <Paper 
        elevation={0} 
        component="form" 
        onSubmit={handleSubmit}
        sx={{ 
          mb: 3, 
          borderRadius: 3, 
          bgcolor: alpha(theme.palette.primary.main, 0.05),
          border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`
        }}
      >
        <Box sx={{ p: 2 }}>
          <Grid container spacing={2} alignItems="center">
            {/* Top row with data type selection */}
            <Grid item xs={12}>
              <FormControl component="fieldset">
                <FormLabel component="legend" sx={{ fontWeight: 'medium', mb: 1 }}>
                  نوع البيانات للتحليل
                </FormLabel>
                <RadioGroup
                  row
                  aria-label="data-metric"
                  name="data-metric"
                  value={dataMetric}
                  onChange={handleDataMetricChange}
                >
                  <FormControlLabel 
                    value="money" 
                    control={<Radio color="primary" />} 
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <LocalAtm fontSize="small" />
                        <span>المبيعات (المبالغ المالية)</span>
                      </Box>
                    } 
                  />
                  <FormControlLabel 
                    value="quantity" 
                    control={<Radio color="secondary" />} 
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <ProductionQuantityLimits fontSize="small" />
                        <span>الكميات</span>
                      </Box>
                    }
                  />
                </RadioGroup>
              </FormControl>
              <Divider sx={{ my: 2 }} />
            </Grid>
            
            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel id="category-selection-label">اختر الفئات</InputLabel>
                <Select
                  labelId="category-selection-label"
                  multiple
                  value={selectedCategories}
                  onChange={handleCategoryChange}
                  input={<OutlinedInput label="اختر الفئات" />}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip 
                          key={value} 
                          label={value} 
                          size="small" 
                          color="primary"
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  )}
                >
                  <MenuItem value="all">
                    <Checkbox checked={allCategoriesSelected} />
                    <ListItemText primary="اختر الكل" />
                  </MenuItem>
                  {categories.map((category) => (
                    <MenuItem key={category} value={category}>
                      <Checkbox checked={selectedCategories.indexOf(category) > -1} />
                      <ListItemText primary={category} />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>الفترة الزمنية</InputLabel>
                <Select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  label="الفترة الزمنية"
                >
                  <MenuItem value="monthly">شهري</MenuItem>
                  <MenuItem value="quarterly">ربع سنوي</MenuItem>
                  <MenuItem value="yearly">سنوي</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={6} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>سنة البداية</InputLabel>
                <Select
                  value={startYear}
                  onChange={(e) => setStartYear(e.target.value)}
                  label="سنة البداية"
                >
                  {Array.from({ length: 10 }, (_, i) => new Date().getFullYear() - 9 + i).map(year => (
                    <MenuItem key={year} value={year.toString()}>{year}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={6} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>سنة النهاية</InputLabel>
                <Select
                  value={endYear}
                  onChange={(e) => setEndYear(e.target.value)}
                  label="سنة النهاية"
                >
                  {Array.from({ length: 10 }, (_, i) => new Date().getFullYear() - 9 + i).map(year => (
                    <MenuItem key={year} value={year.toString()}>{year}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={2}>
              <Button
                fullWidth
                variant="contained"
                color="primary"
                startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <ShowChart />}
                onClick={handleSubmit}
                disabled={loading}
                type="submit"
                sx={{ height: '40px' }}
              >
                تحديث البيانات
              </Button>
            </Grid>
          </Grid>
        </Box>
      </Paper>
    );
  };

  if (loading && !data.length) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  // If no data is available after loading
  if (!loading && (!data.length || !categories.length)) {
    return (
      <Box>
        <Alert 
          severity="warning" 
          sx={{ mb: 4, borderRadius: 2 }}
          variant="filled"
        >
          لا توجد بيانات متاحة لأداء الفئات. يرجى التحقق من اتصال قاعدة البيانات.
        </Alert>
        {renderFilterPanel()}
        <Button
          variant="outlined"
          color="primary"
          onClick={() => generateAndUseSampleData()}
          startIcon={<ShowChart />}
          sx={{ mt: 2 }}
        >
          استخدم بيانات توضيحية
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Page Header */}
      <Box sx={{ 
        p: 3, 
        pb: 1, 
        background: `linear-gradient(120deg, ${alpha(theme.palette.primary.main, 0.1)} 0%, ${alpha(theme.palette.primary.light, 0.15)} 100%)`,
        borderBottom: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`
      }}>
        <Box 
          sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            flexWrap: 'wrap', 
            gap: 2 
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <QueryStats 
              sx={{ 
                color: theme.palette.primary.main, 
                fontSize: 28 
              }} 
            />
            <Typography variant="h5" component="h1" fontWeight="bold">
              تحليل أداء الفئات
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant={selectedTab === 0 ? "contained" : "outlined"}
              color="primary"
              size="small"
              startIcon={<ShowChart />}
              onClick={() => handleTabChange(0)}
            >
              المقارنة
            </Button>
            <Button
              variant={selectedTab === 1 ? "contained" : "outlined"}
              color="primary"
              size="small"
              startIcon={<PieChartIcon />}
              onClick={() => handleTabChange(1)}
            >
              حصة المبيعات
            </Button>
            <Button
              variant={selectedTab === 2 ? "contained" : "outlined"}
              color="primary"
              size="small"
              startIcon={<TrendingUp />}
              onClick={() => handleTabChange(2)}
            >
              النمو
            </Button>
            <Button
              variant={selectedTab === 3 ? "contained" : "outlined"}
              color="primary"
              size="small"
              startIcon={<BarChartIcon />}
              onClick={() => handleTabChange(3)}
            >
              الأداء
            </Button>
          </Box>
        </Box>
      </Box>

      {/* Main Content */}
      <Box sx={{ p: 3, flex: 1, display: 'flex', flexDirection: 'column' }}>
        {renderFilterPanel()}
        
        {error && (
          <Alert 
            severity="error" 
            sx={{ mb: 4, borderRadius: 2 }}
            variant="filled"
          >
            {error}
          </Alert>
        )}
        
        {/* Content based on selected tab */}
        <Box sx={{ flex: 1 }}>
          {selectedTab === 0 && ( // Comparison Tab
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card elevation={3} sx={{ borderRadius: 3, overflow: 'hidden' }}>
                  <CardContent>
                    <Chart
                      options={comparisonChartOptions}
                      series={comparisonSeries()}
                      type="line"
                      height={400}
                    />
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12}>
                <Card elevation={3} sx={{ borderRadius: 3, overflow: 'hidden' }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
                      الأنماط الموسمية
                    </Typography>
                    <Chart
                      options={seasonalTrendsChartOptions}
                      series={seasonalTrendsSeries}
                      type="bar"
                      height={300}
                    />
                    
                    <Box sx={{ mt: 3, p: 2, bgcolor: alpha(theme.palette.info.main, 0.05), borderRadius: 2 }}>
                      <Typography variant="subtitle1" color="primary" fontWeight="bold" gutterBottom>
                        <DateRange sx={{ verticalAlign: 'middle', mr: 1, fontSize: 20 }} />
                        توصيات موسمية
                      </Typography>
                      <Divider sx={{ mb: 2 }} />
                      
                      <Box sx={{ ml: 4 }}>
                        <Typography paragraph>
                          <strong>• مواسم ذروة {dataMetric === 'money' ? 'المبيعات' : 'الكميات'}:</strong> {peakMonths.length > 0 ? (
                            peakMonths.map(peak => `${peak.month} (+${peak.percentage}%)`).join('، ')
                          ) : 'لا توجد بيانات كافية'}
                        </Typography>
                        <Typography>
                          <strong>• توصيات:</strong> زيادة المخزون وتكثيف الحملات التسويقية قبل شهر من بداية مواسم الذروة
                        </Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
          
          {selectedTab === 1 && ( // Sales Share Tab
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card elevation={3} sx={{ borderRadius: 3, overflow: 'hidden', height: '100%' }}>
                  <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
                      <PieChartIcon sx={{ verticalAlign: 'middle', mr: 1, color: theme.palette.primary.main }} />
                      توزيع حصة {dataMetric === 'money' ? 'المبيعات' : 'الكميات'}
                    </Typography>
                    <Box sx={{ flex: 1, minHeight: 400 }}>
                      <Chart
                        options={salesShareChartOptions}
                        series={salesShareSeries}
                        type="pie"
                        height="100%"
                      />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Card elevation={3} sx={{ borderRadius: 3, overflow: 'hidden' }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
                      <MonetizationOn sx={{ verticalAlign: 'middle', mr: 1, color: theme.palette.primary.main }} />
                      أعلى الفئات {dataMetric === 'money' ? 'مبيعاً' : 'كميةً'}
                    </Typography>
                    
                    <Box sx={{ mt: 2 }}>
                      {(dataMetric === 'money' ? [...salesShareData] : [...quantitySalesShareData])
                        .sort((a, b) => b.value - a.value)
                        .map((item, index) => (
                          <Box key={item.name} sx={{ mb: 2 }}>
                            <Grid container alignItems="center" spacing={2}>
                              <Grid item xs={1}>
                                <Typography 
                                  variant="h6" 
                                  sx={{ 
                                    width: 28, 
                                    height: 28, 
                                    borderRadius: '50%', 
                                    bgcolor: getColorPalette()[getCategoryColorIndex(item.name)],
                                    color: '#fff',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontWeight: 'bold'
                                  }}
                                >
                                  {index + 1}
                                </Typography>
                              </Grid>
                              <Grid item xs={7}>
                                <Typography variant="body1" fontWeight="medium">
                                  {item.name}
                                </Typography>
                              </Grid>
                              <Grid item xs={4} sx={{ textAlign: 'right' }}>
                                <Typography variant="body1" fontWeight="bold">
                                  {Math.round(item.value).toLocaleString()} {dataMetric === 'money' ? 'جنيه' : 'قطعة'}
                                </Typography>
                              </Grid>
                            </Grid>
                            <Box sx={{ 
                              mt: 1, 
                              ml: 4, 
                              height: 8, 
                              bgcolor: alpha(theme.palette.primary.main, 0.1),
                              borderRadius: 1,
                              overflow: 'hidden'
                            }}>
                              <Box 
                                sx={{ 
                                  height: '100%', 
                                  width: `${(item.value / (dataMetric === 'money' ? salesShareData[0].value : quantitySalesShareData[0].value)) * 100}%`,
                                  bgcolor: getColorPalette()[getCategoryColorIndex(item.name)],
                                }}
                              />
                            </Box>
                          </Box>
                        ))}
                    </Box>
                  </CardContent>
                </Card>
                
                <Card elevation={3} sx={{ borderRadius: 3, overflow: 'hidden', mt: 3 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
                      النصائح الاستراتيجية
                    </Typography>
                    <Typography paragraph>
                      بناءً على تحليل حصة {dataMetric === 'money' ? 'المبيعات' : 'الكميات'} الحالية، نوصي بالتركيز على:
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <Box sx={{ p: 2, bgcolor: alpha(theme.palette.success.main, 0.1), borderRadius: 2 }}>
                          <Typography variant="subtitle2" color="success.main" fontWeight="bold" gutterBottom>
                            الفئات الأعلى {dataMetric === 'money' ? 'مبيعاً' : 'كميةً'}
                          </Typography>
                          <Typography variant="body2">
                            المحافظة على مستويات المخزون المثلى وضمان توفر المنتجات الأكثر طلباً. كما يمكن استغلال شعبية هذه الفئات للترويج للمنتجات الأخرى من خلال عروض مشتركة.
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Box sx={{ p: 2, bgcolor: alpha(theme.palette.warning.main, 0.1), borderRadius: 2 }}>
                          <Typography variant="subtitle2" color="warning.main" fontWeight="bold" gutterBottom>
                            الفئات الأقل {dataMetric === 'money' ? 'مبيعاً' : 'كميةً'}
                          </Typography>
                          <Typography variant="body2">
                            تطوير استراتيجيات تسويقية مخصصة وتحسين عرض المنتجات لزيادة المبيعات. يمكن أيضاً النظر في تجديد تشكيلة المنتجات وفقاً لاتجاهات السوق والمواسم.
                          </Typography>
                        </Box>
                      </Grid>
                    </Grid>
                    <Box sx={{ mt: 3, p: 2, bgcolor: alpha(theme.palette.info.main, 0.05), borderRadius: 2 }}>
                      <Typography variant="subtitle2" color="info.main" fontWeight="bold" gutterBottom>
                        توزيع الموارد
                      </Typography>
                      <Typography variant="body2">
                        يوصى بتوزيع موارد التسويق والمخزون بما يتناسب مع حصة كل فئة، مع تخصيص نسبة إضافية للفئات الواعدة ذات إمكانات النمو المرتفعة.
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
          
          {selectedTab === 2 && ( // Growth Trends Tab
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card elevation={3} sx={{ borderRadius: 3, overflow: 'hidden' }}>
                  <CardContent>
                    <Chart
                      options={growthTrendsChartOptions}
                      series={growthTrendsSeries}
                      type="bar"
                      height={400}
                    />
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12}>
                <Card elevation={3} sx={{ borderRadius: 3, overflow: 'hidden' }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
                      تحليل معدلات النمو
                    </Typography>
                    <Grid container spacing={3} sx={{ mt: 1 }}>
                      {processGrowthTrendsData().map((item, index) => (
                        <Grid item xs={12} md={4} key={item.Category}>
                          <Box 
                            sx={{ 
                              p: 2, 
                              borderRadius: 2, 
                              bgcolor: item.growthRate >= 0 
                                ? alpha(theme.palette.success.main, 0.1) 
                                : alpha(theme.palette.error.main, 0.1),
                              border: `1px solid ${item.growthRate >= 0 
                                ? alpha(theme.palette.success.main, 0.2) 
                                : alpha(theme.palette.error.main, 0.2)}`
                            }}
                          >
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                              <Typography variant="subtitle1" fontWeight="bold">
                                {item.Category}
                              </Typography>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                {dataMetric === 'money' ? <LocalAtm fontSize="small" /> : <ProductionQuantityLimits fontSize="small" />}
                                <Chip 
                                  label={`${item.growthRate >= 0 ? '+' : ''}${item.growthRate.toFixed(1)}%`}
                                  color={item.growthRate >= 0 ? "success" : "error"}
                                  size="small"
                                />
                              </Box>
                            </Box>
                            <Divider sx={{ my: 1 }} />
                            {/* Show all years data */}
                            {item.allYears.map(year => (
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }} key={year}>
                                <Typography variant="body2" color="text.secondary">
                                  {year}:
                                </Typography>
                                <Typography variant="body2" fontWeight="medium">
                                  {Math.round(item.yearValues[year]).toLocaleString()} {dataMetric === 'money' ? 'جنيه' : 'قطعة'}
                                </Typography>
                              </Box>
                            ))}
                          </Box>
                        </Grid>
                      ))}
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
          
          {selectedTab === 3 && ( // Performance Tab
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card elevation={3} sx={{ borderRadius: 3, overflow: 'hidden' }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
                      مصفوفة أداء الفئات
                    </Typography>
                    <Box sx={{ overflow: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr>
                            <th style={{ padding: '10px', textAlign: 'right', borderBottom: '2px solid #eee' }}>الفئة</th>
                            <th style={{ padding: '10px', textAlign: 'center', borderBottom: '2px solid #eee' }}>متوسط {dataMetric === 'money' ? 'المبيعات' : 'الكميات'}</th>
                            <th style={{ padding: '10px', textAlign: 'center', borderBottom: '2px solid #eee' }}>معدل النمو</th>
                            <th style={{ padding: '10px', textAlign: 'center', borderBottom: '2px solid #eee' }}>الاستقرار</th>
                            <th style={{ padding: '10px', textAlign: 'center', borderBottom: '2px solid #eee' }}>مؤشر الأداء العام</th>
                          </tr>
                        </thead>
                        <tbody>
                          {processPerformanceMatrix().sort((a, b) => b.avgValue - a.avgValue).map((item, index) => {
                            // Calculate overall performance score (simple weighted average)
                            const growthFactor = ((item.growthRate + 20) / 40); // Normalize from -20% to +20%
                            const consistencyFactor = item.consistency / 100;
                            const performanceScore = (item.avgValue * 0.5) + (growthFactor * 0.3) + (consistencyFactor * 0.2);
                            
                            // Get max score for percentage calculation
                            const maxScore = processPerformanceMatrix().reduce((max, curr) => {
                              const currGrowthFactor = ((curr.growthRate + 20) / 40);
                              const currConsistencyFactor = curr.consistency / 100;
                              const currScore = (curr.avgValue * 0.5) + (currGrowthFactor * 0.3) + (currConsistencyFactor * 0.2);
                              return Math.max(max, currScore);
                            }, 0);
                            
                            const scorePercentage = (performanceScore / maxScore) * 100;
                            
                            return (
                              <tr key={item.category}>
                                <td style={{ padding: '10px', textAlign: 'right', borderBottom: '1px solid #eee' }}>
                                  <Typography fontWeight="medium">{item.category}</Typography>
                                </td>
                                <td style={{ padding: '10px', textAlign: 'center', borderBottom: '1px solid #eee' }}>
                                  {Math.round(item.avgValue).toLocaleString()} {dataMetric === 'money' ? 'جنيه' : 'قطعة'}
                                </td>
                                <td style={{ 
                                  padding: '10px', 
                                  textAlign: 'center', 
                                  color: item.growthRate >= 0 ? theme.palette.success.main : theme.palette.error.main,
                                  fontWeight: 'bold',
                                  borderBottom: '1px solid #eee' 
                                }}>
                                  {item.growthRate >= 0 ? '+' : ''}{item.growthRate.toFixed(1)}%
                                </td>
                                <td style={{ padding: '10px', textAlign: 'center', borderBottom: '1px solid #eee' }}>
                                  {Math.round(item.consistency)}%
                                </td>
                                <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>
                                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                    <Box sx={{ flexGrow: 1, mr: 1 }}>
                                      <Box sx={{ width: '100%', bgcolor: alpha(theme.palette.primary.main, 0.1), height: 8, borderRadius: 4 }}>
                                        <Box 
                                          sx={{ 
                                            width: `${scorePercentage}%`, 
                                            bgcolor: getColorPalette()[getCategoryColorIndex(item.category)],
                                            height: '100%',
                                            borderRadius: 4
                                          }} 
                                        />
                                      </Box>
                                    </Box>
                                    <Typography variant="body2" fontWeight="medium">
                                      {Math.round(scorePercentage)}%
                                    </Typography>
                                  </Box>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12}>
                <Card elevation={3} sx={{ borderRadius: 3, overflow: 'hidden' }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
                      توصيات تحليلية
                    </Typography>
                    <Typography variant="body2" paragraph sx={{ mb: 3 }}>
                      بناءً على تحليل البيانات، تم تصنيف الفئات إلى ثلاث مجموعات وفقًا لأدائها العام، مع مراعاة {dataMetric === 'money' ? 'المبيعات' : 'الكميات'} ومعدلات النمو والاستقرار:
                    </Typography>
                    <Grid container spacing={3}>
                      <Grid item xs={12} md={4}>
                        <Box sx={{ p: 2, bgcolor: alpha(theme.palette.success.main, 0.1), borderRadius: 2, height: '100%' }}>
                          <Typography variant="subtitle1" color="success.main" fontWeight="bold" gutterBottom>
                            الفئات عالية الأداء
                          </Typography>
                          <Typography variant="body2" paragraph>
                            تتميز بمعدلات نمو عالية واستقرار في الأداء، وتمثل الركيزة الأساسية لإيرادات العمل
                          </Typography>
                          <Typography variant="body2" paragraph>
                            <strong>المميزات:</strong> استقرار في {dataMetric === 'money' ? 'المبيعات' : 'الكميات'}، معدلات نمو إيجابية، تحقق أعلى إيرادات
                          </Typography>
                          <Typography variant="body2">
                            <strong>الإجراء المقترح:</strong> زيادة الاستثمار في هذه الفئات، توسيع تشكيلة المنتجات، تطوير حملات تسويقية مخصصة للعملاء المهتمين بهذه الفئات
                          </Typography>
                        </Box>
                      </Grid>
                      
                      <Grid item xs={12} md={4}>
                        <Box sx={{ p: 2, bgcolor: alpha(theme.palette.warning.main, 0.1), borderRadius: 2, height: '100%' }}>
                          <Typography variant="subtitle1" color="warning.main" fontWeight="bold" gutterBottom>
                            الفئات المتوسطة
                          </Typography>
                          <Typography variant="body2" paragraph>
                            تظهر إمكانات نمو واعدة ولكن تحتاج إلى تحسين الأداء، وتمثل فرصة للتوسع المستقبلي
                          </Typography>
                          <Typography variant="body2" paragraph>
                            <strong>المميزات:</strong> مستويات متوسطة من {dataMetric === 'money' ? 'المبيعات' : 'الكميات'}، إمكانية للنمو، تذبذب في الأداء
                          </Typography>
                          <Typography variant="body2">
                            <strong>الإجراء المقترح:</strong> مراجعة استراتيجيات التسعير، تطوير عروض ترويجية مبتكرة، البحث عن فرص لتحسين جودة المنتجات وتنويعها
                          </Typography>
                        </Box>
                      </Grid>
                      
                      <Grid item xs={12} md={4}>
                        <Box sx={{ p: 2, bgcolor: alpha(theme.palette.error.main, 0.1), borderRadius: 2, height: '100%' }}>
                          <Typography variant="subtitle1" color="error.main" fontWeight="bold" gutterBottom>
                            الفئات منخفضة الأداء
                          </Typography>
                          <Typography variant="body2" paragraph>
                            تظهر تراجعاً في {dataMetric === 'money' ? 'المبيعات' : 'الكميات'} وعدم استقرار، وتحتاج إلى تدخل سريع لتحسين أدائها
                          </Typography>
                          <Typography variant="body2" paragraph>
                            <strong>المميزات:</strong> انخفاض في {dataMetric === 'money' ? 'المبيعات' : 'الكميات'}، عدم استقرار في الأداء، معدلات نمو سلبية
                          </Typography>
                          <Typography variant="body2">
                            <strong>الإجراء المقترح:</strong> إعادة تقييم شاملة للمنتجات، خفض المخزون غير الفعال، تحليل سلوك العملاء وتفضيلاتهم، النظر في إعادة هيكلة هذه الفئات
                          </Typography>
                        </Box>
                      </Grid>
                    </Grid>
                    
                    <Box sx={{ mt: 3, p: 2, bgcolor: alpha(theme.palette.info.main, 0.05), borderRadius: 2 }}>
                      <Typography variant="subtitle1" color="primary" fontWeight="bold" gutterBottom>
                        ملاحظة هامة حول مؤشر الأداء العام
                      </Typography>
                      <Typography variant="body2">
                        يتم احتساب مؤشر الأداء العام باستخدام معادلة مركبة تأخذ بعين الاعتبار ثلاثة عوامل رئيسية:
                        <ul style={{ marginTop: '8px' }}>
                          <li><strong>متوسط {dataMetric === 'money' ? 'المبيعات' : 'الكميات'} (50%):</strong> يمثل الوزن الأكبر في المعادلة ويعكس القيمة المطلقة {dataMetric === 'money' ? 'للمبيعات' : 'للكميات'}</li>
                          <li><strong>معدل النمو (30%):</strong> يقيس التغير النسبي في {dataMetric === 'money' ? 'المبيعات' : 'الكميات'} بين الفترات المختلفة</li>
                          <li><strong>الاستقرار (20%):</strong> يقيس مدى ثبات {dataMetric === 'money' ? 'المبيعات' : 'الكميات'} وعدم تذبذبها خلال الفترة الزمنية</li>
                        </ul>
                        كلما ارتفع المؤشر، كان أداء الفئة أفضل من حيث {dataMetric === 'money' ? 'المبيعات' : 'الكميات'} والنمو والاستقرار.
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default CategoryPerformanceDashboard;