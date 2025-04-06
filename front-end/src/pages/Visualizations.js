import React, { useState, useEffect } from "react";
import {
  Box,
  Paper,
  Typography,
  Container,
  CircularProgress,
  Alert,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  ListItemText,
  Chip,
  Grid,
  Card,
  CardContent,
  alpha,
  useTheme,
  Tabs,
  Tab,
  OutlinedInput,
  Stack,
  Switch,
  FormControlLabel,
} from "@mui/material";
import {
  BarChart,
  TrendingUp,
  InsertChart,
  DateRange,
  ShowChart,
  QueryStats,
} from "@mui/icons-material";
import Chart from "react-apexcharts";
import axios from "axios";
import SeasonalAnalysisDashboard from "../components/SeasonalAnalysisDashboard";
import CategoryPerformanceDashboard from "../components/CategoryPerformanceDashboard";
import DemandForecastComponent from "../components/DemandForecastComponent";

function Visualizations() {
  const theme = useTheme();

  // Tab state
  const [activeTab, setActiveTab] = useState(0);

  // State for monthly demand data and form
  const [monthlyDemandData, setMonthlyDemandData] = useState([]);
  const [isLoadingMonthlyDemand, setIsLoadingMonthlyDemand] = useState(false);
  const [errorMonthlyDemand, setErrorMonthlyDemand] = useState(null);
  const [monthlyDemandMessage, setMonthlyDemandMessage] = useState(null);
  const [selectedMonthlyDemandCategories, setSelectedMonthlyDemandCategories] =
    useState([]);
  const [startMonthYear, setStartMonthYear] = useState(""); // Format: YYYY-MM
  const [endMonthYear, setEndMonthYear] = useState(""); // Format: YYYY-MM
  const [categories, setCategories] = useState([]);

  // State for toggling quantity and net profit display
  const [showQuantity, setShowQuantity] = useState(true);
  const [showNetProfit, setShowNetProfit] = useState(true);

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  // Set current month for date pickers
  useEffect(() => {
    // Fetch categories to be used in monthly demand
    fetchCategories();
    
    const today = new Date();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const year = today.getFullYear();

    // Set end date to current month
    setEndMonthYear(`${year}-${month}`);

    // Set start date to 6 months ago
    let startMonth = today.getMonth() - 5;
    let startYear = year;

    if (startMonth <= 0) {
      startMonth += 12;
      startYear -= 1;
    }

    setStartMonthYear(`${startYear}-${String(startMonth).padStart(2, "0")}`);
  }, []);

  // Fetch categories
  const fetchCategories = async () => {
    try {
      const response = await axios.get(
        "http://localhost:5000/api/visualization/demand-forecasting"
      );
      const cats = Object.keys(response.data.demand_data || {});
      setCategories(cats);
      setSelectedMonthlyDemandCategories(cats.length > 0 ? [cats[0]] : []);
    } catch (err) {
      console.error("Error fetching categories:", err);
    }
  };

  // Fetch monthly demand data when form is submitted
  const handleMonthlyDemandSubmit = async (e) => {
    if (e) e.preventDefault();
    if (
      !selectedMonthlyDemandCategories.length ||
      !startMonthYear ||
      !endMonthYear
    ) {
      setErrorMonthlyDemand("يرجى ملء جميع الحقول");
      return;
    }

    setIsLoadingMonthlyDemand(true);
    setErrorMonthlyDemand(null);
    setMonthlyDemandMessage(null);

    try {
      console.log("Sending request with params:", {
        categories: selectedMonthlyDemandCategories.join(","),
        start_month_year: startMonthYear,
        end_month_year: endMonthYear,
      });

      const response = await axios.get(
        "http://localhost:5000/api/visualization/monthly-demand",
        {
          params: {
            categories: selectedMonthlyDemandCategories.join(","),
            start_month_year: startMonthYear,
            end_month_year: endMonthYear,
          },
        }
      );

      console.log("Monthly demand response:", response.data);
      setMonthlyDemandData(response.data.monthly_demand_data || []);
      setMonthlyDemandMessage(response.data.message || null);
    } catch (err) {
      setErrorMonthlyDemand(
        "فشل في جلب بيانات الطلب الشهري. يرجى المحاولة مرة أخرى."
      );
      console.error(
        "Error fetching monthly demand data:",
        err.response?.data || err.message
      );
    } finally {
      setIsLoadingMonthlyDemand(false);
    }
  };

  // Handle monthly demand category selection
  const handleMonthlyDemandCategoryChange = (event) => {
    setSelectedMonthlyDemandCategories(event.target.value);
  };

  // Process monthly demand data for quantity chart
  const processMonthlyDemandQuantityData = () => {
    if (!monthlyDemandData || monthlyDemandData.length === 0) {
      return [];
    }

    const groupedData = monthlyDemandData.reduce((acc, item) => {
      const category = item.القسم;
      const monthYear = `${item.year}-${String(item.month).padStart(2, "0")}`;

      if (!acc[category]) {
        acc[category] = [];
      }

      acc[category].push({ x: monthYear, y: item.total_quantity });
      return acc;
    }, {});

    const series = Object.keys(groupedData).map((category) => ({
      name: `${category} - الكمية`,
      type: "line",
      data: groupedData[category],
    }));

    return series;
  };

  // Process monthly demand data for net profit chart
  const processMonthlyDemandNetProfitData = () => {
    if (!monthlyDemandData || monthlyDemandData.length === 0) {
      return [];
    }

    const groupedData = monthlyDemandData.reduce((acc, item) => {
      const category = item.القسم;
      const monthYear = `${item.year}-${String(item.month).padStart(2, "0")}`;

      if (!acc[category]) {
        acc[category] = [];
      }

      acc[category].push({ x: monthYear, y: item.total_money_sold });
      return acc;
    }, {});

    const series = Object.keys(groupedData).map((category) => ({
      name: `${category} - الصافي`,
      type: "area",
      data: groupedData[category],
    }));

    return series;
  };

  const monthlyDemandQuantitySeries = processMonthlyDemandQuantityData();
  const monthlyDemandNetProfitSeries = processMonthlyDemandNetProfitData();

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

  // Chart options for quantity (line chart)
  const quantityChartOptions = {
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
      text: "الكمية الشهرية المباعة",
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
      categories: [
        ...new Set(
          monthlyDemandData.map(
            (item) =>
              `${item.year}-${String(item.month).padStart(2, "0")}`
          )
        ),
      ],
      labels: {
        style: {
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
        },
      },
      title: {
        text: "الشهر/السنة",
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

  // Chart options for net profit (area chart)
  const netProfitChartOptions = {
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
      text: "الصافي الشهري المباع",
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
      categories: [
        ...new Set(
          monthlyDemandData.map(
            (item) =>
              `${item.year}-${String(item.month).padStart(2, "0")}`
          )
        ),
      ],
      labels: {
        style: {
          colors: theme.palette.text.secondary,
          fontFamily: theme.typography.fontFamily,
        },
      },
      title: {
        text: "الشهر/السنة",
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

  const renderHistoricalContent = () => (
    <Box>
      {isLoadingMonthlyDemand && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {errorMonthlyDemand && (
        <Alert
          severity="error"
          sx={{ mb: 4, borderRadius: 2 }}
          variant="filled"
        >
          {errorMonthlyDemand}
        </Alert>
      )}

      {monthlyDemandMessage &&
        !isLoadingMonthlyDemand &&
        monthlyDemandData.length === 0 && (
          <Alert
            severity="warning"
            sx={{ mb: 4, borderRadius: 2 }}
            variant="filled"
          >
            {monthlyDemandMessage}
          </Alert>
        )}

      {!monthlyDemandData.length &&
        !isLoadingMonthlyDemand &&
        !errorMonthlyDemand && (
          <Box sx={{ textAlign: "center", py: 8, px: 2 }}>
            <QueryStats
              sx={{
                fontSize: 60,
                color: alpha(theme.palette.primary.main, 0.4),
                mb: 2,
              }}
            />
            <Typography variant="h6" color="textSecondary" gutterBottom>
              لا توجد بيانات للعرض
            </Typography>
            <Typography variant="body2" color="textSecondary">
              يرجى تحديد الأقسام والتاريخ والضغط على زر "عرض البيانات"
            </Typography>
          </Box>
        )}

      {!isLoadingMonthlyDemand &&
        !errorMonthlyDemand &&
        monthlyDemandData.length > 0 && (
          <Grid container spacing={3}>
            {showQuantity && monthlyDemandQuantitySeries.length > 0 && (
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
                      options={quantityChartOptions}
                      series={monthlyDemandQuantitySeries}
                      type="line"
                      height={400}
                      width="100%"
                    />
                  </CardContent>
                </Card>
              </Grid>
            )}

            {showNetProfit && monthlyDemandNetProfitSeries.length > 0 && (
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
                      options={netProfitChartOptions}
                      series={monthlyDemandNetProfitSeries}
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

  // Render filter panel for historical tab
  const renderHistoricalFilterPanel = () => {
    return (
      <Card
        elevation={0}
        component="form"
        onSubmit={handleMonthlyDemandSubmit}
        sx={{
          mb: 3,
          borderRadius: 3,
          bgcolor: alpha(theme.palette.primary.main, 0.05),
          border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
        }}
      >
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel id="monthly-category-label">
                  اختر الأقسام
                </InputLabel>
                <Select
                  labelId="monthly-category-label"
                  multiple
                  value={selectedMonthlyDemandCategories}
                  onChange={handleMonthlyDemandCategoryChange}
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
                  {categories.map((category) => (
                    <MenuItem key={category} value={category}>
                      <Checkbox
                        checked={
                          selectedMonthlyDemandCategories.indexOf(category) >
                          -1
                        }
                      />
                      <ListItemText primary={category} />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={6} md={2}>
              <TextField
                fullWidth
                size="small"
                label="تاريخ البداية"
                value={startMonthYear}
                onChange={(e) => setStartMonthYear(e.target.value)}
                placeholder="YYYY-MM"
                InputProps={{
                  startAdornment: (
                    <DateRange
                      fontSize="small"
                      color="action"
                      sx={{ mr: 1 }}
                    />
                  ),
                }}
              />
            </Grid>

            <Grid item xs={6} md={2}>
              <TextField
                fullWidth
                size="small"
                label="تاريخ النهاية"
                value={endMonthYear}
                onChange={(e) => setEndMonthYear(e.target.value)}
                placeholder="YYYY-MM"
                InputProps={{
                  startAdornment: (
                    <DateRange
                      fontSize="small"
                      color="action"
                      sx={{ mr: 1 }}
                    />
                  ),
                }}
              />
            </Grid>
            <Grid item xs={6} md={2}>
              <Stack direction="row" spacing={1}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={showQuantity}
                      onChange={(e) => setShowQuantity(e.target.checked)}
                      color="primary"
                      size="small"
                    />
                  }
                  label="الكمية"
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
                  label="الصافي"
                />
              </Stack>
            </Grid>

            <Grid item xs={6} md={2}>
              <Button
                fullWidth
                variant="contained"
                color="primary"
                startIcon={
                  isLoadingMonthlyDemand ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : (
                    <ShowChart />
                  )
                }
                onClick={handleMonthlyDemandSubmit}
                disabled={isLoadingMonthlyDemand}
                type="submit"
                sx={{ height: "40px" }}
              >
                عرض البيانات
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    );
  };

  return (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Page Header */}
      <Box
        sx={{
          p: 3,
          pb: 1,
          background: `linear-gradient(120deg, ${alpha(
            theme.palette.primary.main,
            0.1
          )} 0%, ${alpha(theme.palette.primary.light, 0.15)} 100%)`,
          borderBottom: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 2,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <InsertChart
              sx={{
                color: theme.palette.primary.main,
                fontSize: 28,
              }}
            />
            <Typography variant="h5" component="h1" fontWeight="bold">
              التصورات البيانية
            </Typography>
          </Box>

          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            sx={{
              minHeight: 0,
              "& .MuiTabs-indicator": {
                height: 3,
                borderRadius: "3px 3px 0 0",
              },
              "& .MuiTab-root": {
                minHeight: 0,
                py: 1.5,
                px: 3,
                borderRadius: "8px 8px 0 0",
                fontWeight: "medium",
                fontSize: "0.95rem",
                textTransform: "none",
              },
            }}
          >
            <Tab
              label="توقعات الطلب"
              icon={<TrendingUp />}
              iconPosition="start"
            />
            <Tab
              label="الكميات الشهرية"
              icon={<BarChart />}
              iconPosition="start"
            />
            <Tab
              label="تحليل موسمي مبسط"
              icon={<DateRange />}
              iconPosition="start"
            />
            <Tab
              label="أداء الاقسام"
              icon={<QueryStats />}
              iconPosition="start"
            />
          </Tabs>
        </Box>
      </Box>

      {/* Main Content */}
      <Box
        sx={{
          p: 3,
          flex: 1,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Filter Panel for Historical Tab */}
        {activeTab === 1 && renderHistoricalFilterPanel()}

        {/* Content based on selected tab */}
        <Box sx={{ flex: 1 }}>
          {activeTab === 0 ? (
            <DemandForecastComponent />
          ) : activeTab === 1 ? (
            renderHistoricalContent()
          ) : activeTab === 2 ? (
            <SeasonalAnalysisDashboard />
          ) : (
            <CategoryPerformanceDashboard />
          )}
        </Box>
      </Box>
    </Box>
  );
}

export default Visualizations;