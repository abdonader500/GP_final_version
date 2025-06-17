import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  CircularProgress,
  Alert,
  Paper,
  Divider,
  Grid,
  useTheme,
  alpha,
  Chip,
  TextField,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  Download,
  CalendarMonth,
  Timeline,
  Inventory,
  MonetizationOn,
  CategoryOutlined,
  ShoppingBasket,
  BarChart,
  Lightbulb,
  ExpandMore,
  Campaign,
  LocalOffer,
  Analytics,
  EventNote,
  CompareArrows,
} from "@mui/icons-material";
import axios from "axios";
import Chart from "react-apexcharts";
import { jsPDF } from "jspdf";
import "jspdf-autotable";
import { saveAs } from 'file-saver';
// Import docx library components for Word document generation
import { Document, Packer, Paragraph, TextRun, Table as DocxTable, 
  TableRow as DocxTableRow, TableCell as DocxTableCell, BorderStyle, 
  AlignmentType, HeadingLevel, WidthType } from 'docx';

const SalesStrategyGenerator = () => {
  const theme = useTheme();
  const AmiriRegularBase64 = "data:font/ttf;base64,AAEAAA...";

  // State
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [analysisNotes, setAnalysisNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [strategyData, setStrategyData] = useState(null);
  const [fetchingCategories, setFetchingCategories] = useState(true);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [inflationFactor, setInflationFactor] = useState(30); // Default 30% annual inflation
  const [exportFormat, setExportFormat] = useState("word"); // Default to Word export

  // Fetch categories when component mounts
  useEffect(() => {
    const fetchCategories = async () => {
      setFetchingCategories(true);
      try {
        try {
          const response = await axios.get(
            "http://localhost:5000/api/sales-strategy/categories"
          );
          if (response.data && Array.isArray(response.data)) {
            setCategories(response.data);
            return;
          }
        } catch (apiError) {
          console.error("Error fetching from API:", apiError);
        }

        // Fallback to a default list if API fails
        setCategories([
          "حريمي",
          "رجالي",
          "اطفال",
          "داخلي اطفال",
          "داخلي حريمي",
          "داخلي رجالي",
          "احذية حريمي",
          "احذية رجالي",
          "احذية اطفال",
          "مدارس",
        ]);
      } catch (err) {
        console.error("Error setting categories:", err);
        setError("فشل في جلب قائمة الأقسام. يرجى المحاولة مرة أخرى.");
      } finally {
        setFetchingCategories(false);
      }
    };

    fetchCategories();
  }, []);

  // Handle category selection
  const handleCategoryChange = (event) => {
    setSelectedCategory(event.target.value);
    setStrategyData(null); // Reset strategy data when category changes
  };

  // Handle inflation factor change
  const handleInflationChange = (event) => {
    const value = parseInt(event.target.value);
    if (!isNaN(value) && value >= 0 && value <= 100) {
      setInflationFactor(value);
    }
  };

  // Handle analyst notes change
  const handleAnalysisNotesChange = (event) => {
    setAnalysisNotes(event.target.value);
  };

  // Generate sales strategy
  const generateSalesStrategy = async () => {
    if (!selectedCategory) {
      setError("يرجى اختيار قسم أولاً");
      return;
    }

    setLoading(true);
    setError(null);
    setStrategyData(null);

    try {
      // Call the backend API
      const response = await axios.post(
        "http://localhost:5000/api/sales-strategy/generate",
        {
          category: selectedCategory,
          inflation_factor: inflationFactor,
          analysis_notes: analysisNotes || null,
        }
      );

      // Process the data to enhance the strategy
      const processedData = enhanceStrategyData(response.data);
      setStrategyData(processedData);
    } catch (err) {
      console.error("Error generating sales strategy:", err);
      setError("فشل في إنشاء استراتيجية المبيعات. يرجى المحاولة مرة أخرى.");
    } finally {
      setLoading(false);
    }
  };

  // Enhance the strategy data with additional insights (Unchanged function)
  const enhanceStrategyData = (data) => {
    // If there's no data, return null
    if (!data) return null;

    // Create a deep copy to avoid modifying the original
    const enhancedData = JSON.parse(JSON.stringify(data));

    // Add performance trends analysis if yearly data is available
    if (data.yearlyPerformance && data.yearlyPerformance.length > 1) {
      const years = data.yearlyPerformance.map((y) => y.year);
      const sortedYears = [...years].sort((a, b) => a - b);

      // Calculate year-over-year trends
      const trends = {
        quantity: {},
        revenue: {},
        avgPrice: {},
      };

      // Calculate trends for each year compared to previous
      for (let i = 1; i < sortedYears.length; i++) {
        const currentYear = sortedYears[i];
        const prevYear = sortedYears[i - 1];

        const currentData = data.yearlyPerformance.find(
          (y) => y.year === currentYear
        );
        const prevData = data.yearlyPerformance.find(
          (y) => y.year === prevYear
        );

        if (currentData && prevData) {
          // Calculate percentage changes
          const quantityChange =
            ((currentData.totalQuantity - prevData.totalQuantity) /
              prevData.totalQuantity) *
            100;
          const revenueChange =
            ((currentData.totalRevenue - prevData.totalRevenue) /
              prevData.totalRevenue) *
            100;
          const avgPriceChange =
            ((currentData.avgPrice - prevData.avgPrice) / prevData.avgPrice) *
            100;

          trends.quantity[currentYear] = quantityChange.toFixed(1);
          trends.revenue[currentYear] = revenueChange.toFixed(1);
          trends.avgPrice[currentYear] = avgPriceChange.toFixed(1);
        }
      }

      enhancedData.performanceTrends = trends;

      // Identify if inflation is impacting the business
      // (when price increases but quantity decreases)
      const lastYear = sortedYears[sortedYears.length - 1];
      const secondLastYear = sortedYears[sortedYears.length - 2];

      if (trends.avgPrice[lastYear] > 0 && trends.quantity[lastYear] < 0) {
        enhancedData.inflationImpact = {
          detected: true,
          avgPriceIncrease: trends.avgPrice[lastYear],
          quantityDecrease: Math.abs(trends.quantity[lastYear]),
          year: lastYear,
        };
      } else {
        enhancedData.inflationImpact = {
          detected: false,
        };
      }
    }

    // Enrich seasonal events data
    const seasonalEvents = [
      {
        name: "رمضان",
        months: [8, 9, 10], // Approximate Ramadan months in Hijri calendar
        description: "شهر رمضان المبارك",
        strategicImportance: "مرتفعة",
        salesPattern: data.strongestSeason === "الصيف" ? "ارتفاع" : "معتدل",
      },
      {
        name: "عيد الفطر",
        months: [10],
        description: "عيد الفطر المبارك",
        strategicImportance: "مرتفعة جداً",
        salesPattern: data.peakMonths.includes("شوال")
          ? "ارتفاع حاد"
          : "ارتفاع",
      },
      {
        name: "عيد الأضحى",
        months: [12],
        description: "عيد الأضحى المبارك",
        strategicImportance: "مرتفعة",
        salesPattern: data.peakMonths.includes("ذو الحجة")
          ? "ارتفاع حاد"
          : "ارتفاع",
      },
      {
        name: "العودة للمدارس",
        months: [8, 9], // August/September
        description: "موسم العودة للمدارس",
        strategicImportance:
          data.category.includes("مدارس") || data.category.includes("اطفال")
            ? "مرتفعة جداً"
            : "متوسطة",
        salesPattern:
          data.category.includes("مدارس") && data.peakMonths.includes("سبتمبر")
            ? "ارتفاع حاد"
            : "معتدل",
      },
      {
        name: "الصيف",
        months: [6, 7, 8], // June, July, August
        description: "موسم الصيف",
        strategicImportance:
          data.strongestSeason === "الصيف" ? "مرتفعة" : "متوسطة",
        salesPattern: data.strongestSeason === "الصيف" ? "ارتفاع" : "معتدل",
      },
      {
        name: "الشتاء",
        months: [12, 1, 2], // December, January, February
        description: "موسم الشتاء",
        strategicImportance:
          data.strongestSeason === "الشتاء" ? "مرتفعة" : "متوسطة",
        salesPattern: data.strongestSeason === "الشتاء" ? "ارتفاع" : "معتدل",
      },
    ];

    // Add custom strategies for each event
    seasonalEvents.forEach((event) => {
      // Define strategies based on event and category
      const strategies = [];

      if (event.salesPattern.includes("ارتفاع")) {
        strategies.push("زيادة المخزون قبل الموسم بشهر على الأقل");
        strategies.push("تخصيص ميزانية تسويقية أعلى خلال هذه الفترة");
      }

      if (event.name === "رمضان") {
        strategies.push("تقديم عروض خاصة للتسوق الليلي بعد الإفطار");
        strategies.push("تصميم حملات تسويقية مناسبة لأجواء رمضان");
      }

      if (event.name === "عيد الفطر" || event.name === "عيد الأضحى") {
        strategies.push("تقديم تشكيلة منتجات مميزة للعيد");
        strategies.push("إعداد عروض الهدايا وتغليفها بشكل خاص للعيد");
        strategies.push(
          "تحضير المخزون مبكراً قبل العيد بثلاثة أسابيع على الأقل"
        );
      }

      if (
        event.name === "العودة للمدارس" &&
        (data.category.includes("مدارس") || data.category.includes("اطفال"))
      ) {
        strategies.push("توفير تشكيلة كاملة من ملابس المدارس");
        strategies.push("تقديم خصومات للمشتريات بكميات كبيرة للعائلات");
        strategies.push("تنظيم حملة تسويقية قبل بداية العام الدراسي بشهر");
      }

      if (data.inflationImpact && data.inflationImpact.detected) {
        strategies.push("تقديم خصومات استراتيجية للحفاظ على كمية المبيعات");
        strategies.push("تقديم خيارات بأسعار متنوعة لتناسب جميع الفئات");
      }

      event.strategies = strategies;
    });

    enhancedData.seasonalEvents = seasonalEvents;

    // Create business recommendations based on data analysis
    const businessRecommendations = [];

    // Check for declining quantity trend
    if (
      enhancedData.performanceTrends &&
      Object.values(enhancedData.performanceTrends.quantity).some(
        (val) => parseFloat(val) < 0
      )
    ) {
      businessRecommendations.push({
        title: "استراتيجية لمواجهة انخفاض كميات المبيعات",
        type: "warning",
        icon: <TrendingDown />,
        recommendations: [
          "تطوير حملات ترويجية لزيادة حجم الطلب",
          "تقديم خصومات على الكميات الكبيرة",
          "إعادة تقييم جودة المنتجات ومقارنتها بالمنافسين",
          "استطلاع آراء العملاء لفهم أسباب انخفاض الطلب",
          "تحسين تجربة العملاء وخدمة ما بعد البيع",
        ],
      });
    }

    // Check for inflation impact
    if (enhancedData.inflationImpact && enhancedData.inflationImpact.detected) {
      businessRecommendations.push({
        title: "استراتيجية لمواجهة تأثير التضخم",
        type: "alert",
        icon: <CompareArrows />,
        recommendations: [
          "تطوير خيارات منتجات بأسعار متنوعة لمختلف فئات العملاء",
          "تقديم قيمة إضافية للعملاء لتبرير الزيادة في الأسعار",
          "تحسين كفاءة سلسلة التوريد لتقليل التكاليف",
          "عروض ترويجية استراتيجية للمحافظة على الكميات",
          "تطوير برامج ولاء لتشجيع العملاء على الشراء المتكرر",
        ],
      });
    }

    // Recommendations for peak seasons
    if (enhancedData.strongestSeason) {
      businessRecommendations.push({
        title: `استراتيجية لموسم ${enhancedData.strongestSeason}`,
        type: "success",
        icon: <Timeline />,
        recommendations: [
          "زيادة مستويات المخزون قبل الموسم بفترة كافية",
          "تطوير حملات تسويقية مخصصة للموسم",
          "تدريب فريق المبيعات على التعامل مع الضغط المتزايد",
          "تجهيز العروض الترويجية المناسبة لهذا الموسم",
          "تخصيص مساحة عرض أكبر للمنتجات الأكثر مبيعاً",
        ],
      });
    }

    // Recommendations for weakest season
    if (enhancedData.weakestSeason) {
      businessRecommendations.push({
        title: `استراتيجية لموسم ${enhancedData.weakestSeason}`,
        type: "info",
        icon: <Analytics />,
        recommendations: [
          "تطوير عروض وخصومات لتحفيز الطلب",
          "تنويع التشكيلات المعروضة لجذب اهتمام العملاء",
          "تخفيض مستويات المخزون وتجنب التكدس",
          "الاستفادة من هذه الفترة للتخطيط الاستراتيجي",
          "تطوير منتجات جديدة استعداداً للمواسم القادمة",
        ],
      });
    }

    // Special recommendations for specific categories
    if (enhancedData.category.includes("مدارس")) {
      businessRecommendations.push({
        title: "استراتيجية خاصة لموسم العودة للمدارس",
        type: "primary",
        icon: <EventNote />,
        recommendations: [
          "البدء بالإعداد والتسويق قبل بداية العام الدراسي بشهرين",
          "تقديم عروض للمشتريات الجماعية للمدارس والعائلات",
          "توفير خدمات إضافية مثل التوصيل للمدارس أو الطباعة المجانية للأسماء",
          "تطوير مجموعات متكاملة من مستلزمات المدارس",
          "إقامة شراكات مع المدارس المحلية للحصول على حصة أكبر من السوق",
        ],
      });
    }

    // Add general recommendations based on top products
    if (enhancedData.topProducts && enhancedData.topProducts.length > 0) {
      businessRecommendations.push({
        title: "استراتيجية تطوير المنتجات الرئيسية",
        type: "secondary",
        icon: <Inventory />,
        recommendations: [
          `التركيز على تشكيلة واسعة من ${enhancedData.topProducts[0].name}`,
          "تطوير عروض خاصة للمنتجات الأكثر مبيعاً",
          "قياس رضا العملاء عن المنتجات الرئيسية بشكل مستمر",
          "البحث عن منتجات متكاملة للبيع المتقاطع",
          "الاستثمار في تحسين جودة المنتجات الأكثر مبيعاً",
        ],
      });
      enhancedData.displayTopProducts = enhancedData.topProducts.filter(
        product => product.name !== "غير محدد"
      );
    }

    enhancedData.businessRecommendations = businessRecommendations;

    return enhancedData;
  };
  // Function to generate a Word document with all the strategy data
  // Simple function to generate a Word document with basic content
const generateWordDocument = async (strategyData) => {
  if (!strategyData) return false;
  
  try {
    // Create basic paragraph
    const createParagraph = (text) => {
      return new Paragraph({
        text: text,
        alignment: AlignmentType.RIGHT,
        bidirectional: true,
      });
    };
    
    // Create a simple heading
    const createHeading = (text, level) => {
      return new Paragraph({
        text: text,
        heading: level,
        alignment: AlignmentType.RIGHT,
        bidirectional: true,
      });
    };
    
    // Create a bullet point
    const createBullet = (text) => {
      return new Paragraph({
        text: `• ${text}`,
        alignment: AlignmentType.RIGHT,
        bidirectional: true,
        indent: { left: 720 },
      });
    };
    
    // Create a very basic document structure with minimal formatting
    const children = [
      // Title
      createHeading(`استراتيجية المبيعات: ${strategyData.category}`, HeadingLevel.HEADING_1),
      createParagraph(`تاريخ الإنشاء: ${new Date().toLocaleDateString("ar-EG")}`),
      
      // Summary
      createHeading("ملخص الأداء والتوصيات", HeadingLevel.HEADING_2),
      createParagraph(`إجمالي المبيعات المتوقعة: ${strategyData.annualQuantity.toLocaleString()} قطعة`),
      createParagraph(`إجمالي الإيرادات المتوقعة: ${strategyData.annualRevenue.toLocaleString()} جنيه`),
      createParagraph(`أشهر الذروة: ${strategyData.peakMonths.join("، ")}`),
      createParagraph(`الموسم الأقوى: ${strategyData.strongestSeason}`),
      createParagraph(`الموسم الأضعف: ${strategyData.weakestSeason}`),
      
      // Recommendations
      createHeading("التوصيات الاستراتيجية", HeadingLevel.HEADING_2),
      createBullet(`التركيز الموسمي: تكثيف الجهود التسويقية خلال موسم ${strategyData.strongestSeason} وأشهر الذروة.`),
      createBullet(`تحفيز المبيعات الموسمية: تطبيق استراتيجية تسعير متغيرة خلال العام، مع تقديم عروض خاصة خلال موسم ${strategyData.weakestSeason}.`),
      createBullet("إدارة المخزون: التخطيط المسبق للمخزون بناءً على توقعات الطلب الشهرية."),
    ];
    
    // If there are inflation impacts, add that section
    if (strategyData.inflationImpact && strategyData.inflationImpact.detected) {
      children.push(createHeading("تأثير التضخم", HeadingLevel.HEADING_2));
      children.push(createParagraph(`تم اكتشاف تأثير للتضخم مع زيادة في الأسعار بنسبة ${strategyData.inflationImpact.avgPriceIncrease}% وانخفاض في الكميات بنسبة ${strategyData.inflationImpact.quantityDecrease}%`));
      children.push(createBullet("تطوير خيارات منتجات بفئات سعرية متنوعة"));
      children.push(createBullet("تقديم قيمة إضافية للعملاء لتبرير الزيادة في الأسعار"));
    }
    
    // Add notes if provided
    if (strategyData.analysisNotes) {
      children.push(createHeading("ملاحظات إضافية", HeadingLevel.HEADING_2));
      children.push(createParagraph(strategyData.analysisNotes));
    }
    
    // Create a simple document with minimal formatting
    const doc = new Document({
      sections: [{
        properties: {
          page: {
            margin: {
              top: "2.54cm",
              right: "2.54cm",
              bottom: "2.54cm",
              left: "2.54cm",
            },
          },
        },
        children: children,
      }],
    });
    
    // Generate document buffer
    const buffer = await Packer.toBuffer(doc);
    
    // Create and save blob
    const blob = new Blob([buffer], { 
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
    });
    
    saveAs(blob, `استراتيجية_المبيعات_${strategyData.category}_${Date.now()}.docx`);
    
    return true;
  } catch (error) {
    console.error("Error generating Word document:", error);
    return false;
  }
};

// Enhanced HTML export that will always work as a reliable fallback
const generateHtmlReport = (strategyData) => {
  if (!strategyData) return false;
  
  try {
    // Create a simple HTML report
    const htmlContent = `
      <!DOCTYPE html>
      <html dir="rtl" lang="ar">
      <head>
        <meta charset="UTF-8">
        <title>استراتيجية المبيعات: ${strategyData.category}</title>
        <style>
          body {
            font-family: Arial, 'Segoe UI', Tahoma, sans-serif;
            margin: 20mm;
            direction: rtl;
            text-align: right;
            color: #333;
          }
          h1 {
            color: #333;
            font-size: 24px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
          }
          h2 {
            color: #444;
            font-size: 18px;
            margin-top: 20px;
            background-color: #f8f8f8;
            padding: 8px;
            border-right: 3px solid #3f51b5;
          }
          ul {
            padding-right: 20px;
          }
          li {
            margin-bottom: 8px;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
          }
          th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: right;
          }
          th {
            background-color: #f2f2f2;
          }
          .section {
            margin-bottom: 20px;
          }
          .alert {
            background-color: #ffebee;
            padding: 15px;
            border: 1px solid #ffcdd2;
            border-radius: 4px;
            margin: 15px 0;
          }
          .success {
            background-color: #e8f5e9;
            padding: 15px;
            border: 1px solid #c8e6c9;
            border-radius: 4px;
            margin: 15px 0;
          }
          @media print {
            body {
              margin: 0;
              padding: 15mm;
            }
          }
          .print-button {
            padding: 10px 20px;
            background-color: #4caf50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin: 20px 0;
          }
        </style>
      </head>
      <body>
        <button class="print-button" onclick="window.print()">طباعة التقرير</button>
        
        <h1>استراتيجية المبيعات: ${strategyData.category}</h1>
        <p>تاريخ الإنشاء: ${new Date().toLocaleDateString("ar-EG")}</p>
        
        <div class="section">
          <h2>ملخص الأداء والتوصيات</h2>
          <ul>
            <li>إجمالي المبيعات المتوقعة: ${strategyData.annualQuantity.toLocaleString()} قطعة</li>
            <li>إجمالي الإيرادات المتوقعة: ${strategyData.annualRevenue.toLocaleString()} جنيه</li>
            <li>أشهر الذروة: ${strategyData.peakMonths.join("، ")}</li>
            <li>الموسم الأقوى: ${strategyData.strongestSeason}</li>
            <li>الموسم الأضعف: ${strategyData.weakestSeason}</li>
            ${strategyData.inflationImpact && strategyData.inflationImpact.detected ? 
              `<li>تأثير التضخم: نعم (زيادة السعر ${strategyData.inflationImpact.avgPriceIncrease}% مع انخفاض الكمية ${strategyData.inflationImpact.quantityDecrease}%)</li>` : ''}
          </ul>
        </div>
        
        <div class="section">
          <h2>التحليل الشهري للمبيعات</h2>
          <table>
            <tr>
              <th>الشهر</th>
              <th>الكمية</th>
              <th>الإيرادات</th>
            </tr>
            ${strategyData.monthlyData.map(month => `
            <tr>
              <td>${month.month}</td>
              <td>${month.quantity.toLocaleString()}</td>
              <td>${month.revenue.toLocaleString()} جنيه</td>
            </tr>
            `).join('')}
          </table>
        </div>
        
        <div class="section">
          <h2>التحليل الموسمي للمبيعات</h2>
          <table>
            <tr>
              <th>الموسم</th>
              <th>الكمية</th>
              <th>الإيرادات</th>
            </tr>
            <tr>
              <td>الشتاء</td>
              <td>${strategyData.seasonStats.winter.totalQuantity.toLocaleString()}</td>
              <td>${strategyData.seasonStats.winter.totalRevenue.toLocaleString()} جنيه</td>
            </tr>
            <tr>
              <td>الربيع</td>
              <td>${strategyData.seasonStats.spring.totalQuantity.toLocaleString()}</td>
              <td>${strategyData.seasonStats.spring.totalRevenue.toLocaleString()} جنيه</td>
            </tr>
            <tr>
              <td>الصيف</td>
              <td>${strategyData.seasonStats.summer.totalQuantity.toLocaleString()}</td>
              <td>${strategyData.seasonStats.summer.totalRevenue.toLocaleString()} جنيه</td>
            </tr>
            <tr>
              <td>الخريف</td>
              <td>${strategyData.seasonStats.fall.totalQuantity.toLocaleString()}</td>
              <td>${strategyData.seasonStats.fall.totalRevenue.toLocaleString()} جنيه</td>
            </tr>
          </table>
        </div>
        
        <div class="section">
          <h2>التوصيات الاستراتيجية</h2>
          <div class="success">
            <p>بناءً على تحليل بيانات المبيعات التاريخية لقسم ${strategyData.category}، توصي الاستراتيجية بالتركيز على النقاط التالية:</p>
            <ul>
              ${strategyData.inflationImpact && strategyData.inflationImpact.detected ? `
              <li><strong>مواجهة تأثير التضخم:</strong> تبني استراتيجية تسعير متوازنة للحفاظ على الكميات مع تقديم قيمة مضافة للعملاء لتبرير الزيادة السعرية.</li>
              ` : ''}
              <li><strong>التركيز الموسمي:</strong> تكثيف الجهود التسويقية خلال موسم ${strategyData.strongestSeason} وأشهر الذروة ${strategyData.peakMonths.join("، ")} لتعظيم المبيعات.</li>
              <li><strong>تحفيز المبيعات الموسمية:</strong> تطبيق استراتيجية تسعير متغيرة خلال العام، مع تقديم عروض خاصة خلال موسم ${strategyData.weakestSeason}.</li>
              <li><strong>إدارة المخزون:</strong> التخطيط المسبق للمخزون بناءً على توقعات الطلب الشهرية لضمان توفر المنتجات خلال فترات الذروة وتجنب تكدس المخزون خلال فترات الطلب المنخفض.</li>
            </ul>
          </div>
          
          ${strategyData.analysisNotes ? `
          <div>
            <h3>ملاحظات تحليلية إضافية</h3>
            <p>${strategyData.analysisNotes}</p>
          </div>
          ` : ''}
        </div>
      </body>
      </html>
    `;
    
    // Create a Blob with the HTML content
    const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
    
    // Create a link to download the HTML file
    saveAs(blob, `استراتيجية_المبيعات_${strategyData.category}_${Date.now()}.html`);
    
    return true;
  } catch (err) {
    console.error("Error generating HTML report:", err);
    return false;
  }
};

// The main function that handles document generation
const generatePdfReport = async () => {
  if (!strategyData) return;

  setGeneratingPdf(true);
  setError(null);

  try {
    // Try the Word document generation first
    console.log("Attempting to generate Word document...");
    const wordSuccess = await generateWordDocument(strategyData);
    
    if (wordSuccess) {
      // Word generation successful
      setError(null);
      alert("تم إنشاء ملف Word بنجاح. يمكنك فتحه في برنامج Microsoft Word.");
      setGeneratingPdf(false);
      return;
    }
    
    // If Word generation fails, fall back to HTML
    console.log("Word generation failed, falling back to HTML export...");
    const htmlSuccess = generateHtmlReport(strategyData);
    
    if (htmlSuccess) {
      setError(null);
      alert("تم إنشاء ملف HTML بنجاح. يمكنك فتحه في متصفح الويب وطباعته.");
    } else {
      setError("حدث خطأ أثناء إنشاء التقرير. يرجى المحاولة مرة أخرى.");
    }
  } catch (err) {
    console.error("Error in document generation:", err);
    
    // Always try HTML fallback if Word fails
    try {
      console.log("Exception occurred, trying HTML fallback...");
      const htmlSuccess = generateHtmlReport(strategyData);
      
      if (htmlSuccess) {
        setError(null);
        alert("تم إنشاء ملف HTML بنجاح. يمكنك فتحه في متصفح الويب وطباعته.");
      } else {
        setError("حدث خطأ أثناء إنشاء التقرير. يرجى المحاولة مرة أخرى.");
      }
    } catch (htmlErr) {
      console.error("HTML fallback also failed:", htmlErr);
      setError("حدث خطأ أثناء إنشاء التقرير. يرجى المحاولة مرة أخرى.");
    }
  } finally {
    setGeneratingPdf(false);
  }
};

  // Monthly data chart options
  const getMonthlyChartOptions = () => {
    if (!strategyData) return {};

    return {
      chart: {
        type: "line",
        height: 350,
        toolbar: {
          show: true,
        },
        fontFamily: theme.typography.fontFamily,
      },
      stroke: {
        curve: "smooth",
        width: 3,
      },
      title: {
        text: "أنماط المبيعات الشهرية",
        align: "center",
        style: {
          fontSize: "18px",
          fontWeight: 600,
          fontFamily: theme.typography.fontFamily,
        },
      },
      subtitle: {
        text: "توزيع المبيعات على مدار أشهر السنة",
        align: "center",
        style: {
          fontSize: "12px",
          fontFamily: theme.typography.fontFamily,
        },
      },
      colors: [theme.palette.primary.main, theme.palette.success.main],
      fill: {
        type: "gradient",
        gradient: {
          shade: "light",
          type: "vertical",
          shadeIntensity: 0.3,
          opacityFrom: 0.7,
          opacityTo: 0.2,
          stops: [0, 100],
        },
      },
      markers: {
        size: 5,
        hover: {
          size: 7,
        },
      },
      xaxis: {
        categories: strategyData.monthlyData.map((d) => d.month),
        labels: {
          style: {
            fontFamily: theme.typography.fontFamily,
          },
        },
      },
      yaxis: [
        {
          title: {
            text: "الكمية",
            style: {
              fontFamily: theme.typography.fontFamily,
            },
          },
          labels: {
            formatter: function (val) {
              return val.toFixed(0);
            },
            style: {
              fontFamily: theme.typography.fontFamily,
            },
          },
        },
        {
          opposite: true,
          title: {
            text: "الإيرادات (جنيه)",
            style: {
              fontFamily: theme.typography.fontFamily,
            },
          },
          labels: {
            formatter: function (val) {
              return val.toFixed(0);
            },
            style: {
              fontFamily: theme.typography.fontFamily,
            },
          },
        },
      ],
      tooltip: {
        theme: theme.palette.mode,
        style: {
          fontFamily: theme.typography.fontFamily,
        },
      },
      legend: {
        position: "top",
        horizontalAlign: "right",
        fontFamily: theme.typography.fontFamily,
      },
    };
  };

  // Monthly data series
  const getMonthlyChartSeries = () => {
    if (!strategyData) return [];

    return [
      {
        name: "الكمية",
        type: "line",
        data: strategyData.monthlyData.map((d) => d.quantity),
      },
      {
        name: "الإيرادات",
        type: "area",
        data: strategyData.monthlyData.map((d) => d.revenue),
      },
    ];
  };

  // Yearly performance trend chart
  const getYearlyTrendOptions = () => {
    if (!strategyData || !strategyData.yearlyPerformance) return {};

    return {
      chart: {
        type: "line",
        height: 350,
        toolbar: {
          show: true,
        },
        fontFamily: theme.typography.fontFamily,
      },
      stroke: {
        curve: "straight",
        width: 3,
      },
      title: {
        text: "تحليل أداء المبيعات عبر السنوات",
        align: "center",
        style: {
          fontSize: "18px",
          fontWeight: 600,
          fontFamily: theme.typography.fontFamily,
        },
      },
      subtitle: {
        text: "تطور الكميات والإيرادات ومتوسط الأسعار",
        align: "center",
        style: {
          fontSize: "12px",
          fontFamily: theme.typography.fontFamily,
        },
      },
      colors: [
        theme.palette.primary.main,
        theme.palette.success.main,
        theme.palette.warning.main,
      ],
      markers: {
        size: 6,
      },
      xaxis: {
        categories: strategyData.yearlyPerformance.map((y) =>
          y.year.toString()
        ),
        labels: {
          style: {
            fontFamily: theme.typography.fontFamily,
          },
        },
      },
      yaxis: [
        {
          title: {
            text: "الكمية / الإيرادات",
            style: {
              fontFamily: theme.typography.fontFamily,
            },
          },
          labels: {
            formatter: function (val) {
              return val.toFixed(0);
            },
            style: {
              fontFamily: theme.typography.fontFamily,
            },
          },
        },
        {
          opposite: true,
          title: {
            text: "متوسط السعر",
            style: {
              fontFamily: theme.typography.fontFamily,
            },
          },
          labels: {
            formatter: function (val) {
              return val.toFixed(0);
            },
            style: {
              fontFamily: theme.typography.fontFamily,
            },
          },
        },
      ],
      tooltip: {
        y: {
          formatter: function (val, { seriesIndex }) {
            if (seriesIndex === 2) {
              // Average price
              return val.toFixed(2) + " جنيه";
            }
            return val.toFixed(0);
          },
        },
        theme: theme.palette.mode,
        style: {
          fontFamily: theme.typography.fontFamily,
        },
      },
      legend: {
        position: "top",
        horizontalAlign: "right",
        fontFamily: theme.typography.fontFamily,
      },
    };
  };

  // Yearly performance trend series
  const getYearlyTrendSeries = () => {
    if (!strategyData || !strategyData.yearlyPerformance) return [];

    return [
      {
        name: "الكمية",
        type: "line",
        data: strategyData.yearlyPerformance.map((y) => y.totalQuantity),
      },
      {
        name: "الإيرادات (آلاف)",
        type: "line",
        data: strategyData.yearlyPerformance.map((y) => y.totalRevenue / 1000),
      },
      {
        name: "متوسط السعر",
        type: "line",
        data: strategyData.yearlyPerformance.map((y) => y.avgPrice),
      },
    ];
  };

  // Season comparison chart options
  const getSeasonChartOptions = () => {
    if (!strategyData) return {};

    return {
      chart: {
        type: "bar",
        height: 350,
        stacked: false,
        toolbar: {
          show: true,
        },
        fontFamily: theme.typography.fontFamily,
      },
      plotOptions: {
        bar: {
          horizontal: false,
          borderRadius: 5,
          columnWidth: "55%",
          endingShape: "rounded",
        },
      },
      title: {
        text: "مقارنة المبيعات الموسمية",
        align: "center",
        style: {
          fontSize: "18px",
          fontWeight: 600,
          fontFamily: theme.typography.fontFamily,
        },
      },
      colors: [theme.palette.primary.main, theme.palette.success.main],
      xaxis: {
        categories: ["الشتاء", "الربيع", "الصيف", "الخريف"],
        labels: {
          style: {
            fontFamily: theme.typography.fontFamily,
          },
        },
      },
      yaxis: [
        {
          title: {
            text: "الكمية",
            style: {
              fontFamily: theme.typography.fontFamily,
            },
          },
          labels: {
            formatter: function (val) {
              return val.toFixed(0);
            },
            style: {
              fontFamily: theme.typography.fontFamily,
            },
          },
        },
        {
          opposite: true,
          title: {
            text: "الإيرادات",
            style: {
              fontFamily: theme.typography.fontFamily,
            },
          },
          labels: {
            formatter: function (val) {
              return val.toFixed(0);
            },
            style: {
              fontFamily: theme.typography.fontFamily,
            },
          },
        },
      ],
      tooltip: {
        theme: theme.palette.mode,
        style: {
          fontFamily: theme.typography.fontFamily,
        },
      },
      legend: {
        position: "top",
        horizontalAlign: "right",
        fontFamily: theme.typography.fontFamily,
      },
    };
  };

  // Season comparison series
  const getSeasonChartSeries = () => {
    if (!strategyData) return [];

    return [
      {
        name: "الكمية",
        data: [
          strategyData.seasonStats.winter.totalQuantity,
          strategyData.seasonStats.spring.totalQuantity,
          strategyData.seasonStats.summer.totalQuantity,
          strategyData.seasonStats.fall.totalQuantity,
        ],
      },
      {
        name: "الإيرادات",
        data: [
          strategyData.seasonStats.winter.totalRevenue,
          strategyData.seasonStats.spring.totalRevenue,
          strategyData.seasonStats.summer.totalRevenue,
          strategyData.seasonStats.fall.totalRevenue,
        ],
      },
    ];
  };

  // Product distribution chart options
  const getProductChartOptions = () => {
    if (!strategyData) return {};

    return {
      chart: {
        type: "pie",
        height: 350,
        fontFamily: theme.typography.fontFamily,
      },
      title: {
        text: "توزيع المنتجات الأكثر مبيعًا",
        align: "center",
        style: {
          fontSize: "18px",
          fontWeight: 600,
          fontFamily: theme.typography.fontFamily,
        },
      },
      colors: [
        theme.palette.primary.main,
        theme.palette.primary.light,
        theme.palette.info.main,
        theme.palette.info.light,
        theme.palette.grey[500],
      ],
      labels: strategyData.topProducts.map((p) => p.name),
      responsive: [
        {
          breakpoint: 480,
          options: {
            chart: {
              height: 300,
            },
            legend: {
              position: "bottom",
            },
          },
        },
      ],
      legend: {
        position: "bottom",
        fontFamily: theme.typography.fontFamily,
      },
      tooltip: {
        theme: theme.palette.mode,
        style: {
          fontFamily: theme.typography.fontFamily,
        },
      },
    };
  };

  // Product distribution series
  const getProductChartSeries = () => {
    if (!strategyData) return [];

    return strategyData.topProducts.map((p) => p.percentage);
  };

  // Render the Seasonal Events Section
  const renderSeasonalEventsSection = () => {
    if (!strategyData || !strategyData.seasonalEvents) return null;

    return (
      <Grid item xs={12}>
        <Paper elevation={3} sx={{ p: 3, borderRadius: 3 }}>
          <Typography
            variant="h6"
            gutterBottom
            fontWeight="bold"
            sx={{ display: "flex", alignItems: "center" }}
          >
            <EventNote sx={{ mr: 1, color: theme.palette.primary.main }} />
            استراتيجيات المواسم والمناسبات الخاصة
          </Typography>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow
                  sx={{ bgcolor: alpha(theme.palette.primary.main, 0.05) }}
                >
                  <TableCell sx={{ fontWeight: "bold" }}>
                    الموسم/المناسبة
                  </TableCell>
                  <TableCell sx={{ fontWeight: "bold" }}>
                    الأهمية الاستراتيجية
                  </TableCell>
                  <TableCell sx={{ fontWeight: "bold" }}>
                    نمط المبيعات
                  </TableCell>
                  <TableCell sx={{ fontWeight: "bold" }}>
                    الاستراتيجيات المقترحة
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {strategyData.seasonalEvents.map((event, index) => (
                  <TableRow key={index} hover>
                    <TableCell>{event.name}</TableCell>
                    <TableCell>
                      <Chip
                        label={event.strategicImportance}
                        color={
                          event.strategicImportance === "مرتفعة جداً"
                            ? "error"
                            : event.strategicImportance === "مرتفعة"
                            ? "warning"
                            : "info"
                        }
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>{event.salesPattern}</TableCell>
                    <TableCell>
                      <ul style={{ margin: 0, paddingLeft: 20 }}>
                        {event.strategies.map((strategy, i) => (
                          <li key={i}>{strategy}</li>
                        ))}
                      </ul>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      </Grid>
    );
  };

  // Render the inflation impact section if detected
  const renderInflationImpactSection = () => {
    if (
      !strategyData ||
      !strategyData.inflationImpact ||
      !strategyData.inflationImpact.detected
    )
      return null;

    return (
      <Grid item xs={12}>
        <Paper
          elevation={3}
          sx={{
            p: 3,
            borderRadius: 3,
            backgroundColor: alpha(theme.palette.error.light, 0.05),
            border: `1px solid ${alpha(theme.palette.error.main, 0.2)}`,
          }}
        >
          <Typography
            variant="h6"
            gutterBottom
            fontWeight="bold"
            sx={{
              display: "flex",
              alignItems: "center",
              color: theme.palette.error.dark,
            }}
          >
            <TrendingDown sx={{ mr: 1, color: theme.palette.error.main }} />
            تأثير التضخم على المبيعات
          </Typography>

          <Box sx={{ mt: 2 }}>
            <Typography paragraph>
              تم اكتشاف تأثير محتمل للتضخم على أداء المبيعات في هذه الفئة، حيث
              لوحظ:
            </Typography>

            <Box
              component="ul"
              sx={{
                backgroundColor: alpha(theme.palette.error.main, 0.05),
                borderRadius: 2,
                p: 2,
              }}
            >
              <Box component="li" sx={{ mb: 1 }}>
                <Typography>
                  زيادة في متوسط أسعار البيع بنسبة{" "}
                  <strong>
                    {strategyData.inflationImpact.avgPriceIncrease}%
                  </strong>
                </Typography>
              </Box>

              <Box component="li" sx={{ mb: 1 }}>
                <Typography>
                  انخفاض في كميات المبيعات بنسبة{" "}
                  <strong>
                    {strategyData.inflationImpact.quantityDecrease}%
                  </strong>
                </Typography>
              </Box>

              <Box component="li">
                <Typography>
                  تأثر في سنة{" "}
                  <strong>{strategyData.inflationImpact.year}</strong> مقارنة
                  بالعام السابق
                </Typography>
              </Box>
            </Box>

            <Typography
              variant="subtitle1"
              sx={{ mt: 3, mb: 2, fontWeight: "bold" }}
            >
              استراتيجيات مقترحة لمواجهة تأثير التضخم:
            </Typography>

            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    bgcolor: alpha(theme.palette.warning.main, 0.1),
                  }}
                >
                  <Typography
                    variant="subtitle2"
                    color="warning.dark"
                    fontWeight="bold"
                    gutterBottom
                  >
                    استراتيجية التسعير
                  </Typography>
                  <Box component="ul" sx={{ m: 0 }}>
                    <li>تطوير خيارات منتجات بفئات سعرية متنوعة</li>
                    <li>
                      دراسة مرونة الطلب السعرية لتحديد أفضل استراتيجية تسعير
                    </li>
                    <li>تقديم خصومات موجهة للحفاظ على حجم المبيعات</li>
                  </Box>
                </Box>
              </Grid>

              <Grid item xs={12} md={6}>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    bgcolor: alpha(theme.palette.info.main, 0.1),
                  }}
                >
                  <Typography
                    variant="subtitle2"
                    color="info.dark"
                    fontWeight="bold"
                    gutterBottom
                  >
                    استراتيجية القيمة المضافة
                  </Typography>
                  <Box component="ul" sx={{ m: 0 }}>
                    <li>تحسين جودة المنتجات لتبرير الزيادة السعرية</li>
                    <li>تقديم خدمات إضافية مجانية أو بأسعار رمزية</li>
                    <li>تطوير برامج ولاء للعملاء للحفاظ على قاعدة العملاء</li>
                  </Box>
                </Box>
              </Grid>
            </Grid>
          </Box>
        </Paper>
      </Grid>
    );
  };

  // Render business recommendations
  const renderBusinessRecommendations = () => {
    if (!strategyData || !strategyData.businessRecommendations) return null;

    return (
      <Grid item xs={12}>
        <Paper elevation={3} sx={{ p: 3, borderRadius: 3 }}>
          <Typography
            variant="h6"
            gutterBottom
            fontWeight="bold"
            sx={{ display: "flex", alignItems: "center" }}
          >
            <Lightbulb sx={{ mr: 1, color: theme.palette.primary.main }} />
            التوصيات الاستراتيجية للأعمال
          </Typography>

          <Grid container spacing={3} sx={{ mt: 1 }}>
            {strategyData.businessRecommendations.map((rec, index) => (
              <Grid item xs={12} md={6} key={index}>
                <Accordion defaultExpanded={index === 0}>
                  <AccordionSummary
                    expandIcon={<ExpandMore />}
                    sx={{
                      bgcolor: alpha(
                        rec.type === "warning"
                          ? theme.palette.warning.main
                          : rec.type === "alert"
                          ? theme.palette.error.main
                          : rec.type === "success"
                          ? theme.palette.success.main
                          : rec.type === "info"
                          ? theme.palette.info.main
                          : theme.palette.primary.main,
                        0.1
                      ),
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center" }}>
                      <Box sx={{ mr: 1 }}>{rec.icon}</Box>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {rec.title}
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box component="ol" sx={{ mt: 1, pl: 2 }}>
                      {rec.recommendations.map((item, i) => (
                        <Box component="li" key={i} sx={{ mb: 1 }}>
                          <Typography variant="body2">{item}</Typography>
                        </Box>
                      ))}
                    </Box>
                  </AccordionDetails>
                </Accordion>
              </Grid>
            ))}
          </Grid>
        </Paper>
      </Grid>
    );
  };

  return (
    <Box sx={{ p: 4 }}>
      <Typography
        variant="h5"
        component="h1"
        fontWeight="bold"
        mb={3}
        gutterBottom
        sx={{ display: "flex", alignItems: "center" }}
      >
        <Lightbulb sx={{ mr: 1, color: theme.palette.primary.main }} />
        استراتيجية المبيعات واستشراف الأداء
      </Typography>

      <Paper elevation={3} sx={{ p: 3, borderRadius: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom fontWeight="medium">
          تحليل أداء القسم وإنشاء استراتيجية المبيعات
        </Typography>

        <Typography variant="body2" color="text.secondary" paragraph>
          قم باختيار القسم وإضافة ملاحظاتك ليتم إنشاء استراتيجية مبيعات شاملة،
          مع تحليل للاتجاهات عبر السنوات والمواسم المختلفة، وتوصيات استراتيجية
          محددة للأعمال والتسويق.
        </Typography>

        <Grid container spacing={3} sx={{ mt: 1 }}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel id="category-select-label">القسم</InputLabel>
              <Select
                labelId="category-select-label"
                value={selectedCategory}
                label="القسم"
                onChange={handleCategoryChange}
                disabled={fetchingCategories || loading}
              >
                {categories.map((category) => (
                  <MenuItem key={category} value={category}>
                    {category}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="معدل التضخم السنوي المتوقع (%)"
              type="number"
              value={inflationFactor}
              onChange={handleInflationChange}
              disabled={loading}
              InputProps={{
                startAdornment: (
                  <MonetizationOn sx={{ color: "action.active", mr: 1 }} />
                ),
              }}
              helperText="أدخل معدل التضخم السنوي المتوقع لحساب تأثيره على الأسعار والطلب"
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="ملاحظات وتوجيهات للتحليل (اختياري)"
              multiline
              rows={3}
              value={analysisNotes}
              onChange={handleAnalysisNotesChange}
              disabled={loading}
              placeholder="أضف أي ملاحظات أو توجيهات خاصة ترغب في تضمينها في التحليل والتوصيات"
            />
          </Grid>

          <Grid item xs={12}>
            <Button
              variant="contained"
              color="primary"
              onClick={generateSalesStrategy}
              disabled={fetchingCategories || loading || !selectedCategory}
              startIcon={
                loading ? (
                  <CircularProgress size={20} color="inherit" />
                ) : (
                  <TrendingUp />
                )
              }
              fullWidth
              sx={{ py: 1.5 }}
            >
              {loading ? "جاري التحليل..." : "تحليل وإنشاء الاستراتيجية"}
            </Button>
          </Grid>
        </Grid>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Paper>

      {strategyData && (
        <Box sx={{ mb: 4 }} id="strategyContent">
          <Paper
            elevation={3}
            sx={{
              p: 3,
              borderRadius: 3,
              mb: 4,
              background: `linear-gradient(45deg, ${alpha(
                theme.palette.primary.main,
                0.05
              )} 0%, ${alpha(theme.palette.primary.light, 0.1)} 100%)`,
              border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
            }}
          >
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                flexWrap: "wrap",
                mb: 2,
              }}
            >
              <Box>
                <Typography variant="h5" gutterBottom fontWeight="bold">
                  استراتيجية المبيعات: {strategyData.category}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  تاريخ الإنشاء: {new Date().toLocaleDateString("ar-EG")}
                </Typography>
              </Box>

              <Button
                variant="contained"
                color="primary"
                startIcon={
                  generatingPdf ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : (
                    <Download />
                  )
                }
                onClick={generatePdfReport}
                disabled={generatingPdf}
              >
                {generatingPdf ? "جاري التحميل..." : "تحميل كملف Word"}
              </Button>
            </Box>

            <Divider sx={{ mb: 3 }} />

            <Grid container spacing={2}>
              <Grid item xs={12} md={6} lg={3}>
                <Card
                  sx={{
                    height: "100%",
                    border: `1px solid ${alpha(
                      theme.palette.primary.main,
                      0.2
                    )}`,
                    boxShadow: "none",
                  }}
                >
                  <CardContent sx={{ p: 2 }}>
                  <Typography
                      variant="subtitle1"
                      fontWeight="bold"
                      gutterBottom
                      color="primary"
                      sx={{ display: "flex", alignItems: "center" }}
                    >
                      <MonetizationOn sx={{ mr: 1, fontSize: 20 }} />
                      ملخص المبيعات السنوية
                    </Typography>
                    <Divider sx={{ my: 1 }} />

                    <Box sx={{ mt: 2 }}>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        gutterBottom
                      >
                        إجمالي الكمية المتوقعة
                      </Typography>
                      <Typography variant="h6" fontWeight="bold">
                        {strategyData.annualQuantity.toLocaleString()} قطعة
                      </Typography>
                    </Box>

                    <Box sx={{ mt: 2 }}>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        gutterBottom
                      >
                        إجمالي الإيرادات المتوقعة
                      </Typography>
                      <Typography variant="h6" fontWeight="bold">
                        {strategyData.annualRevenue.toLocaleString()} جنيه
                      </Typography>
                    </Box>

                    {strategyData.inflationImpact &&
                      strategyData.inflationImpact.detected && (
                        <Box
                          sx={{
                            mt: 2,
                            p: 1,
                            borderRadius: 1,
                            bgcolor: alpha(theme.palette.error.main, 0.1),
                            border: `1px dashed ${alpha(
                              theme.palette.error.main,
                              0.4
                            )}`,
                          }}
                        >
                          <Typography
                            variant="body2"
                            color="error"
                            fontWeight="medium"
                          >
                            تأثير التضخم:{" "}
                            {strategyData.inflationImpact.avgPriceIncrease}% ↑
                            سعر, {strategyData.inflationImpact.quantityDecrease}
                            % ↓ كمية
                          </Typography>
                        </Box>
                      )}
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6} lg={3}>
                <Card
                  sx={{
                    height: "100%",
                    border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                    boxShadow: "none",
                  }}
                >
                  <CardContent sx={{ p: 2 }}>
                    <Typography
                      variant="subtitle1"
                      fontWeight="bold"
                      gutterBottom
                      color="info.main"
                      sx={{ display: "flex", alignItems: "center" }}
                    >
                      <CalendarMonth sx={{ mr: 1, fontSize: 20 }} />
                      التحليل الموسمي
                    </Typography>
                    <Divider sx={{ my: 1 }} />

                    <Box sx={{ mt: 2 }}>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        gutterBottom
                      >
                        الموسم الأقوى
                      </Typography>
                      <Typography
                        variant="h6"
                        fontWeight="bold"
                        color="success.main"
                      >
                        {strategyData.strongestSeason}
                      </Typography>
                    </Box>

                    <Box sx={{ mt: 2 }}>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        gutterBottom
                      >
                        الموسم الأضعف
                      </Typography>
                      <Typography
                        variant="h6"
                        fontWeight="bold"
                        color="error.main"
                      >
                        {strategyData.weakestSeason}
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6} lg={3}>
                <Card
                  sx={{
                    height: "100%",
                    border: `1px solid ${alpha(
                      theme.palette.warning.main,
                      0.2
                    )}`,
                    boxShadow: "none",
                  }}
                >
                  <CardContent sx={{ p: 2 }}>
                    <Typography
                      variant="subtitle1"
                      fontWeight="bold"
                      gutterBottom
                      color="warning.main"
                      sx={{ display: "flex", alignItems: "center" }}
                    >
                      <Timeline sx={{ mr: 1, fontSize: 20 }} />
                      أشهر الذروة
                    </Typography>
                    <Divider sx={{ my: 1 }} />

                    <Box
                      sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1 }}
                    >
                      {strategyData.peakMonths.map((month, index) => (
                        <Chip
                          key={index}
                          label={month}
                          color="warning"
                          variant="outlined"
                          size="small"
                          sx={{ fontWeight: "medium" }}
                        />
                      ))}
                    </Box>

                    <Typography
                      variant="body2"
                      sx={{ mt: 2, color: "text.secondary" }}
                    >
                      تحتاج هذه الأشهر لاستراتيجيات خاصة لتعظيم المبيعات
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6} lg={3}>
                <Card
                  sx={{
                    height: "100%",
                    border: `1px solid ${alpha(
                      theme.palette.success.main,
                      0.2
                    )}`,
                    boxShadow: "none",
                  }}
                >
                  <CardContent sx={{ p: 2 }}>
                    <Typography
                      variant="subtitle1"
                      fontWeight="bold"
                      gutterBottom
                      color="success.main"
                      sx={{ display: "flex", alignItems: "center" }}
                    >
                      <Inventory sx={{ mr: 1, fontSize: 20 }} />
                      المنتجات الرئيسية
                    </Typography>
                    <Divider sx={{ my: 1 }} />

                    <Box sx={{ mt: 2 }}>
                      {strategyData.topProducts
                        .slice(0, 10)
                        .map((product, index) => (
                          <Box
                            key={index}
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              mb: 1,
                            }}
                          >
                            <Typography variant="body2">
                              {product.name}
                            </Typography>
                            <Chip
                              label={`${product.percentage}%`}
                              size="small"
                              sx={{
                                bgcolor: alpha(theme.palette.success.main, 0.1),
                                color: "success.main",
                                fontWeight: "bold",
                              }}
                            />
                          </Box>
                        ))}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Paper>

          <Grid container spacing={4}>
            {/* Inflation Impact Section */}
            {renderInflationImpactSection()}

            {/* Yearly Performance Trends */}
            {strategyData.yearlyPerformance &&
              strategyData.yearlyPerformance.length > 1 && (
                <Grid item xs={12}>
                  <Paper elevation={3} sx={{ p: 3, borderRadius: 3 }}>
                    <Chart
                      options={getYearlyTrendOptions()}
                      series={getYearlyTrendSeries()}
                      type="line"
                      height={400}
                    />

                    {strategyData.performanceTrends && (
                      <Box sx={{ mt: 3 }}>
                        <Typography
                          variant="subtitle1"
                          fontWeight="bold"
                          gutterBottom
                        >
                          تحليل اتجاهات الأداء عبر السنوات
                        </Typography>

                        <TableContainer>
                          <Table size="small">
                            <TableHead>
                              <TableRow
                                sx={{
                                  bgcolor: alpha(
                                    theme.palette.primary.main,
                                    0.05
                                  ),
                                }}
                              >
                                <TableCell sx={{ fontWeight: "bold" }}>
                                  السنة
                                </TableCell>
                                <TableCell sx={{ fontWeight: "bold" }}>
                                  تغير الكمية
                                </TableCell>
                                <TableCell sx={{ fontWeight: "bold" }}>
                                  تغير الإيرادات
                                </TableCell>
                                <TableCell sx={{ fontWeight: "bold" }}>
                                  تغير متوسط السعر
                                </TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {Object.keys(strategyData.performanceTrends.quantity).map((year) => (
                                <TableRow key={year}>
                                  <TableCell align="center">{year}</TableCell>
                                  <TableCell align="center">
                                    <Box
                                      sx={{
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center", // Add center justification
                                      }}
                                    >
                                      {parseFloat(strategyData.performanceTrends.quantity[year]) >= 0 ? (
                                        <TrendingUp
                                          fontSize="small"
                                          sx={{
                                            color: "success.main",
                                            mr: 0.5,
                                          }}
                                        />
                                      ) : (
                                        <TrendingDown
                                          fontSize="small"
                                          sx={{ color: "error.main", mr: 0.5 }}
                                        />
                                      )}
                                      <Typography
                                        variant="body2"
                                        color={
                                          parseFloat(strategyData.performanceTrends.quantity[year]) >= 0
                                            ? "success.main"
                                            : "error.main"
                                        }
                                      >
                                        {Math.abs(parseFloat(strategyData.performanceTrends.quantity[year])).toFixed(1)}%
                                      </Typography>
                                    </Box>
                                  </TableCell>
                                  <TableCell align="center">
                                    <Box
                                      sx={{
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center", // Add center justification
                                      }}
                                    >
                                      {parseFloat(strategyData.performanceTrends.revenue[year]) >= 0 ? (
                                        <TrendingUp
                                          fontSize="small"
                                          sx={{
                                            color: "success.main",
                                            mr: 0.5,
                                          }}
                                        />
                                      ) : (
                                        <TrendingDown
                                          fontSize="small"
                                          sx={{ color: "error.main", mr: 0.5 }}
                                        />
                                      )}
                                      <Typography
                                        variant="body2"
                                        color={
                                          parseFloat(strategyData.performanceTrends.revenue[year]) >= 0
                                            ? "success.main"
                                            : "error.main"
                                        }
                                      >
                                        {Math.abs(parseFloat(strategyData.performanceTrends.revenue[year])).toFixed(1)}%
                                      </Typography>
                                    </Box>
                                  </TableCell>
                                  <TableCell align="center">
                                    <Box
                                      sx={{
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center", 
                                      }}
                                    >
                                      {parseFloat(strategyData.performanceTrends.avgPrice[year]) >= 0 ? (
                                        <TrendingUp
                                          fontSize="small"
                                          sx={{
                                            color: "success.main",
                                            mr: 0.5,
                                          }}
                                        />
                                      ) : (
                                        <TrendingDown
                                          fontSize="small"
                                          sx={{ color: "error.main", mr: 0.5 }}
                                        />
                                      )}
                                      <Typography
                                        variant="body2"
                                        color={
                                          parseFloat(strategyData.performanceTrends.avgPrice[year]) >= 0
                                            ? "success.main"
                                            : "error.main"
                                        }
                                      >
                                        {Math.abs(parseFloat(strategyData.performanceTrends.avgPrice[year])).toFixed(1)}%
                                      </Typography>
                                    </Box>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </Box>
                    )}
                  </Paper>
                </Grid>
              )}

            <Grid item xs={12} md={6}>
              <Paper elevation={3} sx={{ p: 3, borderRadius: 3 }}>
                <Chart
                  options={getMonthlyChartOptions()}
                  series={getMonthlyChartSeries()}
                  type="line"
                  height={350}
                />
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper elevation={3} sx={{ p: 3, borderRadius: 3 }}>
                <Chart
                  options={getSeasonChartOptions()}
                  series={getSeasonChartSeries()}
                  type="bar"
                  height={350}
                />
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper elevation={3} sx={{ p: 3, borderRadius: 3 }}>
                <Chart
                  options={getProductChartOptions()}
                  series={getProductChartSeries()}
                  type="pie"
                  height={350}
                />
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper elevation={3} sx={{ p: 3, borderRadius: 3 }}>
                <Typography
                  variant="h6"
                  gutterBottom
                  fontWeight="bold"
                  sx={{ display: "flex", alignItems: "center" }}
                >
                  <CategoryOutlined
                    sx={{ mr: 1, color: theme.palette.primary.main }}
                  />
                  توصيات التسعير الموسمية
                </Typography>

                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow
                        sx={{
                          bgcolor: alpha(theme.palette.primary.main, 0.05),
                        }}
                      >
                        <TableCell sx={{ fontWeight: "bold" }}>
                          الموسم
                        </TableCell>
                        <TableCell sx={{ fontWeight: "bold" }}>
                          تعديل السعر
                        </TableCell>
                        <TableCell sx={{ fontWeight: "bold" }}>السبب</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {strategyData.pricingRecommendations.map((rec, index) => (
                        <TableRow key={index} hover>
                          <TableCell>{rec.season}</TableCell>
                          <TableCell>
                            <Chip
                              label={rec.adjustment}
                              color={
                                rec.adjustment.includes("+")
                                  ? "success"
                                  : "error"
                              }
                              size="small"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>{rec.reason}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>

            {/* Seasonal Events Section */}
            {renderSeasonalEventsSection()}

            <Grid item xs={12}>
              <Paper elevation={3} sx={{ p: 3, borderRadius: 3 }}>
                <Typography
                  variant="h6"
                  gutterBottom
                  fontWeight="bold"
                  sx={{ display: "flex", alignItems: "center" }}
                >
                  <Campaign sx={{ mr: 1, color: theme.palette.primary.main }} />
                  الحملات التسويقية المقترحة
                </Typography>

                <Grid container spacing={2} sx={{ mt: 1 }}>
                  {strategyData.marketingCampaigns.map((campaign, index) => (
                    <Grid item xs={12} md={6} lg={3} key={index}>
                      <Card
                        sx={{
                          height: "100%",
                          bgcolor: alpha(theme.palette.primary.main, 0.03),
                        }}
                      >
                        <CardContent>
                          <Typography
                            variant="subtitle1"
                            gutterBottom
                            fontWeight="bold"
                          >
                            {campaign.name}
                          </Typography>

                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              mb: 1,
                            }}
                          >
                            <CalendarMonth
                              sx={{
                                fontSize: 18,
                                mr: 1,
                                color: "text.secondary",
                              }}
                            />
                            <Typography variant="body2">
                              التوقيت: {campaign.timing}
                            </Typography>
                          </Box>

                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              mb: 1,
                            }}
                          >
                            <ShoppingBasket
                              sx={{
                                fontSize: 18,
                                mr: 1,
                                color: "text.secondary",
                              }}
                            />
                            <Typography variant="body2">
                              التركيز: {campaign.focus}
                            </Typography>
                          </Box>

                          <Box sx={{ display: "flex", alignItems: "center" }}>
                            <MonetizationOn
                              sx={{
                                fontSize: 18,
                                mr: 1,
                                color: "text.secondary",
                              }}
                            />
                            <Typography variant="body2">
                              الميزانية: {campaign.budget}
                            </Typography>
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </Paper>
            </Grid>

            {/* Business Recommendations Section */}
            {renderBusinessRecommendations()}

            <Grid item xs={12}>
              <Paper
                elevation={3}
                sx={{
                  p: 3,
                  borderRadius: 3,
                  background: `linear-gradient(45deg, ${alpha(
                    theme.palette.success.main,
                    0.05
                  )} 0%, ${alpha(theme.palette.primary.light, 0.1)} 100%)`,
                  border: `1px solid ${alpha(theme.palette.success.main, 0.1)}`,
                }}
              >
                <Typography
                  variant="h6"
                  gutterBottom
                  fontWeight="bold"
                  sx={{ display: "flex", alignItems: "center" }}
                >
                  <Lightbulb
                    sx={{ mr: 1, color: theme.palette.success.main }}
                  />
                  الخلاصة والتوصيات النهائية
                </Typography>

                <Typography paragraph>
                  بناءً على تحليل بيانات المبيعات التاريخية لقسم{" "}
                  <strong>{strategyData.category}</strong>، توصي الاستراتيجية
                  بالتركيز على النقاط التالية:
                </Typography>

                <Box component="ul" sx={{ pl: 2 }}>
                  {strategyData.inflationImpact &&
                  strategyData.inflationImpact.detected ? (
                    <Box component="li" sx={{ mb: 1 }}>
                      <Typography>
                        <strong>مواجهة تأثير التضخم:</strong> تبني استراتيجية
                        تسعير متوازنة للحفاظ على الكميات مع تقديم قيمة مضافة
                        للعملاء لتبرير الزيادة السعرية.
                      </Typography>
                    </Box>
                  ) : null}

                  <Box component="li" sx={{ mb: 1 }}>
                    <Typography>
                      <strong>التركيز الموسمي:</strong> تكثيف الجهود التسويقية
                      خلال موسم <strong>{strategyData.strongestSeason}</strong>{" "}
                      وأشهر الذروة{" "}
                      <strong>{strategyData.peakMonths.join("، ")}</strong>{" "}
                      لتعظيم المبيعات.
                    </Typography>
                  </Box>

                  <Box component="li" sx={{ mb: 1 }}>
                    <Typography>
                      <strong>تحفيز المبيعات الموسمية:</strong> تطبيق استراتيجية
                      تسعير متغيرة خلال العام، مع تقديم عروض خاصة خلال موسم{" "}
                      <strong>{strategyData.weakestSeason}</strong>.
                    </Typography>
                  </Box>

                  {strategyData.topProducts &&
                  strategyData.topProducts.length > 0 ? (
                    <Box component="li" sx={{ mb: 1 }}>
                      <Typography>
                        <strong>تطوير المنتجات الرئيسية:</strong> الاستثمار في
                        تطوير وترويج{" "}
                        <strong>{strategyData.topProducts[0].name}</strong> و
                        <strong>
                          {strategyData.topProducts[1]?.name || ""}
                        </strong>{" "}
                        للاستفادة من شعبيتها في السوق.
                      </Typography>
                    </Box>
                  ) : null}

                  <Box component="li">
                    <Typography>
                      <strong>إدارة المخزون:</strong> التخطيط المسبق للمخزون
                      بناءً على توقعات الطلب الشهرية لضمان توفر المنتجات خلال
                      فترات الذروة وتجنب تكدس المخزون خلال فترات الطلب المنخفض.
                    </Typography>
                  </Box>
                </Box>

                {analysisNotes && (
                  <Box
                    sx={{
                      mt: 3,
                      p: 2,
                      bgcolor: alpha(theme.palette.info.main, 0.1),
                      borderRadius: 2,
                    }}
                  >
                    <Typography
                      variant="subtitle2"
                      sx={{ color: "info.dark", fontWeight: "bold", mb: 1 }}
                    >
                      ملاحظات تحليلية إضافية
                    </Typography>
                    <Typography variant="body2">{analysisNotes}</Typography>
                  </Box>
                )}
              </Paper>
            </Grid>
          </Grid>
        </Box>
      )}
    </Box>
  );
};

export default SalesStrategyGenerator;
                          
                    
                