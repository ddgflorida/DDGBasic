REM --- ON ERROR GOTO Example ---
REM This program demonstrates how to trap and handle runtime errors.

REM Activate the error handler and tell it to jump to the "ErrorHandler" label on an error
ON ERROR GOTO ErrorHandler

PRINT "--- Test 1: Trapping a recoverable error ---"
PRINT "Attempting to delete a file that does not exist..."
KILL "this_file_does_not_exist.tmp"

PRINT "Program execution has resumed successfully after the error."
PRINT

REM Disable the error handler. Any subsequent errors will be fatal.
PRINT "--- Test 2: Disabling the error handler ---"
ON ERROR GOTO 0
PRINT "Error handler is now disabled."
PRINT "Attempting to divide by zero (this will cause a fatal error)..."

y = 10 / 0

REM This line should never be reached
PRINT "This line will NOT be printed."

END

REM This is the dedicated block of code to handle any errors that occur
ErrorHandler:
PRINT
PRINT "*** In Error Handler ***"
PRINT "Error Code    : ", ERR
PRINT "Error Message : ", ERRMSG$
PRINT "Resuming execution at the next line..."
PRINT
RESUME NEXT