REM ZIP/UNZIP Test Script
REM Creates test files, zips them, unzips to verify, and cleans up

PRINT "ZIP/UNZIP Test Script"
PRINT "===================="
PRINT

REM Create test directory and files
PRINT "Creating test files..."
MKDIR "zip_test"

REM Create some test files with content
OPEN "zip_test/file1.txt" FOR OUTPUT AS #1
PRINT #1, "This is test file 1"
PRINT #1, "Created by ZIP test script"
PRINT #1, "Line 3 of file 1"
CLOSE #1

OPEN "zip_test/file2.txt" FOR OUTPUT AS #2
PRINT #2, "This is test file 2"
PRINT #2, "Different content here"
CLOSE #2

OPEN "zip_test/data.csv" FOR OUTPUT AS #3
PRINT #3, "Name,Age,City"
PRINT #3, "John,25,New York"
PRINT #3, "Jane,30,Los Angeles"
CLOSE #3

REM Create a small BASIC program file
OPEN "zip_test/hello.bas" FOR OUTPUT AS #4
PRINT #4, "REM Simple test program"
PRINT #4, "PRINT " + CHR$(34) + "Hello from ZIP archive!" + CHR$(34)
PRINT #4, "END"
CLOSE #4

PRINT "Created 4 test files in zip_test directory"
PRINT

REM Test ZIP command with individual files
PRINT "Testing ZIP with individual files..."
ZIP "test_archive.zip" FROM "zip_test/file1.txt", "zip_test/file2.txt"

IF ERR = 0 THEN
    PRINT "ZIP completed successfully"
ELSE
    PRINT "ZIP failed: "; ERRMSG$
    GOTO cleanup
END IF

REM Test ZIP with FILES pattern
PRINT "Testing ZIP with FILES pattern..."
ZIP "all_files.zip" FROM "zip_test/*"

IF ERR = 0 THEN
    PRINT "ZIP with pattern completed successfully"
ELSE
    PRINT "ZIP with pattern failed: "; ERRMSG$
END IF

REM Test UNZIP to default location
PRINT "Testing UNZIP to current directory..."
UNZIP "test_archive.zip"

IF ERR = 0 THEN
    PRINT "UNZIP completed successfully"
ELSE
    PRINT "UNZIP failed: "; ERRMSG$
END IF

REM Test UNZIP to specific directory
PRINT "Testing UNZIP to specific directory..."
MKDIR "extracted"
UNZIP "all_files.zip" TO "extracted"

IF ERR = 0 THEN
    PRINT "UNZIP to directory completed successfully"
ELSE
    PRINT "UNZIP to directory failed: "; ERRMSG$
END IF

REM Verify extracted files exist
PRINT
PRINT "Verifying extracted files..."

IF FILE_EXISTS("file1.txt") THEN
    PRINT "✓ file1.txt extracted to current directory"
ELSE
    PRINT "✗ file1.txt not found"
END IF

IF FILE_EXISTS("extracted/data.csv") THEN
    PRINT "✓ data.csv extracted to extracted directory"
ELSE
    PRINT "✗ data.csv not found in extracted directory"
END IF

REM Test running the extracted BASIC program
IF FILE_EXISTS("extracted/hello.bas") THEN
    PRINT "Running extracted BASIC program:"
    RUN "extracted/hello.bas"
    IF ERR = 0 THEN
        PRINT "✓ Extracted program ran successfully"
    ELSE
        PRINT "✗ Error running extracted program: "; ERRMSG$
    END IF
END IF

cleanup:
PRINT
PRINT "Cleaning up test files..."

REM Remove individual extracted files
IF FILE_EXISTS("file1.txt") THEN
    KILL "file1.txt"
    PRINT "Removed file1.txt"
END IF

IF FILE_EXISTS("file2.txt") THEN
    KILL "file2.txt"
    PRINT "Removed file2.txt"
END IF

REM Remove ZIP archives
IF FILE_EXISTS("test_archive.zip") THEN
    KILL "test_archive.zip"
    PRINT "Removed test_archive.zip"
END IF

IF FILE_EXISTS("all_files.zip") THEN
    KILL "all_files.zip"
    PRINT "Removed all_files.zip"
END IF

REM Remove test files in zip_test directory
DIM test_files AS ARRAY
FILES "zip_test/*" INTO test_files

FOR i = 0 TO UBOUND(test_files)
    file_path$ = "zip_test/" + test_files(i)
    IF FILE_EXISTS(file_path$) THEN
        KILL file_path$
    END IF
NEXT i

REM Remove extracted directory and its contents
DIM extracted_files AS ARRAY
FILES "extracted/*" INTO extracted_files

FOR i = 0 TO UBOUND(extracted_files)
    file_path$ = "extracted/" + extracted_files(i)
    IF FILE_EXISTS(file_path$) THEN
        KILL file_path$
    END IF
NEXT i

REM Remove directories
RMDIR "extracted"
RMDIR "zip_test"

PRINT "Cleanup completed"
PRINT
PRINT "ZIP/UNZIP test finished!"

END