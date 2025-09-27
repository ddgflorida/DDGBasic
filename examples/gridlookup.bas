REM ==========================================================
REM  Test Script for the GRIDEDIT LOOKUP Feature
REM  - Requires northwind.db in the same directory
REM ==========================================================
DATABASE OPEN "\ddg\data\sqlite\northwind.db"

PRINT "Loading an editable grid for the 'Orders' table..."
PRINT "The Customer and Employee fields have lookups enabled."
SELECT COUNT(*)  FROM Orders;
REM --- Use GRIDEDIT with two separate LOOKUP clauses ---
GRIDEDIT "Orders" _
    FIELDS "OrderID, CustomerID, EmployeeID, OrderDate, ShipCity" _
    WHERE "CustomerID LIKE 'A%'" _
    SEARCH  _
    LOOKUP CustomerID (SELECT CustomerID, CompanyName, Country FROM Customers) RETURNS "CustomerID" DISPLAY "CompanyName" _
    LOOKUP EmployeeID (SELECT EmployeeID, LastName, FirstName FROM Employees)  RETURNS "EmployeeID" DISPLAY "LastName"

PRINT
PRINT "GRIDEDIT session finished."