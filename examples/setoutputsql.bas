DATABASE ENGINE DUCKDB
CREATE TABLE users (id INTEGER, name TEXT, status TEXT);
INSERT INTO users VALUES (1, 'Alice', 'active');
INSERT INTO users VALUES (2, 'Bob O''Malley', 'inactive');
INSERT INTO users VALUES (3, 'Charlie', NULL);
PRINT "Generating backup.sql..."
SET OUTPUT FORMAT SQL OPTIONS "tablename=USERS,mode=REPLACE"
SELECT * FROM users ORDER BY 1;