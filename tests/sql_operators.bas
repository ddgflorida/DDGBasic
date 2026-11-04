REM SQL operators that are not BASIC characters (||, ~, |, <<) must work inside SQL.
REM Any failed check raises an error (exit 1).
DATABASE OPEN ":memory:"
select 'Hello World' || ' how are you';
CREATE TABLE p (first TEXT, last TEXT);
INSERT INTO p VALUES ('Ann', 'Lee');
full$ = (SELECT first || ' ' || last FROM p)
IF full$ <> "Ann Lee" THEN ERROR 1, "|| in a subquery gave [" + full$ + "]"
n = (SELECT (1 | 2) + (~1) + (1 << 2))
IF n <> 5 THEN ERROR 1, "| ~ << gave " + STR$(n)
FOR r IN (SELECT first || '-' || last AS name FROM p)
  IF r.name <> "Ann-Lee" THEN ERROR 1, "|| in FOR ... IN gave [" + r.name + "]"
NEXT
PRINT "sql_operators: all checks passed"
