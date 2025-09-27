REM ==========================================================
REM  Test Script for the FORM LOOKUP Feature
REM  - Requires northwind.db in the same directory
REM ==========================================================

DATABASE OPEN "c:\ddg\data\sqlite\northwind.db"

REM --- Define the Data Entry Form for the 'Orders' Table ---
FORM Orders_Form TITLE "Edit Order Details"
    SOURCE (SELECT * FROM Orders)

    HEADING "Editing Order"

    FIELD OrderID TYPE TEXT READONLY LABEL "Order ID"
    
    REM --- This is the field with the lookup ---
    FIELD CustomerID TYPE TEXT LABEL "Customer" _
        LOOKUP (SELECT CustomerID, CompanyName, Country FROM Customers ORDER BY CompanyName) _
        RETURNS "CustomerID" _
        DISPLAY "CompanyName"

    FIELD OrderDate TYPE TEXT LABEL "Order Date"
    FIELD ShipCity TYPE TEXT LABEL "Ship to City"

    SEPARATOR

    BUTTON "Save" ACTION "UPDATE"
    BUTTON "Cancel" ACTION "CANCEL"
ENDFORM


REM --- Open the form to edit Order #10248 ---
OPENFORM Orders_Form USING 10248

PRINT
PRINT "Form closed. Action was: "; FORM_RESULT$
PRINT "Selected ID was: "; FORM_SELECTED_ID

REM If data was saved, FORM_DATA will contain the new values
IF FORM_RESULT$ = "UPDATE" THEN
    PRINT "Data from form:"
    PRINT FORM_DATA
END IF