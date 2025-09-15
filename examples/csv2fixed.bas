REM -----------------------------------------------------------------
REM CSV to Fixed-Width Converter
REM
REM This script converts a comma-separated value (CSV) file into a
REM fixed-width text file with a single space as a separator.
REM
REM It automatically detects if the input CSV has a header row
REM and calculates the required width for each column.
REM
REM Usage:
REM   python dbbasic.py csv_to_fixed.bas <input.csv> <output.txt>
REM -----------------------------------------------------------------

REM --- 1. Argument Handling ---
IF COMMAND$(1) = "" OR COMMAND$(2) = "" THEN
PRINT "Usage: python dbbasic.py csv_to_fixed.bas <input.csv> <output.txt>"
END
END IF

input_file$ = COMMAND$(1)
output_file$ = COMMAND$(2)

PRINT "Input CSV: "; input_file$
PRINT "Output Fixed-Width: "; output_file$
PRINT ""

REM --- 2. Analyze CSV to Determine Column Widths ---
PRINT "Analyzing CSV..."
DIM report AS HASH
' Analyze the file, automatically detecting if a header row is present.
ANALYZE CSV input_file$ OPTIONS "header=auto" INTO report

IF HASH_COUNT(report) = 0 THEN
PRINT "Error: Failed to analyze CSV file. Ensure it exists and is readable."
END
END IF

stats_hash = report("COLUMN_STATISTICS")
has_header = (report("HEADER_ROW") = -1)
num_columns = HASH_COUNT(stats_hash)

PRINT "Analysis complete. "; num_columns; " columns found."
PRINT ""

REM --- 3. Get Column Order and Store Max Widths ---
DIM column_names AS ARRAY ' This will hold the column keys in the correct order.
DIM widths AS HASH      ' This will store the max width for each column key.

IF has_header THEN
' If a header exists, read the first line to get the exact column order.
h = FREEFILE()
OPEN input_file$ FOR INPUT AS #h
LINE INPUT #h, header_line$
CLOSE #h

raw_headers = SPLIT(header_line$, report("DELIMITER"))
FOR i = 0 TO UBOUND(raw_headers)
    ' Store the original header name. We'll use this to look up values.
    column_names(i) = raw_headers(i)
    ' The stats hash uses cleaned-up header names as keys.
    clean_header$ = REPLACE$(raw_headers(i), CHR$(13), "")
    widths(raw_headers(i)) = stats_hash(clean_header$)("MAX_LEN")
NEXT i

ELSE
' If no header, the keys are "Field_1", "Field_2", etc. We can generate them in order.
FOR i = 1 TO num_columns
key$ = "Field_" + LTRIM$(STR$(i))
column_names(i-1) = key$
widths(key$) = stats_hash(key$)("MAX_LEN")
NEXT i
END IF

REM --- 4. Read CSV and Write Fixed-Width Output ---
PRINT "Writing to "; output_file$; "..."

out_handle = FREEFILE()
OPEN output_file$ FOR OUTPUT AS #out_handle

' Build the options string for the FOR...IN loop
options$ = "header="
IF has_header THEN
options$ = options$ + "true"
ELSE
options$ = options$ + "false"
END IF

FOR rec IN CSV(input_file$) OPTIONS options$
line_out$ = ""
' Loop through the columns in their original order.
FOR i = 0 TO UBOUND(column_names)
col_name$ = column_names(i)

    ' In FOR...IN CSV, if there's no header, keys are "1", "2", etc.
    ' We need to adjust our lookup key accordingly.
    lookup_key$ = col_name$
    IF NOT has_header THEN
        lookup_key$ = LTRIM$(STR$(i + 1))
    END IF

    cell_value$ = rec(lookup_key$)
    max_len = widths(col_name$)
    
    ' Replace newlines and carriage returns with a single space.
    clean_value$ = REPLACE$(cell_value$, CHR$(10), " ")
    clean_value$ = REPLACE$(clean_value$, CHR$(13), "")
    
    ' Truncate if the value is longer than the max length found.
    IF LEN(clean_value$) > max_len THEN
        clean_value$ = LEFT$(clean_value$, max_len)
    END IF
    
    ' Pad the value with spaces to the required width (right-padding).
    padded_value$ = clean_value$
    IF LEN(padded_value$) < max_len THEN
        padded_value$ = padded_value$ + SPACE$(max_len - LEN(padded_value$))
    END IF
    
    ' Add the padded value plus a separator space to the output line.
    line_out$ = line_out$ + padded_value$ + " "
NEXT i

' Remove the trailing space from the end of the line before writing.
PRINT #out_handle, RTRIM$(line_out$)

NEXT
CLOSE #out_handle

PRINT
PRINT "Conversion complete."