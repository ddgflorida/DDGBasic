REM CREATE TRIGGER can be written as line-level SQL and inside EXECUTE, although
REM its body contains ';'. Any failed check raises an error (exit 1).
DATABASE OPEN ":memory:"
CREATE TABLE t (a INTEGER);
CREATE TABLE log (msg TEXT);
CREATE TRIGGER trg AFTER INSERT ON t FOR EACH ROW
BEGIN
  INSERT INTO log VALUES ('added; ' || NEW.a);
  INSERT INTO log VALUES (CASE WHEN NEW.a > 1 THEN 'big' ELSE 'small' END);
END;
INSERT INTO t VALUES (1);
INSERT INTO t VALUES (5);
n = (SELECT COUNT(*) FROM log)
IF n <> 4 THEN ERROR 1, "line-level trigger: log rows = " + STR$(n)
s$ = (SELECT msg FROM log WHERE rowid = 4)
IF s$ <> "big" THEN ERROR 1, "CASE ... END inside the trigger body gave " + s$

EXECUTE "CREATE TEMP TRIGGER trg2 AFTER DELETE ON t BEGIN DELETE FROM log; END; DELETE FROM t"
n = (SELECT COUNT(*) FROM log)
IF n <> 0 THEN ERROR 1, "trigger created by EXECUTE did not run"
PRINT "create_trigger: all checks passed"
