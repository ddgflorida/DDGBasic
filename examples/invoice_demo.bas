REM ===================================================================
REM Invoices: a traditional master-detail screen, on the Chinook music-store
REM database. The invoice is a form at the top and its lines a grid below,
REM as invoice screens were in the business software of the 1990s.
REM
REM   PgUp/PgDn  previous/next invoice      F2   find an invoice
REM   F4         edit the invoice header    Ins  add a track
REM   Enter      edit a quantity or price   Del  remove a line
REM   Esc        quit
REM
REM The lines grid hands PgUp, PgDn, F2, F4 and Ins back to the program
REM (BROWSE ... EXIT ON), which acts on LASTKEY$ and shows the grid again.
REM The data is copied into memory first, so the demo never changes the file.
REM ===================================================================
db$ = "data/chinook.sqlite"
IF NOT FILE_EXISTS(db$) THEN db$ = "examples/data/chinook.sqlite"
DATABASE OPEN ":memory:"
ATTACH DATABASE :db$ AS src;
FOR t IN (SELECT name, sql FROM src.sqlite_master WHERE type = 'table'
          AND name IN ('Invoice', 'InvoiceLine', 'Customer', 'Employee', 'Track', 'Album', 'Artist'))
    EXECUTE t.sql
    EXECUTE "INSERT INTO main." & t.name & " SELECT * FROM src." & t.name
NEXT
EXECUTE "DETACH DATABASE src"

SET THEME "default"                    REM SET THEME "classic" gives the blue screens of the time
inv = (SELECT MIN(InvoiceId) FROM Invoice)
CLS
DO
    GOSUB show_invoice
    REM The lines: Quantity and UnitPrice can be edited (the other columns are worked out).
    REM The line's id, which BROWSE needs to save a change, comes last, out of view.
    BROWSE (SELECT (SELECT substr(t.Name, 1, 25) FROM Track t WHERE t.TrackId = l.TrackId) AS track,
                   (SELECT substr(a.Title, 1, 15) FROM Track t JOIN Album a ON a.AlbumId = t.AlbumId
                     WHERE t.TrackId = l.TrackId) AS album,
                   l.Quantity, l.UnitPrice, l.Quantity * l.UnitPrice AS amount, l.InvoiceLineId
              FROM InvoiceLine l WHERE l.InvoiceId = :inv ORDER BY l.InvoiceLineId) _
        EDIT KEY "InvoiceLineId" AT 8, 1, 23, 80 TITLE "Lines" _
        FORMAT UnitPrice "#,##0.00", amount "#,##0.00" EXIT ON "PgUp,PgDn,F2,F4,Ins"
    k$ = LASTKEY$
    REM The total follows the lines
    UPDATE Invoice SET Total = COALESCE((SELECT SUM(UnitPrice * Quantity) FROM InvoiceLine
                                          WHERE InvoiceId = :inv), 0) WHERE InvoiceId = :inv;
    IF k$ = "PGDN" THEN inv = (SELECT COALESCE(MIN(InvoiceId), :inv) FROM Invoice WHERE InvoiceId > :inv)
    IF k$ = "PGUP" THEN inv = (SELECT COALESCE(MAX(InvoiceId), :inv) FROM Invoice WHERE InvoiceId < :inv)
    IF k$ = "F2" THEN GOSUB find_invoice
    IF k$ = "F4" THEN GOSUB edit_header
    IF k$ = "INS" THEN GOSUB add_line
LOOP UNTIL k$ = CHR$(27)

COLOR 7, 0
CLS
FOR h IN (SELECT i.InvoiceId, c.FirstName || ' ' || c.LastName AS customer, i.BillingCity, i.Total,
                 (SELECT COUNT(*) FROM InvoiceLine WHERE InvoiceId = i.InvoiceId) AS lines
            FROM Invoice i JOIN Customer c ON c.CustomerId = i.CustomerId WHERE i.InvoiceId = :inv)
    PRINT "Last invoice: " & LTRIM$(STR$(h.InvoiceId)) & " for " & h.customer & " (" & h.BillingCity & "), " & _
          LTRIM$(STR$(h.lines)) & " lines, total " & TRIM$(FORMAT$(h.Total, "$#,##0.00"))
NEXT
END
REM The test runner plays a session (find, add a track, change its quantity and the city) and checks for:
REM EXPECT: Last invoice: 98 for Luís Gonçalves (Testville), 3 lines, total $6.95

show_invoice:
    REM The header: a form with the invoice, its customer, sales rep and billing address
    FOR h IN (SELECT i.InvoiceId, substr(i.InvoiceDate, 1, 10) AS day, i.Total,
                     i.BillingAddress, i.BillingCity, i.BillingCountry,
                     c.FirstName || ' ' || c.LastName AS customer, COALESCE(c.Company, '') AS company,
                     COALESCE(e.FirstName || ' ' || e.LastName, '') AS rep,
                     (SELECT COUNT(*) FROM Invoice WHERE InvoiceId <= i.InvoiceId) AS position
                FROM Invoice i JOIN Customer c ON c.CustomerId = i.CustomerId
                LEFT JOIN Employee e ON e.EmployeeId = c.SupportRepId
               WHERE i.InvoiceId = :inv)
        BOX 1, 1, 7, 80, "Invoice " & LTRIM$(STR$(h.position)) & " of " & LTRIM$(STR$((SELECT COUNT(*) FROM Invoice))) DOUBLE
        @ 2, 3 SAY "Invoice : " & PADRIGHT$(LTRIM$(STR$(h.InvoiceId)), 12, " ") & "Date : " & h.day
        @ 2, 56 SAY "Total : " & FORMAT$(h.Total, "#,##0.00")
        @ 3, 3 SAY "Customer: " & PADRIGHT$(h.customer, 26, " ") & "Rep  : " & h.rep
        @ 4, 3 SAY "Company : " & h.company
        @ 5, 3 SAY "Bill to : " & h.BillingAddress & ", " & h.BillingCity & ", " & h.BillingCountry
    NEXT
    @ 24, 1 SAY PADRIGHT$(" PgUp/PgDn invoice  F2 find  F4 header  Ins add track  Del remove  Esc quit", 79, " ")
    RETURN

find_invoice:
    BROWSE (SELECT c.LastName || ', ' || c.FirstName AS customer, substr(i.InvoiceDate, 1, 10) AS day,
                   i.Total, i.InvoiceId
              FROM Invoice i JOIN Customer c ON c.CustomerId = i.CustomerId
             ORDER BY customer, i.InvoiceDate) _
        AT 3, 6, 22, 75 TITLE "Find an invoice (type a name)" FORMAT Total "#,##0.00" INTO f
    IF LASTKEY$ <> CHR$(27) THEN inv = f.InvoiceId
    RETURN

edit_header:
    FOR r IN (SELECT CustomerId, substr(InvoiceDate, 1, 10) AS day, BillingAddress, BillingCity, BillingCountry
                FROM Invoice WHERE InvoiceId = :inv)
        BOX 1, 1, 7, 80, "Invoice " & LTRIM$(STR$(inv)) & ": PgDn saves, Esc cancels" DOUBLE
        @ 2, 3 SAY "Customer: " GET r.CustomerId PICTURE "999" _
            LOOKUP (SELECT CustomerId, LastName || ', ' || FirstName AS name FROM Customer ORDER BY name) _
            HINT "The customer's number; F2 lists the customers"
        @ 2, 40 SAY "Date    : " GET r.day PICTURE "@D" HINT "The invoice date: YYYY-MM-DD"
        @ 3, 3 SAY "Address : " GET r.BillingAddress PICTURE "@S50" HINT "Street address for the bill"
        @ 4, 3 SAY "City    : " GET r.BillingCity PICTURE "@S25" HINT "City for the bill"
        @ 5, 3 SAY "Country : " GET r.BillingCountry PICTURE "@S25" HINT "Country for the bill"
        READ
        IF LASTKEY$ <> CHR$(27) THEN
            UPDATE Invoice SET CustomerId = :r.CustomerId, InvoiceDate = :r.day || ' 00:00:00',
                   BillingAddress = :r.BillingAddress, BillingCity = :r.BillingCity,
                   BillingCountry = :r.BillingCountry WHERE InvoiceId = :inv;
        END IF
    NEXT
    RETURN

add_line:
    BROWSE (SELECT t.Name AS track, ar.Name AS artist, a.Title AS album, t.UnitPrice, t.TrackId
              FROM Track t JOIN Album a ON a.AlbumId = t.AlbumId JOIN Artist ar ON ar.ArtistId = a.ArtistId
             ORDER BY t.Name) _
        AT 3, 3, 22, 78 TITLE "Add a track (type its name)" FORMAT UnitPrice "#,##0.00" INTO t
    IF LASTKEY$ <> CHR$(27) THEN
        INSERT INTO InvoiceLine (InvoiceId, TrackId, UnitPrice, Quantity) VALUES (:inv, :t.TrackId, :t.UnitPrice, 1);
    END IF
    RETURN
