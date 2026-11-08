REM HELP text fixes and ANALYZE JSON wildcards. Failed checks raise errors.
ANALYZE JSON "data/json_glob/*.json" INTO r
IF r("FILE_COUNT") <> 2 THEN ERROR 1, "ANALYZE JSON wildcard file count"
IF r("TOTAL_RECORDS") <> 3 THEN ERROR 1, "ANALYZE JSON wildcard record count"

HELP EXECUTE
REM EXPECT: To run DDGBasic code from a string, use EVAL.
HELP CHAIN
REM EXPECT: CHAIN "filename" [, arg1, arg2, ...] [PRESERVE]
HELP FOR IN
REM EXPECT: FOR f$ IN FILES("*.csv")
HELP SHOW CREATE TABLE
REM EXPECT: SHOW CREATE TABLE [tablename]
HELP INSERT
REM EXPECT: INSERT INTO log (msg) VALUES ('System Start');
HELP EMAIL
REM EXPECT: [HTMLBODY "..."]
PRINT "help_fixes: all checks passed"
REM EXPECT: help_fixes: all checks passed
