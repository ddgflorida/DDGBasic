REM =============================================
REM  Product Manager Form
REM  Demonstrates DISPLAY, view-switching, and all field types.
REM =============================================

REM --- 1. SETUP DATABASE (for a complete test) ---
DATABASE OPEN ":memory:"
CREATE TABLE Products (
  id INTEGER PRIMARY KEY,
  sku TEXT,
  productName TEXT,
  stockQty INTEGER,
  notes TEXT
);
INSERT INTO Products VALUES (101, "A-1001", "Flux Capacitor", 12, "Requires 1.21 gigawatts.");
INSERT INTO Products VALUES (102, "B-2015", "T-800 Endoskeleton", 3, "Cybernetic organism. Living tissue over metal endoskeleton.");
INSERT INTO Products VALUES (103, "C-3PO", "Protocol Droid", 1, "Fluent in over six million forms of communication.");


REM --- 2. DEFINE THE MASTER FORM ---
REM This one form acts as both a grid and a single-record editor.
REM It starts as a grid because DISPLAY > 1.
FORM ProductManager DISPLAY 10 
   SOURCE (SELECT id, sku, productName, stockQty, notes FROM Products ORDER BY sku)

  REM These FIELDs define BOTH the grid columns AND the single-record layout.
  HEADING "Product Record"
  SEPARATOR

  FIELD id TYPE NUMBER LABEL "ID" READONLY

  FIELD sku TYPE TEXT LABEL "SKU" _
    REQUIRED MESSAGE "SKU is required." _
    PATTERN "^[A-Z]-\d{4}$" MESSAGE "SKU must be in the format A-1234."
  
  FIELD productName TYPE TEXT LABEL "Product Name" _
    REQUIRED MESSAGE "Product Name cannot be empty." _
    MAXLENGTH 50 MESSAGE "Name is too long."

  FIELD stockQty TYPE NUMBER LABEL "Stock" _
    REQUIRED MESSAGE "Stock quantity is required." _
    MINVALUE 0 MESSAGE "Stock cannot be negative."

  FIELD notes TYPE MEMO LABEL "Notes" _
    PLACEHOLDER "Enter product details and notes..."

  REM These buttons will be shown contextually by the TUI.
  SEPARATOR
  BUTTON "Edit Details" ACTION VIEW_SINGLE  REM For the grid view
  BUTTON "Back to Grid" ACTION VIEW_GRID    REM For the single-record view
  BUTTON "Save" ACTION UPDATE               REM For the single-record view
  BUTTON "Close" ACTION CLOSE               REM Universal button
END FORM


REM --- 3. RUN THE APPLICATION ---
PRINT "Loading Product Manager..."
OPEN FORM ProductManager

PRINT "Application finished."