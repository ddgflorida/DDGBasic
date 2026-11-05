REM ANALYZE CSV ... SAVE SCHEMA TO writes a schema that UPGRADE CSV can use directly,
REM including its process_by script. Any failed check raises an error (exit 1).
ANALYZE CSV "data/upgrade/a.csv" SAVE SCHEMA TO "upgrade_schema.json"
UPGRADE CSV "data/upgrade/*.csv" USING SCHEMA "upgrade_schema.json" INTO "upgrade_out"
IF ERR <> 0 THEN ERROR 1, "UPGRADE CSV failed: " + ERRMSG$
READ FILE "upgrade_out/b.csv" INTO b$
IF INSTR(b$, "id,name,amount") <> 1 THEN ERROR 1, "b.csv header not upgraded: " + b$
IF INSTR(b$, "2,bob,") = 0 THEN ERROR 1, "b.csv row not upgraded: " + b$

REM Edit the saved schema: add process_by that drops id 2.
READ FILE "upgrade_schema.json" INTO s$
schema = PARSEJSON(s$)
schema.process_by = `IF rec.id = "2" THEN rec.is_valid = 0`
OPEN "upgrade_schema2.json" FOR OUTPUT AS #1
PRINT #1, JSON_SERIALIZE$(schema);
CLOSE #1
UPGRADE CSV "data/upgrade/*.csv" USING SCHEMA "upgrade_schema2.json" INTO "upgrade_out2"
READ FILE "upgrade_out2/b.csv" INTO b2$
IF INSTR(b2$, "bob") THEN ERROR 1, "process_by did not drop the row"
PRINT "upgrade_csv_schema: all checks passed"
