REM LOAD ... REJECTS INTO: rejected rows go to a side table with their line number,
REM the reason and the source values before transforms. Failed checks raise errors.
DATABASE OPEN ":memory:"

FUNCTION has_at(v)
    has_at = INSTR(v, "@") > 0
END FUNCTION

FUNCTION qty_ok(r)
    qty_ok = VAL(r.qty) >= 0
END FUNCTION

REM Each kind of rejection is recorded: validate=, VALIDATE col WITH, VALIDATE ROW WITH
LOAD CSV "data/rejects.csv" CREATE TABLE ok REJECTS INTO bad OPTIONS "header=true, transform=name:upper, validate=email:REQUIRED" VALIDATE email WITH has_at VALIDATE ROW WITH qty_ok
REM EXPECT: 2 records loaded into table ok, 3 rejected into bad
IF (SELECT COUNT(*) FROM ok) <> 2 THEN ERROR 1, "loaded rows"
IF (SELECT COUNT(*) FROM bad) <> 3 THEN ERROR 1, "rejected rows"
IF (SELECT _reason FROM bad WHERE id = '2') <> "validate: Column 'email' is REQUIRED but is empty." THEN ERROR 1, "validate= reason"
IF (SELECT _reason FROM bad WHERE id = '4') <> "VALIDATE email WITH HAS_AT" THEN ERROR 1, "VALIDATE col reason"
IF (SELECT _reason FROM bad WHERE id = '3') <> "VALIDATE ROW WITH QTY_OK" THEN ERROR 1, "VALIDATE ROW reason"
IF (SELECT _linenum FROM bad WHERE id = '3') <> 4 THEN ERROR 1, "reject line number"
IF (SELECT name FROM bad WHERE id = '3') <> "cy" THEN ERROR 1, "rejects keep values before transforms"

REM process_by rejections; an existing rejects table is appended to; REJECTS may follow OPTIONS
code$ = "IF rec.id = ""5"" THEN rec.is_valid = 0"
LOAD CSV "data/rejects.csv" INTO TABLE ok TRUNCATE OPTIONS "header=true, process_by=code$" REJECTS INTO TABLE bad
REM EXPECT: 4 records loaded into table ok, 1 rejected into bad
IF (SELECT COUNT(*) FROM bad) <> 4 THEN ERROR 1, "rejects appended"
IF (SELECT _reason FROM bad WHERE id = '5') <> "process_by: rec.is_valid = 0" THEN ERROR 1, "process_by reason"

REM UPSERT and IGNORE report the rejects too
LOAD CSV "data/rejects.csv" INTO TABLE ok UPSERT USING KEY "id" REJECTS INTO bad2 OPTIONS "header=true, validate=email:REQUIRED"
REM EXPECT: 4 records upserted into table ok, 1 rejected into bad2
CREATE TABLE ig (id TEXT PRIMARY KEY, name TEXT, email TEXT, qty TEXT);
LOAD CSV "data/rejects.csv" INTO TABLE ig IGNORE REJECTS INTO bad3 OPTIONS "header=true" VALIDATE email WITH has_at
REM EXPECT: 3 records loaded into table ig (0 ignored), 2 rejected into bad3

REM With no rejects the table is still created, empty
LOAD CSV "data/rejects.csv" CREATE TABLE all_rows REJECTS INTO none OPTIONS "header=true"
REM EXPECT: 5 records loaded into table all_rows, 0 rejected into none
IF (SELECT COUNT(*) FROM none) <> 0 THEN ERROR 1, "empty rejects table"

REM A failed load rolls back its rejects and drops a rejects table it created
CREATE TABLE strict (id TEXT, name TEXT, email TEXT NOT NULL, qty TEXT);
failed = 0
ON ERROR GOTO load_failed
LOAD CSV "data/rejects.csv" INTO TABLE strict REJECTS INTO bad4 OPTIONS "header=true" VALIDATE ROW WITH qty_ok
GOTO after_bad4
load_failed:
failed = failed + 1
RESUME NEXT
after_bad4:
IF failed <> 1 THEN ERROR 1, "the NOT NULL load should fail"
IF (SELECT COUNT(*) FROM sqlite_master WHERE name = 'bad4') <> 0 THEN ERROR 1, "failed load left its rejects table"
CREATE TABLE bad5 (_linenum INTEGER, _reason TEXT, id TEXT, name TEXT, email TEXT, qty TEXT);
LOAD CSV "data/rejects.csv" INTO TABLE strict REJECTS INTO bad5 OPTIONS "header=true" VALIDATE ROW WITH qty_ok
IF failed <> 2 THEN ERROR 1, "the second NOT NULL load should fail"
IF (SELECT COUNT(*) FROM bad5) <> 0 THEN ERROR 1, "failed load kept its rejects"
ON ERROR GOTO 0

REM REJECTS INTO is refused where it can't apply
msg$ = ""
ON ERROR GOTO refused
LOAD CSV "data/rejects.csv" CREATE TABLE same REJECTS INTO same
IF INSTR(msg$, "must not be the LOAD target") = 0 THEN ERROR 1, "same-table message: " + msg$
LOAD JSON "data/people_tags.json" CREATE TABLE p REJECTS INTO pbad OPTIONS "normalize=true"
IF INSTR(msg$, "not supported with normalize") = 0 THEN ERROR 1, "normalize message: " + msg$
ON ERROR GOTO 0
GOTO done
refused:
msg$ = ERRMSG$
RESUME NEXT
done:

PRINT "load_rejects: all checks passed"
REM EXPECT: load_rejects: all checks passed
