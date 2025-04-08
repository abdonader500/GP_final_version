import React, { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  AlertTitle,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  ListItemText,
  OutlinedInput,
  Chip,
  Tabs,
  Tab,
  FormControlLabel,
  Switch,
  Stack,
  Button,
  Paper,
  Divider,
  alpha,
  useTheme,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  Tooltip,
} from "@mui/material";
import {
  ShowChart,
  CategoryRounded,
  Inventory2Outlined,
  Autorenew,
  Check,
  Info,
  Warning,
  BarChart,
  Timeline,
  CalendarMonth,
  TrendingUp,
  Analytics,
} from "@mui/icons-material";
import Chart from "react-apexcharts";
import axios from "axios";

function DemandForecastComponent() {
  const theme = useTheme();

  // State for sub-tabs
  const [activeSubTab, setActiveSubTab] = useState(0);

  // State for demand data
  const [demandData, setDemandData] = useState({});
  const [isLoadingDemand, setIsLoadingDemand] = useState(true);
  const [errorDemand, setErrorDemand] = useState(null);
  const [demandMessage, setDemandMessage] = useState(null);
  const [selectedDemandCategories, setSelectedDemandCategories] = useState([]);
  const [allCategoriesSelected, setAllCategoriesSelected] = useState(true);
  const [categories, setCategories] = useState([]);

  // State for item-level demand data
  const [itemDemandData, setItemDemandData] = useState({});
  const [isLoadingItemDemand, setIsLoadingItemDemand] = useState(false);
  const [errorItemDemand, setErrorItemDemand] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [itemSpecifications, setItemSpecifications] = useState([]);
  const [selectedItemSpecifications, setSelectedItemSpecifications] = useState([]);
  const [allItemsSelected, setAllItemsSelected] = useState(true);

  // State for toggling quantity and net profit display
  const [showQuantity, setShowQuantity] = useState(true);
  const [showNetProfit, setShowNetProfit] = useState(true);

  // State for AI forecast
  const [isRunningForecast, setIsRunningForecast] = useState(false);
  const [forecastSuccess, setForecastSuccess] = useState(false);
  const [forecastError, setForecastError] = useState(null);
  const [showForecastDialog, setShowForecastDialog] = useState(false);
  const [forecastProgress, setForecastProgress] = useState(0);
  const [forecastStep, setForecastStep] = useState(0);
  const [showSuccessSnackbar, setShowSuccessSnackbar] = useState(false);

  // State for model metrics
  const [modelMetrics, setModelMetrics] = useState({});
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false);
  const [bestModel, setBestModel] = useState(null);

  // State for showing the seasonal comparison chart
  const [showSeasonalComparison, setShowSeasonalComparison] = useState(false);
  const [seasonalPatterns, setSeasonalPatterns] = useState([]);

  // Handle sub-tab change
  const handleSubTabChange = (event, newValue) => {
    setActiveSubTab(newValue);
  };

  // Fetch category-level demand data on component mount
  useEffect(() => {
    fetchCategoryDemandData();
  }, []);

  // Fetch item specifications when selected category changes
  useEffect(() => {
    if (selectedCategory) {
      fetchItemSpecifications();
    }
  }, [selectedCategory]);

  // Fetch category-level demand data
  const fetchCategoryDemandData = async () => {
    setIsLoadingDemand(true);
    setErrorDemand(null);
    setDemandMessage(null);
    try {
      const response = await axios.get(
        "http://localhost:5000/api/visualization/demand-forecasting"
      );
      
      setDemandData(response.data.demand_data || {});
      setDemandMessage(response.data.message || null);
      
      const cats = Object.keys(response.data.demand_data || {});
      setCategories(cats);
      setSelectedDemandCategories(cats);
      
      // Set default selected category for item-level tab
      if (cats.length > 0 && !selectedCategory) {
        setSelectedCategory(cats[0]);
      }

      // Also fetch model metrics for the first category
      if (cats.length > 0) {
        fetchModelMetrics(cats[0]);
      }

      // Fetch seasonal patterns for all categories
      fetchSeasonalPatterns();
      
    } catch (err) {
      setErrorDemand("فشل في جلب بيانات الطلب. يرجى المحاولة مرة أخرى.");
      console.error("Error fetching demand data:", err);
    } finally {
      setIsLoadingDemand(false);
    }
  };

  // Fetch item specifications for a selected category
  const fetchItemSpecifications = async () => {
    if (!selectedCategory) return;
    
    setIsLoadingItemDemand(true);
    setErrorItemDemand(null);
    
    try {
      const response = await axios.get(
        "http://localhost:5000/api/visualization/item-demand-forecasting",
        {
          params: {
            category: selectedCategory
          }
        }
      );
      
      const itemData = response.data.item_demand_data || {};
      setItemDemandData(itemData);
      
      // Extract item specifications for the selected category, excluding "غير محدد"
      const specs = itemData[selectedCategory] 
        ? Object.keys(itemData[selectedCategory]).filter(spec => spec !== "غير محدد")
        : [];
      setItemSpecifications(specs);
      
      // Set all specifications as selected by default
      setSelectedItemSpecifications(specs);
      setAllItemsSelected(true);

      // Fetch model metrics for this category
      fetchModelMetrics(selectedCategory);
      
    } catch (err) {
      setErrorItemDemand("فشل في جلب بيانات الطلب على مستوى المنتجات. يرجى المحاولة مرة أخرى.");
      console.error("Error fetching item demand data:", err);
    } finally {
      setIsLoadingItemDemand(false);
    }
  };

  // Fetch model metrics for a category
  const fetchModelMetrics = async (category) => {
    setIsLoadingMetrics(true);
    try {
      const response = await axios.get(
        "http://localhost:5000/api/demand-forecasting/get-model-metrics",
        {
          params: {
            category: category
          }
        }
      );

      if (response.data.success && response.data.data) {
        setModelMetrics(response.data.data);
        
        // Find the best model
        const models = response.data.data;
        let bestModelId = null;
        let lowestRMSE = Infinity;
        
        Object.entries(models).forEach(([id, model]) => {
          if (model.metrics && model.metrics.rmse && model.metrics.rmse < lowestRMSE) {
            lowestRMSE = model.metrics.rmse;
            bestModelId = id;
          }
        });
        
        setBestModel(bestModelId ? models[bestModelId] : null);
      }
    } catch (err) {
      console.error("Error fetching model metrics:", err);
    } finally {
      setIsLoadingMetrics(false);
    }
  };

  // Fetch seasonal patterns
  const fetchSeasonalPatterns = async () => {
    try {
      const response = await axios.get(
        "http://localhost:5000/api/demand-forecasting/get-seasonal-patterns"
      );

      if (response.data.success && response.data.data) {
        setSeasonalPatterns(response.data.data);
      }
    } catch (err) {
      console.error("Error fetching seasonal patterns:", err);
    }
  };

  // Handle category selection change for category-level tab
  const handleDemandCategoryChange = (event) => {
    const value = event.target.value;
    if (value[value.length - 1] === "all") {
      setSelectedDemandCategories(
        categories.length === selectedDemandCategories.length ? [] : [...categories]
      );
      setAllCategoriesSelected(!allCategoriesSelected);
      return;
    }
    setSelectedDemandCategories(value);
    setAllCategoriesSelected(false);
  };

  // Handle category selection change for item-level tab
  const handleCategoryChange = (event) => {
    setSelectedCategory(event.target.value);
  };

  // Handle item specification selection change
  const handleItemSpecificationsChange = (event) => {
    const value = event.target.value;
    
    if (value[value.length - 1] === "all") {
      setSelectedItemSpecifications(
        itemSpecifications.length === selectedItemSpecifications.length ? [] : [...itemSpecifications]
      );
      setAllItemsSelected(!allItemsSelected);
      return;
    }
    
    setSelectedItemSpecifications(value);
    setAllItemsSelected(false);
  };

  // Run AI forecast
  const runAIForecast = async () => {
    setIsRunningForecast(true);
    setForecastError(null);
    setShowForecastDialog(true);
    setForecastProgress(0);
    setForecastStep(0);
    
    // Simulate progress (will actually run on the server)
    const progressInterval = setInterval(() => {
      setForecastProgress((prev) => {
        const newProgress = prev + 5;
        if (newProgress >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return newProgress;
      });
      
      // Update step based on progress
      setForecastStep((prev) => {
        if (forecastProgress < 30) return 0;
        if (forecastProgress < 70) return 1;
        return 2;
      });
    }, 1500);
    
    try {
      const response = await axios.post(
        "http://localhost:5000/api/demand-forecasting/run-ai-forecast",
        {
          train_models: true,
          generate_forecasts: true,
          save_to_mongodb: true,
          forecast_horizon: 12
        }
      );
      
      if (response.data.success) {
        clearInterval(progressInterval);
        setForecastProgress(100);
        setForecastStep(3);
        setForecastSuccess(true);
        setTimeout(() => {
          setShowForecastDialog(false);
          setShowSuccessSnackbar(true);
          // Refresh data after successful forecast
          fetchCategoryDemandData();
        }, 2000);
      } else {
        clearInterval(progressInterval);
        setForecastError(response.data.message || "فشل في تشغيل نظام التنبؤ الذكي.");
      }
    } catch (err) {
      clearInterval(progressInterval);
      console.error("Error running AI forecast:", err);
      setForecastError(
        err.response?.data?.message || "فشل في تشغيل نظام التنبؤ الذكي. يرجى المحاولة مرة أخرى."
      );
    } finally {
      setIsRunningForecast(false);
    }
  };

  // Process demand data for quantity chart (category-level)
  const processDemandQuantityData = () => {
    if (
      !demandData ||
      Object.keys(demandData).length === 0 ||
      !selectedDemandCategories.length
    ) {
      return [];
    }

    const series = selectedDemandCategories.map((category) => {
      const quantityData = Array.from({ length: 12 }, (_, i) => {
        const month = String(i + 1);
        return {
          x: month,
          y: Math.round(demandData[category]?.[month]?.quantity || 0),
        };
      });

      return {
        name: `${category} - الكمية`,
        type: "line",
        data: quantityData,
      };
    });

    return series;
  };

  // Process demand data for net profit chart (category-level)
  const processDemandNetProfitData = () => {
    if (
      !demandData ||
      Object.keys(demandData).length === 0 ||
      !selectedDemandCategories.length
    ) {
      return [];
    }

    const series = selectedDemandCategories.map((category) => {
      const moneySoldData = Array.from({ length: 12 }, (_, i) => {
        const month = String(i + 1);
        return {
          x: month,
          y: Math.round(demandData[category]?.[month]?.money_sold || 0),
        };
      });

      return {
        name: `${category} - الصافي`,
        type: "area",
        data: moneySoldData,
      };
    });

    return series;
  };

  // Process demand data for pie chart (item-level quantity)
  const processItemDemandQuantityData = () => {
    if (
      !itemDemandData ||
      !selectedCategory ||
      !itemDemandData[selectedCategory] ||
      !selectedItemSpecifications.length
    ) {
      return [];
    }

    // Calculate total quantity for each item specification
    let itemQuantityTotals = selectedItemSpecifications
      .filter(spec => spec !== "غير محدد") // Exclude "غير محدد" items
      .map((spec) => {
        let total = 0;
        
        // Sum up quantities across all months
        for (let i = 1; i <= 12; i++) {
          const month = String(i);
          total += Math.round(itemDemandData[selectedCategory]?.[spec]?.[month]?.quantity || 0);
        }
        
        return {
          name: spec,
          value: total
        };
      });
    
    // Sort by quantity (descending)
    itemQuantityTotals = itemQuantityTotals.sort((a, b) => b.value - a.value);
    
    // Calculate total for percentage calculation
    const grandTotal = itemQuantityTotals.reduce((sum, item) => sum + item.value, 0);
    
    // Add percentage to each item and filter out items below 4%
    itemQuantityTotals = itemQuantityTotals.map(item => ({
      ...item,
      percentage: (item.value / grandTotal) * 100
    })).filter(item => item.percentage >= 4);
    
    return itemQuantityTotals;
  };

  // Process demand data for pie chart (item-level profit)
  const processItemDemandNetProfitData = () => {
    if (
      !itemDemandData ||
      !selectedCategory ||
      !itemDemandData[selectedCategory] ||
      !selectedItemSpecifications.length
    ) {
      return [];
    }

    // Calculate total profit for each item specification
    let itemProfitTotals = selectedItemSpecifications
      .filter(spec => spec !== "غير محدد") // Exclude "غير محدد" items
      .map((spec) => {
        let total = 0;
        
        // Sum up money sold across all months
        for (let i = 1; i <= 12; i++) {
          const month = String(i);
          total += Math.round(itemDemandData[selectedCategory]?.[spec]?.[month]?.money_sold || 0);
        }
        
        return {
          name: spec,
          value: total
        };
      });
    
    // Sort by profit (descending)
    itemProfitTotals = itemProfitTotals.sort((a, b) => b.value - a.value);
    
    // Calculate total for percentage calculation
    const grandTotal = itemProfitTotals.reduce((sum, item) => sum + item.value, 0);
    
    // Add percentage to each item and filter out items below 4%
    itemProfitTotals = itemProfitTotals.map(item => ({
      ...item,
      percentage: (item.value / grandTotal) * 100
    })).filter(item => item.percentage >= 4);
    
    return itemProfitTotals;
  };

  // Process seasonal patterns data
  const processSeasonalPatternsData = () => {
    if (!seasonalPatterns.length) return [];

    return [{
      name: "متوسط الكمية الشهرية",
      data: seasonalPatterns.map(item => item.average_quantity)
    }];
  };

  const categoryDemandQuantitySeries = processDemandQuantityData();
  const categoryDemandNetProfitSeries = processDemandNetProfitData();
  const itemDemandQuantitySeries = processItemDemandQuantityData();
  const itemDemandNetProfitSeries = processItemDemandNetProfitData();
  const seasonalPatternsSeries = processSeasonalPatternsData();

  // Create a custom color palette that matches theme
  const getColorPalette = () => {
    return [
      theme.palette.primary.main,
      theme.palette.secondary.main,
      theme.palette.success.main,
      theme.palette.info.main,
      theme.palette.warning.main,
      theme.palette.error.main,
      "#9C27B0", // Purple
      "#00BCD4", // Cyan
      "#8BC34A", // Light Green
      "#FF9800", // Orange
      "#607D8B", // Blue Grey
      "#E91E63", // Pink
      "#CDDC39", // Lime
      "#795548", // Brown
      "#009688", // Teal
      "#673AB7", // Deep Purple
      "#4CAF50", // Green
      "#FF5722", // Deep Orange
      "#3F51B5", // Indigo
      "#FFC107", // Amber
    ];
  };
  
  // Function to get consistent color index for a category or product
  const getCategoryColorIndex = (name) => {
    // Map common product types to consistent colors
    const productTypeMap = {
      'تيشرت': 0,
      'بنطلون': 1,
      'حذاء': 2,
      'قميص': 3,
      'جاكيت': 4,
      'بلوزة': 5,
      'كوتشي': 6,
      'جزمة': 7,
      'سوت': 8,
      'طقم': 9,
      'بوكسر': 10,
      'صندل': 11,
      'شنطة': 12,
      'فستان': 13,
      'شورت': 14
    };
    
    // Check if there's a predefined mapping
    for (const [type, index] of Object.entries(productTypeMap)) {
      if (name.includes(type)) {
        return index;
      }
    }
    
    // If no mapping found, use string hash
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = ((hash << 5) - hash) + name.charCodeAt(i);
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash) % getColorPalette().length;
  };

  // Chart options for quantity (line chart for category level, pie chart for item level)
  const quantityChartOptions = (isItemLevel = false) => {
    if (isItemLevel) {
      // Pie chart options for item level
      return {
        chart: {
          type: "pie",
          height: 350,
          background: "transparent",
          fontFamily: theme.typography.fontFamily,
        },
        title: {
          text: `توزيع الكميات حسب المنتج (${selectedCategory})`,
          align: "center",
          style: { 
            fontSize: "18px",
            fontWeight: 600,
            fontFamily: theme.typography.fontFamily,
            color: theme.palette.text.primary 
          },
        },
        labels: itemDemandQuantitySeries.map(item => item.name),
        colors: itemDemandQuantitySeries.map(item => 
          getColorPalette()[getCategoryColorIndex(item.name)]
        ),
        dataLabels: {
          enabled: true,
          formatter: function (val, opts) {
            return `${Math.round(val)}%`;
          },
          style: {
            fontSize: "14px",
            fontFamily: theme.typography.fontFamily,
            fontWeight: 400,
          },
          dropShadow: {
            enabled: false
          }
        },
        legend: {
          position: "bottom",
          fontSize: "14px",
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
            formatter: function(value, { series, seriesIndex, dataPointIndex, w }) {
              return `${Math.round(itemDemandQuantitySeries[dataPointIndex].value)} قطعة`;
            }
          }
        },
        subtitle: {
          text: 'يتم عرض المنتجات التي تشكل 4% أو أكثر من إجمالي الكمية',
          align: 'center',
          style: {
            fontSize: '12px',
            fontFamily: theme.typography.fontFamily,
            color: theme.palette.text.secondary
          }
        },
        responsive: [{
          breakpoint: 480,
          options: {
            chart: {
              width: 300
            },
            legend: {
              position: "bottom"
            }
          }
        }]
      };
    } else {
      // Line chart options for category level
      return {
        chart: {
          type: "line",
          height: 280,
          background: "transparent",
          toolbar: {
            show: true,
            tools: {
              download: true,
              selection: true,
              zoom: true,
              zoomin: true,
              zoomout: true,
              pan: true,
              reset: true,
            },
          },
          fontFamily: theme.typography.fontFamily,
        },
        title: {
          text: "توقعات الكمية حسب الفئة",
          align: "center",
          style: {
            fontSize: "18px",
            fontWeight: 600,
            fontFamily: theme.typography.fontFamily,
            color: theme.palette.text.primary,
          },
        },
        xaxis: {
          type: "category",
          categories: Array.from({ length: 12 }, (_, i) => {
            const date = new Date(2025, i, 1);
            return date.toLocaleString('ar-EG', { month: 'short' });
          }),
          labels: {
            style: {
              colors: theme.palette.text.secondary,
              fontFamily: theme.typography.fontFamily,
            },
          },
          title: {
            text: "الشهر",
            style: {
              color: theme.palette.text.secondary,
              fontFamily: theme.typography.fontFamily,
              fontWeight: 500,
            },
          },
        },
        yaxis: {
          title: {
            text: "الكمية",
            style: {
              color: theme.palette.text.secondary,
              fontFamily: theme.typography.fontFamily,
              fontWeight: 500,
            },
          },
          labels: {
            style: {
              colors: theme.palette.text.secondary,
              fontFamily: theme.typography.fontFamily,
            },
            formatter: (value) => Math.round(value),
          },
        },
        colors: getColorPalette(),
        stroke: {
          width: 3,
          curve: "smooth",
          lineCap: "round",
        },
        grid: {
          borderColor: theme.palette.divider,
          strokeDashArray: 3,
          opacity: 0.5,
        },
        tooltip: {
          theme: theme.palette.mode,
          y: {
            formatter: (value) => Math.round(value),
          },
          style: {
            fontFamily: theme.typography.fontFamily,
          },
        },
        legend: {
          position: "top",
          horizontalAlign: "right",
          fontSize: "14px",
          fontFamily: theme.typography.fontFamily,
          markers: {
            width: 12,
            height: 12,
            radius: 6,
          },
          itemMargin: {
            horizontal: 10,
            vertical: 10,
          },
        },
        dataLabels: {
          enabled: false,
        },
        markers: {
          size: 5,
          shape: "circle",
          strokeWidth: 0,
          hover: {
            size: 7,
          },
        },
        animations: {
          enabled: true,
          easing: "easeinout",
          speed: 800,
          animateGradually: {
            enabled: true,
            delay: 150,
          },
          dynamicAnimation: {
            enabled: true,
            speed: 350,
          },
        },
      };
    }
  };

  // Chart options for net profit (area chart for category level, pie chart for item level)
  const netProfitChartOptions = (isItemLevel = false) => {
    if (isItemLevel) {
      // Pie chart options for item level
      return {
        chart: {
          type: "pie",
          height: 350,
          background: "transparent",
          fontFamily: theme.typography.fontFamily,
        },
        title: {
          text: `توزيع المبيعات حسب المنتج (${selectedCategory})`,
          align: "center",
          style: { 
            fontSize: "18px",
            fontWeight: 600,
            fontFamily: theme.typography.fontFamily,
            color: theme.palette.text.primary 
          },
        },
        labels: itemDemandNetProfitSeries.map(item => item.name),
        colors: itemDemandNetProfitSeries.map(item => 
          getColorPalette()[getCategoryColorIndex(item.name)]
        ),
        dataLabels: {
          enabled: true,
          formatter: function (val, opts) {
            return `${Math.round(val)}%`;
          },
          style: {
            fontSize: "14px",
            fontFamily: theme.typography.fontFamily,
            fontWeight: 400,
          },
          dropShadow: {
            enabled: false
          }
        },
        legend: {
          position: "bottom",
          fontSize: "14px",
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
            formatter: function(value, { series, seriesIndex, dataPointIndex, w }) {
              return `${Math.round(itemDemandNetProfitSeries[dataPointIndex].value)} جنيه`;
            }
          }
        },
        subtitle: {
          text: 'يتم عرض المنتجات التي تشكل 4% أو أكثر من إجمالي المبيعات',
          align: 'center',
          style: {
            fontSize: '12px',
            fontFamily: theme.typography.fontFamily,
            color: theme.palette.text.secondary
          }
        },
        responsive: [{
          breakpoint: 480,
          options: {
            chart: {
              width: 300
            },
            legend: {
              position: "bottom"
            }
          }
        }]
      };
    } else {
      // Area chart options for category level
      return {
        chart: {
          type: "area",
          height: 280,
          background: "transparent",
          toolbar: {
            show: true,
            tools: {
              download: true,
              selection: true,
              zoom: true,
              zoomin: true,
              zoomout: true,
              pan: true,
              reset: true,
            },
          },
          fontFamily: theme.typography.fontFamily,
        },
        title: {
          text: "توقعات المبيعات حسب الفئة",
          align: "center",
          style: {
            fontSize: "18px",
            fontWeight: 600,
            fontFamily: theme.typography.fontFamily,
            color: theme.palette.text.primary,
          },
        },
        xaxis: {
          type: "category",
          categories: Array.from({ length: 12 }, (_, i) => {
            const date = new Date(2025, i, 1);
            return date.toLocaleString('ar-EG', { month: 'short' });
          }),
          labels: {
            style: {
              colors: theme.palette.text.secondary,
              fontFamily: theme.typography.fontFamily,
            },
          },
          title: {
            text: "الشهر",
            style: {
              color: theme.palette.text.secondary,
              fontFamily: theme.typography.fontFamily,
              fontWeight: 500,
            },
          },
        },
        yaxis: {
          title: {
            text: "الصافي (جنيه)",
            style: {
              color: theme.palette.text.secondary,
              fontFamily: theme.typography.fontFamily,
              fontWeight: 500,
            },
          },
          labels: {
            style: {
              colors: theme.palette.text.secondary,
              fontFamily: theme.typography.fontFamily,
            },
            formatter: (value) => Math.round(value),
          },
        },
        colors: getColorPalette(),
        stroke: {
          width: 2,
          curve: "smooth",
        },
        fill: {
          type: "gradient",
          gradient: {
            shadeIntensity: 1,
            opacityFrom: 0.7,
            opacityTo: 0.2,
            stops: [0, 90, 100],
          },
        },
        grid: {
          borderColor: theme.palette.divider,
          strokeDashArray: 3,
          opacity: 0.5,
        },
        tooltip: {
          theme: theme.palette.mode,
          y: {
            formatter: (value) => `${Math.round(value)} جنيه`,
          },
          style: {
            fontFamily: theme.typography.fontFamily,
          },
        },
        legend: {
          position: "top",
          horizontalAlign: "right",
          fontSize: "14px",
          fontFamily: theme.typography.fontFamily,
          markers: {
            width: 12,
            height: 12,
            radius: 6,
          },
          itemMargin: {
            horizontal: 10,
            vertical: 10,
          },
        },
        dataLabels: {
          enabled: false,
        },
        markers: {
          size: 0,
          hover: {
            size: 5,
          },
        },
        animations: {
          enabled: true,
          easing: "easeinout",
          speed: 800,
          animateGradually: {
            enabled: true,
            delay: 150,
          },
          dynamicAnimation: {
            enabled: true,
            speed: 350,
          },
        },
      };
    }
  };

  // Chart options for seasonal patterns
  const seasonalPatternsOptions = {
    chart: {
      type: "bar",
      height: 280,
      background: "transparent",
      toolbar: {
        show: true,
      },
      fontFamily: theme.typography.fontFamily,
    },
    title: {
      text: "نمط الطلب الموسمي",
      align: "center",
      style: {
        fontSize: "18px",
        fontWeight: 600,
        fontFamily: theme.typography.fontFamily,
        color: theme.palette.text.primary,
      },
    },
    xaxis: {
      type: "category",
      categories: Array.from({ length: 12 }, (_, i) => {
        const date = new Date(2025, i, 1);
        return date.toLocaleString('ar-EG', { month: 'short' });
      }),
      labels: {
        style: {
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
        },
      },
      title: {
        text: "الشهر",
        style: {
          color: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
          fontWeight: 500,
        },
      },
    },
    yaxis: {
      title: {
        text: "متوسط الكمية",
        style: {
          color: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
          fontWeight: 500,
        },
      },
      labels: {
        style: {
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
        },
        formatter: (value) => Math.round(value),
      },
    },
    colors: [theme.palette.info.main],
    plotOptions: {
      bar: {
        borderRadius: 4,
        columnWidth: '70%',
      }
    },
    dataLabels: {
      enabled: true,
      formatter: function (val) {
        return Math.round(val);
      },
      style: {
        fontSize: '12px',
        colors: ['#fff'],
        fontFamily: theme.typography.fontFamily,
      },
    },
    grid: {
      borderColor: theme.palette.divider,
      strokeDashArray: 3,
      opacity: 0.5,
    },
    tooltip: {
      theme: theme.palette.mode,
      y: {
        formatter: (value) => Math.round(value),
      },
      style: {
        fontFamily: theme.typography.fontFamily,
      },
    },
  };

  // Find peak months from seasonal patterns
  const findPeakMonths = () => {
    if (!seasonalPatterns.length) return [];
    
    // Get avg value to determine threshold
    const avgQuantity = seasonalPatterns.reduce((acc, item) => acc + item.average_quantity, 0) / seasonalPatterns.length;
    const threshold = avgQuantity * 1.2; // 20% above average
    
    // Find months above threshold
    const peaks = seasonalPatterns
      .filter(item => item.average_quantity > threshold)
      .sort((a, b) => b.average_quantity - a.average_quantity);
    
    return peaks.map(peak => {
      const date = new Date(2025, peak.month - 1, 1);
      const monthName = date.toLocaleString('ar-EG', { month: 'long' });
      const percentage = ((peak.average_quantity / avgQuantity) - 1) * 100;
      
      return {
        month: monthName,
        percentage: Math.round(percentage)
      };
    });
  };

  const peakMonths = findPeakMonths();

  // Render filter panel for category-level tab
  const renderCategoryFilterPanel = () => {
    return (
      <Box sx={{ p: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={5}>
            <FormControl fullWidth size="small">
              <InputLabel id="category-forecast-label">
                اختر الأقسام
              </InputLabel>
              <Select
                labelId="category-forecast-label"
                multiple
                value={selectedDemandCategories}
                onChange={handleDemandCategoryChange}
                input={<OutlinedInput label="اختر الأقسام" />}
                renderValue={(selected) => (
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
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
                    <Checkbox
                      checked={
                        selectedDemandCategories.indexOf(category) > -1
                      }
                    />
                    <ListItemText primary={category} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={3}>
            <Stack direction="row" spacing={2} alignItems="center">
              <FormControlLabel
                control={
                  <Switch
                    checked={showQuantity}
                    onChange={(e) => setShowQuantity(e.target.checked)}
                    color="primary"
                    size="small"
                  />
                }
                label="عرض الكمية"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={showNetProfit}
                    onChange={(e) => setShowNetProfit(e.target.checked)}
                    color="success"
                    size="small"
                  />
                }
                label="عرض الصافي"
              />
            </Stack>
          </Grid>

          <Grid
            item
            xs={12}
            md={4}
            sx={{ display: "flex", justifyContent: "flex-end", gap: 2 }}
          >
            <Button
              variant="outlined"
              color="info"
              startIcon={<Analytics />}
              onClick={() => setShowSeasonalComparison(!showSeasonalComparison)}
              sx={{ height: "40px" }}
            >
              {showSeasonalComparison ? "إخفاء" : "عرض"} التحليل الموسمي
            </Button>
            
            <Button
              variant="contained"
              color="primary"
              startIcon={
                isRunningForecast ? (
                  <CircularProgress size={20} color="inherit" />
                ) : (
                  <Autorenew />
                )
              }
              onClick={runAIForecast}
              disabled={isRunningForecast}
              sx={{ height: "40px", minWidth: "140px" }}
            >
              تشغيل النموذج
            </Button>
          </Grid>
        </Grid>
      </Box>
    );
  };

  // Render filter panel for item-level tab
  const renderItemFilterPanel = () => {
    return (
      <Box sx={{ p: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel id="item-category-label">
                اختر القسم
              </InputLabel>
              <Select
                labelId="item-category-label"
                value={selectedCategory}
                onChange={handleCategoryChange}
                input={<OutlinedInput label="اختر القسم" />}
                disabled={isLoadingItemDemand}
              >
                {categories.map((category) => (
                  <MenuItem key={category} value={category}>
                    {category}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Stack direction="row" spacing={2} alignItems="center">
              <FormControlLabel
                control={
                  <Switch
                    checked={showQuantity}
                    onChange={(e) => setShowQuantity(e.target.checked)}
                    color="primary"
                    size="small"
                  />
                }
                label="عرض الكمية"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={showNetProfit}
                    onChange={(e) => setShowNetProfit(e.target.checked)}
                    color="success"
                    size="small"
                  />
                }
                label="عرض الصافي"
              />
            </Stack>
          </Grid>
          
          <Grid
            item
            xs={12}
            md={6}
            sx={{ display: "flex", justifyContent: "flex-end", gap: 2 }}
          >
            <Button
              variant="outlined"
              color="info"
              startIcon={<Analytics />}
              onClick={() => setShowSeasonalComparison(!showSeasonalComparison)}
              sx={{ height: "40px" }}
            >
              {showSeasonalComparison ? "إخفاء" : "عرض"} التحليل الموسمي
            </Button>
            
            <Button
              variant="contained"
              color="primary"
              startIcon={
                isLoadingItemDemand ? (
                  <CircularProgress size={20} color="inherit" />
                ) : (
                  <ShowChart />
                )
              }
              onClick={fetchItemSpecifications}
              disabled={isLoadingItemDemand || !selectedCategory}
              sx={{ height: "40px", minWidth: "140px" }}
            >
              تحديث البيانات
            </Button>
            
            <Button
              variant="contained"
              color="secondary"
              startIcon={
                isRunningForecast ? (
                  <CircularProgress size={20} color="inherit" />
                ) : (
                  <Autorenew />
                )
              }
              onClick={runAIForecast}
              disabled={isRunningForecast}
              sx={{ height: "40px", minWidth: "140px" }}
            >
              تشغيل النموذج
            </Button>
          </Grid>
        </Grid>
      </Box>
    );
  };

  // Render AI forecast dialog
  const renderForecastDialog = () => {
    return (
      <Dialog
        open={showForecastDialog}
        onClose={forecastSuccess ? () => setShowForecastDialog(false) : undefined}
        maxWidth="sm"
        fullWidth
        aria-labelledby="forecast-dialog-title"
      >
        <DialogTitle id="forecast-dialog-title">
          {forecastSuccess ? "تم بنجاح" : "جاري تشغيل نظام التنبؤ الذكي"}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {forecastError ? (
              <Alert severity="error" sx={{ mt: 2 }}>
                {forecastError}
              </Alert>
            ) : forecastSuccess ? (
              <Alert severity="success" sx={{ mt: 2 }}>
                تم تشغيل نظام التنبؤ الذكي بنجاح!
              </Alert>
            ) : (
              <>
                <Typography variant="body2" gutterBottom>
                  يقوم النظام الآن بتدريب نماذج التنبؤ وإنشاء التوقعات. قد تستغرق هذه العملية بضع دقائق.
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={forecastProgress}
                  sx={{ my: 3, height: 10, borderRadius: 5 }}
                />
                <Typography variant="body2" align="center">
                  {forecastProgress}% مكتمل
                </Typography>
              </>
            )}
          </DialogContentText>

          <Stepper activeStep={forecastStep} sx={{ mt: 4 }}>
            <Step>
              <StepLabel>تحليل البيانات</StepLabel>
            </Step>
            <Step>
              <StepLabel>تدريب النماذج</StepLabel>
            </Step>
            <Step>
              <StepLabel>إنشاء التوقعات</StepLabel>
            </Step>
          </Stepper>
        </DialogContent>
        <DialogActions>
          {(forecastSuccess || forecastError) && (
            <Button onClick={() => setShowForecastDialog(false)}>إغلاق</Button>
          )}
        </DialogActions>
      </Dialog>
    );
  };

  // Render model metrics card
  const renderModelMetricsCard = () => {
    if (!bestModel) return null;

    return (
      <Card 
        elevation={3} 
        sx={{ 
          borderRadius: 3, 
          overflow: "hidden", 
          mb: 3,
          backgroundColor: alpha(theme.palette.primary.main, 0.04),
        }}
      >
        <CardContent>
          <Typography variant="h6" gutterBottom color="primary">
            <Analytics sx={{ verticalAlign: "middle", mr: 1 }} />
            معلومات نموذج التنبؤ
          </Typography>

          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <Typography variant="body2" color="text.secondary">
                نوع النموذج:
              </Typography>
              <Typography variant="body1" fontWeight="medium">
                {bestModel.model_type === 'arima' ? 'ARIMA (نموذج انحدار متكامل متوسط متحرك)' : 
                bestModel.model_type === 'exp_smoothing' ? 'التمهيد الأسي' : 
                bestModel.model_type === 'prophet' ? 'Prophet (نموذج السلاسل الزمنية)' : 
                bestModel.model_type}
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="body2" color="text.secondary">
                القسم:
              </Typography>
              <Typography variant="body1" fontWeight="medium">
                {bestModel.category}
              </Typography>
            </Grid>

            {bestModel.metrics && (
              <>
                <Grid item xs={12} md={3}>
                  <Typography variant="body2" color="text.secondary">
                    RMSE (جذر متوسط مربع الخطأ):
                  </Typography>
                  <Typography variant="body1" fontWeight="medium" color={theme.palette.success.main}>
                    {bestModel.metrics.rmse ? bestModel.metrics.rmse.toFixed(2) : 'غير متاح'}
                  </Typography>
                </Grid>

                <Grid item xs={12} md={3}>
                  <Typography variant="body2" color="text.secondary">
                    MAE (متوسط الخطأ المطلق):
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {bestModel.metrics.mae ? bestModel.metrics.mae.toFixed(2) : 'غير متاح'}
                  </Typography>
                </Grid>

                <Grid item xs={12} md={3}>
                  <Typography variant="body2" color="text.secondary">
                    MAPE (النسبة المئوية للخطأ المطلق):
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {bestModel.metrics.mape ? `${bestModel.metrics.mape.toFixed(2)}%` : 'غير متاح'}
                  </Typography>
                </Grid>

                <Grid item xs={12} md={3}>
                  <Typography variant="body2" color="text.secondary">
                    R² (معامل التحديد):
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {bestModel.metrics.r2 ? bestModel.metrics.r2.toFixed(4) : 'غير متاح'}
                  </Typography>
                </Grid>
              </>
            )}
          </Grid>

          <Box sx={{ mt: 2, p: 2, bgcolor: alpha(theme.palette.info.main, 0.05), borderRadius: 2 }}>
            <Typography variant="body2">
              <Info fontSize="small" sx={{ verticalAlign: "middle", mr: 1, color: theme.palette.info.main }} />
              تم تدريب هذا النموذج باستخدام البيانات التاريخية من 2021 إلى 2024 لإنتاج تنبؤات دقيقة لعام 2025. 
              كلما انخفضت قيمة RMSE، زادت دقة النموذج في التنبؤ.
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  };

  // Render category-level forecast content
  const renderCategoryForecastContent = () => (
    <Box>
      {isLoadingDemand && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {errorDemand && (
        <Alert
          severity="error"
          sx={{ mb: 4, borderRadius: 2 }}
          variant="filled"
        >
          {errorDemand}
        </Alert>
      )}

      {demandMessage &&
        !isLoadingDemand &&
        Object.keys(demandData).length === 0 && (
          <Alert
            severity="warning"
            sx={{ mb: 4, borderRadius: 2 }}
            variant="filled"
          >
            {demandMessage}
          </Alert>
        )}

      {!isLoadingDemand && !errorDemand && Object.keys(demandData).length > 0 && (
        <Grid container spacing={3}>
          {/* Model metrics card */}
          {bestModel && renderModelMetricsCard()}

          {/* Seasonal analysis */}
          {showSeasonalComparison && seasonalPatterns.length > 0 && (
            <Grid item xs={12}>
              <Card elevation={3} sx={{ borderRadius: 3, overflow: "hidden" }}>
                <CardContent>
                  <Chart
                    options={seasonalPatternsOptions}
                    series={seasonalPatternsSeries}
                    type="bar"
                    height={350}
                  />
                  
                  {/* Seasonal insights */}
                  <Box sx={{ mt: 3, p: 2, bgcolor: alpha(theme.palette.info.main, 0.05), borderRadius: 2 }}>
                    <Typography variant="subtitle1" color="primary" fontWeight="bold" gutterBottom>
                      <CalendarMonth sx={{ verticalAlign: 'middle', mr: 1 }} />
                      تحليل الأنماط الموسمية
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    
                    <Box sx={{ ml: 4 }}>
                      <Typography paragraph>
                        <strong>• مواسم ذروة الطلب:</strong> {peakMonths.length > 0 ? (
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
          )}

          {showQuantity && categoryDemandQuantitySeries.length > 0 && (
            <Grid item xs={12}>
              <Card
                elevation={3}
                sx={{
                  borderRadius: 3,
                  overflow: "hidden",
                  maxWidth: "1200px",
                  mx: "auto",
                }}
              >
                <CardContent sx={{ p: 2 }}>
                  <Chart
                    options={quantityChartOptions(false)}
                    series={categoryDemandQuantitySeries}
                    type="line"
                    height={400}
                    width="100%"
                  />
                </CardContent>
              </Card>
            </Grid>
          )}

          {showNetProfit && categoryDemandNetProfitSeries.length > 0 && (
            <Grid item xs={12}>
              <Card
                elevation={3}
                sx={{
                  borderRadius: 3,
                  overflow: "hidden",
                  maxWidth: "1200px",
                  mx: "auto",
                }}
              >
                <CardContent sx={{ p: 2 }}>
                  <Chart
                    options={netProfitChartOptions(false)}
                    series={categoryDemandNetProfitSeries}
                    type="area"
                    height={400}
                    width="100%"
                  />
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      )}
    </Box>
  );

  // Render item-level forecast content
  const renderItemForecastContent = () => (
    <Box>
      {isLoadingItemDemand && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {errorItemDemand && (
        <Alert
          severity="error"
          sx={{ mb: 4, borderRadius: 2 }}
          variant="filled"
        >
          {errorItemDemand}
        </Alert>
      )}

      {!selectedCategory && (
        <Alert
          severity="info"
          sx={{ mb: 4, borderRadius: 2 }}
        >
          يرجى اختيار قسم لعرض توقعات الطلب على مستوى المنتجات
        </Alert>
      )}

      {selectedCategory &&
        !isLoadingItemDemand &&
        !errorItemDemand &&
        (!itemDemandData[selectedCategory] || Object.keys(itemDemandData[selectedCategory]).length === 0) && (
          <Alert
            severity="warning"
            sx={{ mb: 4, borderRadius: 2 }}
          >
            لا توجد بيانات متاحة للمنتجات في هذا القسم
          </Alert>
        )}

      {selectedCategory &&
        !isLoadingItemDemand &&
        !errorItemDemand &&
        itemDemandData[selectedCategory] && (
          <Grid container spacing={3}>
            {/* Model metrics card */}
            {bestModel && renderModelMetricsCard()}

            {/* Seasonal analysis */}
            {showSeasonalComparison && seasonalPatterns.length > 0 && (
              <Grid item xs={12}>
                <Card elevation={3} sx={{ borderRadius: 3, overflow: "hidden" }}>
                  <CardContent>
                    <Chart
                      options={seasonalPatternsOptions}
                      series={seasonalPatternsSeries}
                      type="bar"
                      height={350}
                    />
                    
                    {/* Seasonal insights */}
                    <Box sx={{ mt: 3, p: 2, bgcolor: alpha(theme.palette.info.main, 0.05), borderRadius: 2 }}>
                      <Typography variant="subtitle1" color="primary" fontWeight="bold" gutterBottom>
                        <CalendarMonth sx={{ verticalAlign: 'middle', mr: 1 }} />
                        تحليل الأنماط الموسمية
                      </Typography>
                      <Divider sx={{ mb: 2 }} />
                      
                      <Box sx={{ ml: 4 }}>
                        <Typography paragraph>
                          <strong>• مواسم ذروة الطلب:</strong> {peakMonths.length > 0 ? (
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
            )}

            {itemDemandQuantitySeries.length === 0 && showQuantity && (
              <Grid item xs={12}>
                <Alert severity="info">
                  لا توجد منتجات تشكل ٤٪ أو أكثر من إجمالي الكمية في هذا القسم
                </Alert>
              </Grid>
            )}

            {showQuantity && itemDemandQuantitySeries.length > 0 && (
              <Grid item xs={12} md={6}>
                <Card
                  elevation={3}
                  sx={{
                    borderRadius: 3,
                    overflow: "hidden",
                    height: '100%',
                  }}
                >
                  <CardContent sx={{ p: 2, height: '100%' }}>
                    <Chart
                      options={quantityChartOptions(true)}
                      series={itemDemandQuantitySeries.map(item => item.value)}
                      type="pie"
                      height="400"
                    />
                    
                    {/* Top items list */}
                    <Box sx={{ mt: 3 }}>
                      <Typography variant="subtitle1" gutterBottom>
                        أعلى {Math.min(5, itemDemandQuantitySeries.length)} منتجات من حيث الكمية:
                      </Typography>
                      
                      <Grid container spacing={1}>
                        {itemDemandQuantitySeries.slice(0, 5).map((item, index) => (
                          <Grid item xs={12} key={index}>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                              <Box 
                                sx={{ 
                                  width: 16, 
                                  height: 16, 
                                  borderRadius: '50%', 
                                  bgcolor: getColorPalette()[getCategoryColorIndex(item.name)],
                                  mr: 1.5
                                }} 
                              />
                              <Typography variant="body2" sx={{ flexGrow: 1 }}>
                                {item.name}
                              </Typography>
                              <Typography variant="body2" fontWeight="bold">
                                {item.value.toLocaleString()} ق ({item.percentage.toFixed(1)}%)
                              </Typography>
                            </Box>
                          </Grid>
                        ))}
                      </Grid>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            )}

            {itemDemandNetProfitSeries.length === 0 && showNetProfit && (
              <Grid item xs={12}>
                <Alert severity="info">
                  لا توجد منتجات تشكل ٤٪ أو أكثر من إجمالي المبيعات في هذا القسم
                </Alert>
              </Grid>
            )}

            {showNetProfit && itemDemandNetProfitSeries.length > 0 && (
              <Grid item xs={12} md={6}>
                <Card
                  elevation={3}
                  sx={{
                    borderRadius: 3,
                    overflow: "hidden",
                    height: '100%',
                  }}
                >
                  <CardContent sx={{ p: 2, height: '100%' }}>
                    <Chart
                      options={netProfitChartOptions(true)}
                      series={itemDemandNetProfitSeries.map(item => item.value)}
                      type="pie"
                      height="400"
                    />
                    
                    {/* Top items list */}
                    <Box sx={{ mt: 3 }}>
                      <Typography variant="subtitle1" gutterBottom>
                        أعلى {Math.min(5, itemDemandNetProfitSeries.length)} منتجات من حيث المبيعات:
                      </Typography>
                      
                      <Grid container spacing={1}>
                        {itemDemandNetProfitSeries.slice(0, 5).map((item, index) => (
                          <Grid item xs={12} key={index}>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                              <Box 
                                sx={{ 
                                  width: 16, 
                                  height: 16, 
                                  borderRadius: '50%', 
                                  bgcolor: getColorPalette()[getCategoryColorIndex(item.name)],
                                  mr: 1.5
                                }} 
                              />
                              <Typography variant="body2" sx={{ flexGrow: 1 }}>
                                {item.name}
                              </Typography>
                              <Typography variant="body2" fontWeight="bold">
                                {item.value.toLocaleString()} ج ({item.percentage.toFixed(1)}%)
                              </Typography>
                            </Box>
                          </Grid>
                        ))}
                      </Grid>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            )}
            
            {/* Insights and Recommendations */}
            {(showQuantity || showNetProfit) && (itemDemandQuantitySeries.length > 0 || itemDemandNetProfitSeries.length > 0) && (
              <Grid item xs={12}>
                <Card elevation={3} sx={{ borderRadius: 3, overflow: "hidden" }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom color="primary">
                      <TrendingUp sx={{ verticalAlign: "middle", mr: 1 }} />
                      تحليلات وتوصيات للمنتجات
                    </Typography>
                    
                    <Grid container spacing={3} sx={{ mt: 1 }}>
                      {/* High Demand Items */}
                      <Grid item xs={12} md={4}>
                        <Paper 
                          elevation={0} 
                          sx={{ 
                            p: 2, 
                            bgcolor: alpha(theme.palette.success.main, 0.1),
                            borderRadius: 2,
                            border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`
                          }}
                        >
                          <Typography variant="subtitle1" color="success.main" fontWeight="bold" gutterBottom>
                            منتجات عالية الطلب
                          </Typography>
                          <Typography variant="body2" paragraph sx={{ mb: 2 }}>
                            هذه المنتجات تشكل نسبة كبيرة من الطلب ويجب التركيز على توفرها باستمرار.
                          </Typography>
                          
                          <Box component="ul" sx={{ pl: 2, mb: 0 }}>
                            {itemDemandQuantitySeries.slice(0, 3).map((item, index) => (
                              <Typography component="li" variant="body2" key={index} sx={{ mb: 0.5 }}>
                                {item.name} ({item.percentage.toFixed(1)}% من الكمية)
                              </Typography>
                            ))}
                          </Box>
                        </Paper>
                      </Grid>
                      
                      {/* Seasonal Planning */}
                      <Grid item xs={12} md={4}>
                        <Paper 
                          elevation={0} 
                          sx={{ 
                            p: 2, 
                            bgcolor: alpha(theme.palette.warning.main, 0.1),
                            borderRadius: 2,
                            border: `1px solid ${alpha(theme.palette.warning.main, 0.2)}`,
                            height: '100%'
                          }}
                        >
                          <Typography variant="subtitle1" color="warning.main" fontWeight="bold" gutterBottom>
                            التخطيط الموسمي
                          </Typography>
                          <Typography variant="body2" paragraph>
                            ينصح بزيادة المخزون قبل موسم الذروة بشهر على الأقل.
                          </Typography>
                          
                          <Typography variant="body2" paragraph>
                            {peakMonths.length > 0 ? (
                              <>
                                يجب التركيز على المنتجات عالية الطلب خلال أشهر: {' '}
                                <strong>{peakMonths.map(peak => peak.month).join('، ')}</strong>
                              </>
                            ) : (
                              'حافظ على مستويات متوازنة من المخزون على مدار السنة.'
                            )}
                          </Typography>
                        </Paper>
                      </Grid>
                      
                      {/* Profit Maximization */}
                      <Grid item xs={12} md={4}>
                        <Paper 
                          elevation={0} 
                          sx={{ 
                            p: 2, 
                            bgcolor: alpha(theme.palette.info.main, 0.1),
                            borderRadius: 2,
                            border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                            height: '100%'
                          }}
                        >
                          <Typography variant="subtitle1" color="info.main" fontWeight="bold" gutterBottom>
                            تعظيم الأرباح
                          </Typography>
                          <Typography variant="body2" paragraph>
                            اعتمادًا على بيانات الطلب المتوقعة، يمكن تعديل استراتيجيات التسعير للمنتجات التالية:
                          </Typography>
                          
                          <Box component="ul" sx={{ pl: 2, mb: 0 }}>
                            {itemDemandNetProfitSeries.slice(0, 3).map((item, index) => (
                              <Typography component="li" variant="body2" key={index} sx={{ mb: 0.5 }}>
                                {item.name} (مبيعات متوقعة: {item.value.toLocaleString()} ج)
                              </Typography>
                            ))}
                          </Box>
                        </Paper>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>
        )}
    </Box>
  );

  return (
    <Box>
      <Card
        elevation={0}
        sx={{
          mb: 3,
          borderRadius: 3,
          bgcolor: alpha(theme.palette.primary.main, 0.05),
          border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
        }}
      >
        {/* Header with sub-tabs */}
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs
            value={activeSubTab}
            onChange={handleSubTabChange}
            variant="fullWidth"
            textColor="primary"
            indicatorColor="primary"
            aria-label="demand forecast tabs"
          >
            <Tab
              icon={<CategoryRounded sx={{ mr: 1 }} />}
              iconPosition="start"
              label="توقعات الأقسام"
            />
            <Tab
              icon={<Inventory2Outlined sx={{ mr: 1 }} />}
              iconPosition="start"
              label="توقعات المنتجات"
            />
          </Tabs>
        </Box>

        {/* Filter panel based on active tab */}
        {activeSubTab === 0
          ? renderCategoryFilterPanel()
          : renderItemFilterPanel()}
      </Card>

      {/* Content based on active tab */}
      {activeSubTab === 0
        ? renderCategoryForecastContent()
        : renderItemForecastContent()}

      {/* AI forecast dialog */}
      {renderForecastDialog()}

      {/* Success snackbar */}
      <Snackbar
        open={showSuccessSnackbar}
        autoHideDuration={6000}
        onClose={() => setShowSuccessSnackbar(false)}
        message="تم تشغيل نظام التنبؤ الذكي بنجاح!"
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        action={
          <Button
            color="secondary"
            size="small"
            onClick={() => setShowSuccessSnackbar(false)}
          >
            إغلاق
          </Button>
        }
      />
    </Box>
  );
}

export default DemandForecastComponent;