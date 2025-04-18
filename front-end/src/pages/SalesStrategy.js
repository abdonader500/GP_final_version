import React from 'react';
import { Box, Typography, Container, alpha, useTheme } from '@mui/material';
import { Lightbulb } from '@mui/icons-material';
import SalesStrategyGenerator from '../components/SalesStrategyGenerator';

const SalesStrategy = () => {
  const theme = useTheme();

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
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
            display: 'flex',
            alignItems: 'center',
            gap: 1.5,
          }}
        >
          <Lightbulb
            sx={{
              color: theme.palette.primary.main,
              fontSize: 28,
            }}
          />
          <Typography variant="h5" component="h1" fontWeight="bold">
            استراتيجيات المبيعات
          </Typography>
        </Box>
      </Box>

      {/* Main Content */}
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'auto',
        }}
      >
        {/* Sales Strategy Generator Component */}
        <SalesStrategyGenerator />
      </Box>
    </Box>
  );
};

export default SalesStrategy;