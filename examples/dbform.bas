REM =============================================
REM  Product Manager Form
REM  Demonstrates DISPLAY, view-switching, and all field types.
REM =============================================
REM --- 1. SETUP DATABASE (for a complete test) ---
DATABASE OPEN "c:\ddg\data\sqlite\hospital.db"
SET UI WEB
REM --- 2. DEFINE THE MASTER FORM ---
FORM docform DISPLAY 10
   SOURCE (SELECT d.* FROM Doctor d ORDER BY 3)
   HEADING "Doctor Information"
   SEPARATOR
   SEPARATOR
   BUTTON "Edit Details" ACTION VIEW_SINGLE
   BUTTON "Back to Grid" ACTION VIEW_GRID   
   BUTTON "Save" ACTION UPDATE            
   BUTTON "Close" ACTION CLOSE            
END FORM

REM --- 3. RUN THE APPLICATION ---
PRINT "Loading Doctor Manager..."

DO
    OPEN FORM docform
    
    REM Check what action the user performed
    IF FORM_RESULT$ = "UPDATE" THEN
        REM User clicked Save - perform the database update
        PRINT "Saving changes..."
        
        REM Get the primary key value
        LET record_id = FORM_SELECTED_ID
        LET first_name$ = FORM_DATA("doc_first_name")
        LET last_name$ = FORM_DATA("doc_last_name") 
        LET phone$ = FORM_DATA("doc_ph_no")
        LET date_val$ = FORM_DATA("doc_date")
        LET address$ = FORM_DATA("doc_address")
		
		REM Debug: Print the variables to see what we have
        PRINT "RECORD_ID = " + STR$(RECORD_ID)
        PRINT "FIRST_NAME$ = " + FIRST_NAME$
        PRINT "LAST_NAME$ = " + LAST_NAME$
		REM DUMP VARIABLES
        REM Build and execute UPDATE statement
        UPDATE Doctor SET 
            doc_first_name = :first_name$,
            doc_last_name = :last_name$,
            doc_ph_no = :phone$,
            doc_date = :date_val$,
            doc_address = :address$
        WHERE doc_id = :record_id;
        
        IF ERR = 0 THEN
            PRINT "Record updated successfully."
        ELSE
            PRINT "Update failed: " + ERRMSG$
        END IF
        
    ELSEIF FORM_RESULT$ = "CLOSE" THEN
        REM User clicked Close - exit the loop
        EXIT DO
        
    ELSEIF FORM_RESULT$ = "CANCEL" THEN
        REM User cancelled - just continue
        PRINT "Operation cancelled."
        
    END IF
    
LOOP UNTIL FORM_RESULT$ = "CLOSE"

PRINT "Application finished."