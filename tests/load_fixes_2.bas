REM LOAD fixes, part 2: INTO TABLE defaults to APPEND, IGNORE counts, validate and
REM transform rules, XML limit, HTML link resolution, the fields= warning, and the
REM normalizer (validation, scalar arrays, table counts). Failed checks raise errors.
DATABASE OPEN ":memory:"
CREATE TABLE other (x INTEGER);

REM INTO TABLE without a mode appends; IGNORE reports the rows actually inserted
CREATE TABLE k (id TEXT PRIMARY KEY, Name TEXT, "when" TEXT);
LOAD CSV "data/keys.csv" INTO TABLE k OPTIONS "header=true"
LOAD CSV "data/keys.csv" INTO TABLE k IGNORE OPTIONS "header=true"
REM EXPECT: 0 records loaded into table k (2 ignored)
IF (SELECT COUNT(*) FROM k) <> 2 THEN ERROR 1, "INTO TABLE default mode"

REM validate= column names are case-insensitive
LOAD CSV "data/keys.csv" CREATE TABLE v OPTIONS "header=true, validate=name:REQUIRED"
IF (SELECT COUNT(*) FROM v) <> 1 THEN ERROR 1, "validate column case"

REM transform= rules split at the first colon, and rule names ignore case
LOAD CSV "data/keys.csv" CREATE TABLE t OPTIONS "header=true, transform=when:date(YYYY-MM-DD HH:MI,DD/MM/YYYY HH:MI);name:UPPER"
IF (SELECT "when" FROM t WHERE id = '1') <> "02/01/2024 10:30" THEN ERROR 1, "transform date mask with colon"
IF (SELECT Name FROM t WHERE id = '1') <> "ANN" THEN ERROR 1, "transform rule name case"

REM XML limit stops reading: the file is broken after the third record
LOAD XML "data/truncated.xml" CREATE TABLE x OPTIONS "record_tag=r, limit=2"
IF (SELECT COUNT(*) FROM x) <> 2 THEN ERROR 1, "XML limit"

REM HTML links and images resolve against source_url
LOAD HTML "data/links.html" CREATE TABLE lk OPTIONS "element_type=links, source_url=https://example.com/dir/page.html"
IF (SELECT href FROM lk WHERE text = 'B') <> "https://example.com/dir/a/b.html" THEN ERROR 1, "LINKS relative href"
IF (SELECT href FROM lk WHERE text = 'Top') <> "https://example.com/top.html" THEN ERROR 1, "LINKS rooted href"

REM fields= is ignored by LOAD JSON, with a warning
LOAD JSON "data/people_tags.json" CREATE TABLE j OPTIONS "fields=id"
REM EXPECT: Warning: the fields option is ignored by LOAD JSON.

REM normalize: the invalid row and its children are skipped, scalar arrays give one row per value,
REM and only the created tables are counted
LOAD JSON "data/people_tags.json" CREATE TABLE person OPTIONS "normalize=true, validate=NAME:REQUIRED"
REM EXPECT: Created 3 tables:
IF (SELECT COUNT(*) FROM person) <> 1 THEN ERROR 1, "normalize validation row"
IF (SELECT COUNT(*) FROM person_items) <> 1 THEN ERROR 1, "normalize validation child rows"
IF (SELECT COUNT(*) FROM person_tags) <> 2 THEN ERROR 1, "scalar array rows"
IF (SELECT COUNT(*) FROM person_tags WHERE tags IS NULL) <> 0 THEN ERROR 1, "scalar array NULL rows"
PRINT "load_fixes_2: all checks passed"
REM EXPECT: load_fixes_2: all checks passed
