REM ANALYZE fixes: INTO without DIM, HEADERS as an array, JSONL non-object counts,
REM multi-file XML INTO in either clause order. Failed checks raise errors.
ANALYZE CSV "data/schema_cols.csv" INTO c
IF UBOUND(c.HEADERS) <> 2 OR c.HEADERS(1) <> "name" THEN ERROR 1, "ANALYZE CSV HEADERS array"

ANALYZE JSONL "data/mixed.jsonl" INTO j
IF j.TOTAL_RECORDS <> 5 THEN ERROR 1, "JSONL TOTAL_RECORDS = " + STR$(j.TOTAL_RECORDS)
IF j.VALID_JSON_RECORDS <> 2 THEN ERROR 1, "JSONL VALID_JSON_RECORDS = " + STR$(j.VALID_JSON_RECORDS)
IF j.NON_OBJECT_RECORDS <> 2 OR j.INVALID_JSON_RECORDS <> 1 THEN ERROR 1, "JSONL non-object/invalid counts"

ANALYZE XML "data/xml/*.xml" INTO x SAVE SCHEMA TO "xml_schema.json"
IF x.FILE_COUNT <> 2 OR x.ROOT_ELEMENT <> "orders" THEN ERROR 1, "multi-file ANALYZE XML INTO"
IF NOT FILE_EXISTS("xml_schema.json") THEN ERROR 1, "SAVE SCHEMA TO after INTO"
PRINT "analyze_fixes: all checks passed"
