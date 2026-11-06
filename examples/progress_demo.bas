REM Progress demo: a PROGRESS bar while a table is filled, then a pop-up MENU with more
REM items than the screen has rows (it scrolls; PgUp/PgDn move a page), and an ALERT.
REM Pop-ups have drop shadows; SET SHADOW OFF would turn them off.
REM Keys: arrows, PgUp/PgDn, Home/End, Enter, a first letter, Esc.
DATABASE OPEN ":memory:"
CREATE TABLE cities (id INTEGER PRIMARY KEY, name TEXT, people INTEGER);
COLOR 15, 1, 0, 3
CLS
@ 2, 4 SAY "Building the city table..."

CREATE TABLE names (id INTEGER PRIMARY KEY, name TEXT);
INSERT INTO names (name) VALUES ('Austin'), ('Boston'), ('Chicago'), ('Dallas'), ('Denver'), ('Detroit'),
    ('El Paso'), ('Fresno'), ('Houston'), ('Indianapolis'), ('Jacksonville'), ('Kansas City'), ('Las Vegas'),
    ('Long Beach'), ('Los Angeles'), ('Louisville'), ('Memphis'), ('Mesa'), ('Miami'), ('Milwaukee'),
    ('Minneapolis'), ('Nashville'), ('New York'), ('Oakland'), ('Oklahoma City'), ('Omaha'), ('Philadelphia'),
    ('Phoenix'), ('Portland'), ('Raleigh'), ('Sacramento'), ('San Antonio'), ('San Diego'), ('San Francisco'),
    ('San Jose'), ('Seattle'), ('Tucson'), ('Tulsa'), ('Virginia Beach'), ('Washington');
n = 40 * 50
FOR i = 1 TO n
    PROGRESS i, n TITLE "Loading cities"
    k = MOD(i - 1, 40) + 1
    INSERT INTO cities (name, people) SELECT name, :i FROM names WHERE id = :k;
NEXT i
PROGRESS OFF
@ 2, 4 SAY "Loaded " & TRIM$(STR$((SELECT COUNT(*) FROM cities))) & " rows.          "

REM A menu of the 40 cities: it is taller than the screen, so it scrolls
DIM choices$(39)
k = 0
FOR c IN (SELECT name, SUM(people) AS total FROM cities GROUP BY name ORDER BY name)
    choices$(k) = c.name
    k = k + 1
NEXT
choice = MENU(4, 10, choices$)
IF choice > 0 THEN
    pick$ = choices$(choice - 1)
    x = ALERT(pick$ & ";" & TRIM$(STR$((SELECT COUNT(*) FROM cities WHERE name = :pick$))) & " rows", "OK")
END IF

COLOR 7, 0
CLS
IF choice > 0 THEN PRINT "You chose "; pick$ ELSE PRINT "No city chosen."
REM EXPECT: You chose Washington
