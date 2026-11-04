REM Multi-word keywords (END IF, FOR EACH, TO FILE, ...) are joined by the lexer.
REM That must not change text inside strings, SQL literals or comments.
REM Any failed check raises an error (exit 1).
s$ = "send TO FILE, end if, for each, read file, with details, on error goto"
IF LEN(s$) <> 70 THEN ERROR 1, "string changed: " + s$
IF INSTR(s$, "TO FILE") = 0 THEN ERROR 1, "TO FILE collapsed: " + s$
IF INSTR(s$, "for each") = 0 THEN ERROR 1, "for each collapsed: " + s$

b$ = `end function ${1 + 1} line input`
IF b$ <> "end function 2 line input" THEN ERROR 1, "backtick string changed: " + b$

DATABASE OPEN ":memory:"
CREATE TABLE t (s TEXT);
INSERT INTO t VALUES ('for each item'), ('END  IF');
n = (SELECT COUNT(*) FROM t WHERE s = 'for each item')
IF n <> 1 THEN ERROR 1, "SQL literal changed"
n = (SELECT COUNT(*) FROM t WHERE s = 'END  IF')
IF n <> 1 THEN ERROR 1, "SQL literal with spaces changed"

REM The keywords themselves must still work outside strings.
DIM h AS HASH
h("a") = 1
count = 0
FOR EACH k IN HASH h
  IF k = "a" THEN
    count = count + 1
  END IF
NEXT
IF count <> 1 THEN ERROR 1, "FOR EACH / END IF no longer work"

PRINT "keyword_strings: all checks passed"
