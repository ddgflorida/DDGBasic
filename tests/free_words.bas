REM Words used by SET EMAIL, EMAIL and LOAD TEXT are ordinary variable names, while those
REM statements still work. Failed checks raise errors.
user = "ann" : text = "hello" : body = 1 : host = "h" : port = 25 : email = "a@x.com"
subject = "s" : password = "p" : domain = "d" : sender = "me" : cc = 2 : bcc = 3
provider = 4 : security = 5 : apikey = 6 : htmlbody = 7
IF user & text & host & email & subject & password & domain & sender <> "annhelloha@x.comspdme" THEN ERROR 1, "string names"
IF body + port + cc + bcc + provider + security + apikey + htmlbody <> 53 THEN ERROR 1, "numeric names"

n = 0
FOR line$ IN TEXT("data/two_lines.txt")
    n = n + 1
NEXT
IF n <> 2 THEN ERROR 1, "FOR ... IN TEXT"
DATABASE OPEN ":memory:"
LOAD TEXT "data/two_lines.txt" CREATE TABLE lines
IF (SELECT COUNT(*) FROM lines) <> 2 THEN ERROR 1, "LOAD TEXT"
DIM t AS TEXT
t = "typed"

REM SET EMAIL and EMAIL still parse; with no mail server the send fails with ERR = -1
SET EMAIL PROVIDER "smtp" HOST "127.0.0.1" PORT 1 USER "u" PASSWORD "p" SENDER "me@x.com" SECURITY "none"
EMAIL TO "you@x.com" CC "c@x.com" SUBJECT "hi" BODY "text" HTMLBODY "<b>x</b>"
IF ERR <> -1 THEN ERROR 1, "EMAIL should have been parsed and tried"
PRINT "free_words: all checks passed"
REM EXPECT: free_words: all checks passed
