import React from 'react';
import { FormControl, InputLabel, Select, MenuItem, TextField, Button } from '@mui/material';

function PricingForm({
  categories,
  selectedCategory,
  setSelectedCategory,
  purchasePrice,
  setPurchasePrice,
  handleSubmit,
}) {
  return (
    <form onSubmit={handleSubmit}>
      <FormControl fullWidth margin="normal">
        <InputLabel id="category-label">الفئة</InputLabel>
        <Select
          labelId="category-label"
          id="category"
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          required
        >
          <MenuItem value="">اختر الفئة</MenuItem>
          {categories.map((cat) => (
            <MenuItem key={cat} value={cat}>
              {cat}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <TextField
        fullWidth
        margin="normal"
        label="سعر الشراء"
        type="number"
        value={purchasePrice}
        onChange={(e) => setPurchasePrice(e.target.value)}
        inputProps={{ min: 0, step: 0.01 }}
        required
      />
      <Button type="submit" variant="contained" color="primary" sx={{ mt: 2 }}>
        احصل على نسبة الربح المثلى
      </Button>
    </form>
  );
}

export default PricingForm;