import React from 'react';
import { Typography, Box } from '@mui/material';

function ResultsDisplay({ result }) {
  const priceLevelMap = {
    low: 'منخفض',
    moderate: 'متوسط',
    high: 'مرتفع',
    very_high: 'مرتفع جدا',
  };

  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h5" gutterBottom>
        النتائج
      </Typography>
      <Typography>الفئة: {result.category}</Typography>
      <Typography>السعر الأصلي: {result.original_price}</Typography>
      <Typography>السعر المعدل (2023): {result.adjusted_price_2023}</Typography>
      <Typography>مستوى السعر: {priceLevelMap[result.classified_price_level]}</Typography>
      <Typography>نسبة الربح المثلى: {result.optimal_profit_percentage}%</Typography>
    </Box>
  );
}

export default ResultsDisplay;