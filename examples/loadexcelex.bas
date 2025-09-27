REM ---
REM Example: Convert an Excel sheet to a JSON file with transformations.
REM ---

PRINT "--- Starting Excel to JSON Conversion ---"
PRINT

REM --- Configuration ---
REM Set the path to your source Excel file and the desired output file.
excel_file$ = "c:\ddg\data\excel\salesdata.xlsx"
PRINT "Loading Excel data into a SQL table. Using file: ";excel_file$
PRINT "Header is:"; "Product ID     Region     Sales Amount"
PRINT
PRINT "--- Define Options ---"
PRINT "1. sheetname: Specify the exact sheet to load."
PRINT "2. fields: Select and rename columns."
PRINT "3. transform: Clean up the data by trimming and uppercasing the Region."
PRINT "4. format: Specify the output format as JSON."
options$ = `sheetname="SalesData" fields=[Product ID] as product_id,[Region],[Sales Amount] as amount transform=trimall;Region:upper`
PRINT "Source File: "; excel_file$
PRINT "Using Options: "; options$
PRINT

REM --- Run the Conversion ---
LOAD EXCEL excel_file$ CREATE TABLE excel_sample OPTIONS options$

IF ERR <> 0 THEN
    PRINT "An error occurred during the conversion:"
    PRINT ERRMSG$
    END
END IF
PRINT
DESCRIBE TABLE "excel_sample"
PRINT
PRINT "--- Verification ---"
PRINT "SELECT the table data to verify its content..."

SELECT * FROM excel_sample;

PRINT
PRINT "--- Process Complete ---"
END
