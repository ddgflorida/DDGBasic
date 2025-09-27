REM -----------------------------------------------------------------
REM CSV to JSON Converter (with Automatic Type Conversion)
REM
REM This script converts a CSV file into a JSON array, intelligently
REM converting values to numbers or booleans when appropriate.
REM
REM It uses ANALYZE CSV to determine the data type of each column.
REM - If a header exists, it is used for the JSON keys.
REM - If no header exists, keys are generated (C1, C2, C3, ...).
REM
REM Usage:
REM   python dbbasic.py csv2json.bas <input.csv> <output.json>
REM -----------------------------------------------------------------
PRINT PROGRAM$
ON ERROR GOTO errhandler
REM --- 1. Argument Handling ---
IF COMMAND$(1) = "" OR COMMAND$(2) = "" THEN
	PRINT "Usage: python dbbasic.py csv2json.bas <input.csv> <output.json>"
	END
END IF

input_file$ = COMMAND$(1)
output_file$ = COMMAND$(2)

PRINT "Input CSV: "; input_file$
PRINT "Output JSON: "; output_file$
PRINT ""

REM --- 2. Analyze CSV to Determine Structure and Types ---
PRINT "Analyzing CSV..."
DIM report AS HASH
ANALYZE CSV input_file$ OPTIONS "header=auto" INTO report

IF HASH_COUNT(report) = 0 THEN
	PRINT "Error: Failed to analyze CSV file. Ensure it exists and is readable."
	END
END IF

stats_hash = report("COLUMN_STATISTICS")
headers = report("HEADERS")   REM Get the ordered headers directly from the report
has_header = (report("HEADER_ROW") = -1)
num_columns = UBOUND(headers) + 1

PRINT "Analysis complete. "; num_columns; " columns found."
PRINT ""

REM --- 3. Read CSV and Convert Data Types ---
PRINT "Reading CSV data and converting types..."
DIM all_records AS ARRAY
row_num = 0

options$ = "header="
IF has_header THEN
   options$ = options$ + "true"
ELSE
    options$ = options$ + "false"
END IF

FOR rec IN CSV(input_file$) OPTIONS options$
DIM record_hash AS HASH

FOR i = 0 TO UBOUND(headers)
    header_name$ = headers(i)
    
    lookup_key$ = ""
    IF has_header THEN
        lookup_key$ = header_name$
    ELSE
        REM If no header, the keys in the rec hash are "1", "2", etc.
        lookup_key$ = LTRIM$(STR$(i + 1))
    END IF

    cell_value$ = rec(lookup_key$)
    
    REM Get the analysis stats for this column
    column_stats = stats_hash(header_name$)
    suggested_type$ = column_stats("SUGGESTED_SQL_TYPE")

    REM Convert the value based on the suggested type
    IF cell_value$ = "" THEN
        REM Leave empty strings as they are (will become "" in JSON)
        record_hash(header_name$) = cell_value$
    ELSEIF suggested_type$ = "INTEGER" OR suggested_type$ = "REAL" THEN
        REM Clean and convert to number
        cleaned_value$ = REPLACE$(cell_value$, "$", "")
        cleaned_value$ = REPLACE$(cleaned_value$, ",", "")
        record_hash(header_name$) = VAL(cleaned_value$)
    ELSEIF suggested_type$ = "LOGICAL" THEN
        REM Convert to BASIC boolean (-1 for true, 0 for false)
        lower_val$ = LCASE$(cell_value$)
        IF lower_val$ = "true" OR lower_val$ = "t" OR lower_val$ = "y" OR lower_val$ = "yes" OR lower_val$ = "1" THEN
            record_hash(header_name$) = -1.0
        ELSE
            record_hash(header_name$) = 0.0
        END IF
    ELSE
        REM For DATE and TEXT, keep as string
        record_hash(header_name$) = cell_value$
    END IF

NEXT i

all_records(row_num) = record_hash
row_num = row_num + 1

NEXT

PRINT row_num; " data records read."
PRINT ""

REM --- 4. Serialize the Array to JSON and Write to File ---
PRINT "Writing to "; output_file$; "..."

json_output$ = JSON_SERIALIZE$(all_records, 2)    REM Pretty-print with an indent of 2

out_handle = FREEFILE()
OPEN output_file$ FOR OUTPUT AS #out_handle
PRINT #out_handle, json_output$
CLOSE #out_handle

PRINT
PRINT "Conversion complete."
END

errhandler:
  PRINT "=== YOU HAVE AN ERROR ===="
  PRINT ERR
  PRINT ERRMSG$
  PRINT "-------------------------------------------"
  END