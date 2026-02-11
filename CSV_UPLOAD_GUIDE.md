# CSV Upload Feature - Complete Guide

## Overview
The FreshFlow application now supports CSV file uploads to bulk import inventory items. This feature allows you to quickly add hundreds or thousands of items to your inventory at once.

## CSV File Format

### Required Columns
Your CSV file must include these columns (case-insensitive):
- **Item Name** (or `item_name`, `name`)
- **Category** (or `category`)
- **Quantity** (or `quantity`)
- **Expiry Date** (or `expiry_date`, `expirydate`)

### Optional Columns
- **Supplier** (or `supplier`)
- **Supplier Cost** (or `supplier_cost`, `cost`)

### Column Name Variations
The system accepts various column name formats:
- `Item Name`, `item_name`, `Item_Name`, `NAME`
- `Expiry Date`, `expiry_date`, `ExpiryDate`, `EXPIRY_DATE`
- `Supplier Cost`, `supplier_cost`, `Supplier Cost`, `COST`

### Example CSV File

```csv
Item Name,Category,Quantity,Expiry Date,Supplier,Supplier Cost
Fresh Milk,Dairy,50,2024-12-31,Dairy Direct,2.50
Bananas,Fruits,100,2024-12-25,Fresh Foods,1.20
Bread,Grains,30,2024-12-20,Bakery Co,3.00
Chicken Breast,Meat,40,2025-01-05,Meat Market,8.50
Apples,Fruits,75,2025-01-10,Fresh Foods,2.00
```

## Date Format Support

The system accepts dates in multiple formats:
- `YYYY-MM-DD` (e.g., 2024-12-31) - **Recommended**
- `DD/MM/YYYY` (e.g., 31/12/2024)
- `MM/DD/YYYY` (e.g., 12/31/2024)
- `DD-MM-YYYY` (e.g., 31-12-2024)
- `YYYY/MM/DD` (e.g., 2024/12/31)

## How to Use

### Step 1: Prepare Your CSV File
1. Open Excel, Google Sheets, or any spreadsheet application
2. Create columns: Item Name, Category, Quantity, Expiry Date, Supplier, Supplier Cost
3. Fill in your data
4. Save as CSV format (Comma Separated Values)

### Step 2: Upload the File
1. Navigate to the **Inventory** page (`/inventory`)
2. Click the **Upload** icon (📤) in the top-right corner of the inventory table
3. Click **"Select CSV File"** and choose your file
4. Click **"Upload & Import"**
5. Wait for processing to complete

### Step 3: Review Results
- You'll see a summary showing:
  - Total rows processed
  - Successfully imported items
  - Failed rows (if any)
  - Error details for any failed rows

## Handling Large Files (50,000+ Rows)

The system is optimized to handle large CSV files efficiently:

### Automatic Batch Processing
- Files are processed in **batches of 1,000 rows**
- This prevents memory issues and improves performance
- Progress is shown during upload

### Performance Tips
1. **File Size Limit**: Maximum 50MB file size
2. **Processing Time**: 
   - Small files (< 1,000 rows): ~5-10 seconds
   - Medium files (1,000-10,000 rows): ~30-60 seconds
   - Large files (10,000-50,000 rows): ~2-5 minutes
3. **Memory Usage**: The batch processing keeps memory usage low even for very large files

### For Very Large Files (>50,000 rows)
If you have extremely large files:
1. Split your CSV into multiple files (e.g., 10,000 rows each)
2. Upload them one at a time
3. Or consider using the API directly for programmatic imports

## Error Handling

### Common Errors and Solutions

#### Missing Required Columns
**Error**: "Missing required columns: name, category"
**Solution**: Ensure your CSV has columns named Item Name, Category, Quantity, and Expiry Date

#### Invalid Date Format
**Error**: "Row 5: Invalid date format: 31-12-24"
**Solution**: Use full dates like `2024-12-31` or `31/12/2024`

#### Invalid Quantity
**Error**: "Row 10: Invalid quantity value: abc"
**Solution**: Quantity must be a number (integers or decimals)

#### Empty Required Fields
**Error**: "Row 15: Item Name cannot be empty"
**Solution**: Fill in all required fields for each row

### Partial Imports
If some rows fail:
- Successful rows are still imported
- Failed rows are skipped
- Error messages show which rows failed and why
- You can fix the errors and upload again

## Best Practices

1. **Validate Before Upload**
   - Check that all required columns exist
   - Verify date formats
   - Ensure quantities are numbers
   - Remove empty rows

2. **Use Consistent Data**
   - Use the same category names across files
   - Use consistent date formats
   - Keep supplier names consistent

3. **Start Small**
   - Test with a small file (10-20 rows) first
   - Verify the data appears correctly
   - Then upload larger files

4. **Backup Important Data**
   - CSV uploads **add** items to your inventory
   - They don't replace existing items
   - Always verify after upload

5. **Handle Duplicates**
   - The system will allow duplicate items
   - If you want to prevent duplicates, check your inventory first
   - Consider using the edit/delete features to manage duplicates

## Technical Details

### Flask Route
- **Endpoint**: `/inventory/upload-csv`
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Authentication**: Required (login)

### Data Mapping
CSV columns are mapped to MongoDB fields:
- `Item Name` → `name`
- `Category` → `category`
- `Quantity` → `quantity` (converted to integer)
- `Expiry Date` → `expiry_date` (normalized to YYYY-MM-DD)
- `Supplier` → `supplier`
- `Supplier Cost` → `cost` (converted to float)

### Batch Insertion
- Uses MongoDB's `insert_many()` for efficiency
- Batch size: 1,000 items
- `ordered=False` to continue even if some items fail
- Automatically retries on batch failures

### Error Reporting
- Maximum 50 error messages displayed (to prevent UI overload)
- Errors include row numbers for easy identification
- Detailed error messages explain what went wrong

## Example: Complete CSV File

```csv
Item Name,Category,Quantity,Expiry Date,Supplier,Supplier Cost
Fresh Whole Milk,Dairy,45,2024-12-31,Dairy Farm Inc,2.75
Organic Bananas,Fruits,120,2024-12-28,Green Market,1.50
Whole Wheat Bread,Grains,25,2024-12-20,Bakery Fresh,3.25
Chicken Breast - Boneless,Meat,35,2025-01-03,Fresh Meat Co,9.00
Red Delicious Apples,Fruits,90,2025-01-08,Apple Orchard,2.25
Fresh Spinach,Vegetables,60,2024-12-22,Veggie Direct,1.75
Greek Yogurt,Dairy,40,2024-12-30,Yogurt Makers,3.50
Orange Juice - 1L,Beverages,30,2025-01-15,Drink Corp,4.00
Granola Bars,Snacks,50,2025-02-10,Snack Co,2.50
Brown Rice - 1kg,Grains,20,2025-03-01,Grain Suppliers,5.00
```

## Troubleshooting

### File Won't Upload
- Check file size (< 50MB)
- Verify it's a .csv file
- Ensure you're logged in

### Upload Takes Too Long
- Large files take time
- Check your internet connection
- Don't close the browser during upload

### Data Not Appearing
- Refresh the page
- Check the upload results for errors
- Verify the data was actually inserted (check total item count)

### Browser Issues
- Clear browser cache
- Try a different browser
- Check browser console for JavaScript errors

---

**Need Help?** If you encounter issues not covered here, check the error messages in the upload results or contact support.

