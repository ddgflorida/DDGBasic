# DbBasic Function Reference

This reference lists all major built-in functions available in DbBasic, grouped by category and with usage examples. Replace variables as needed for your own programs.

---

## 🗂️ FILE & DIRECTORY FUNCTIONS

| Function | Description | Example |
|----------|-------------|---------|
| `CURDIR$()` | Returns the current working directory as a string. | `PRINT CURDIR$` |
| `DISKSPACE(path$)` | Returns the number of free bytes on the disk containing the path. | `PRINT DISKSPACE("C:\\")` |
| `EOF(file_num)` | Returns -1 if at end of file, else 0. | `IF EOF(1) THEN PRINT "End of file"` |
| `FILE_EXISTS(path$)` | Returns -1 if file/dir exists, else 0. | `IF FILE_EXISTS("data.txt") THEN PRINT "Found!"` |
| `FILEATTR(path$)` | Returns file attributes as a number. | `PRINT FILEATTR("data.txt")` |
| `FILESIZE(path$)` | Returns file size in bytes, or -1 if missing. | `PRINT FILESIZE("data.txt")` |
| `FILETIME(path$)` | Returns last modification as "YYYY-MM-DD HH:MI:SS". | `PRINT FILETIME("data.txt")` |
| `FREEFILE()` | Returns next available file handle. | `num = FREEFILE()` |
| `BASENAME$(path$)` | Returns the filename from a path. | `PRINT BASENAME$("C:\\folder\\file.txt")` |
| `PATHNAME$(path$)` | Returns the directory portion of a path. | `PRINT PATHNAME$("C:\\folder\\file.txt")` |

---

## 📝 STRING FUNCTIONS

| Function | Description | Example |
|----------|-------------|---------|
| `ASC(string$)` | ASCII code of the first character. | `PRINT ASC("A")    ' 65` |
| `CHR$(code)` | Character for ASCII code. | `PRINT CHR$(65)    ' "A"` |
| `FORMATDATE$(date$, mask$)` | Format date using a mask. | `PRINT FORMATDATE$("20240101", "YYYY-MM-DD")` |
| `HEX$(number)` | Hexadecimal string. | `PRINT HEX$(255)   ' "ff"` |
| `INSTR([start,] s$, sub$)` | Position of substring in string. | `PRINT INSTR("hello","e")   ' 2` |
| `LCASE$(string$)` | To lowercase. | `PRINT LCASE$("ABC")` |
| `LEFT$(string$, n)` | Leftmost n characters. | `PRINT LEFT$("hello",3)` |
| `LTRIM$(string$)` | Trim leading whitespace. | `PRINT LTRIM$("  hi")` |
| `MID$(string$, start, [len])` | Substring from position. | `PRINT MID$("hello",2,3)` |
| `OCT$(number)` | Octal string. | `PRINT OCT$(10)` |
| `PADLEFT$(s$, len, pad$)` | Pad left with character. | `PRINT PADLEFT$("A",5,"-")` |
| `PADRIGHT$(s$, len, pad$)` | Pad right with character. | `PRINT PADRIGHT$("A",5,"-")` |
| `PROPER$(string$)` | Title case. | `PRINT PROPER$("hello world")` |
| `REPEAT$(s$, n)` | Repeat string n times. | `PRINT REPEAT$("x",3)` |
| `REPLACE$(src$, old$, new$ [,count] [,ignore_case])` | Replace substrings. | `PRINT REPLACE$("abab","a","X")` |
| `REVERSE$(string$)` | Reverse string. | `PRINT REVERSE$("abc")` |
| `RIGHT$(string$, n)` | Rightmost n characters. | `PRINT RIGHT$("hello",2)` |
| `RTRIM$(string$)` | Trim trailing whitespace. | `PRINT RTRIM$("hi  ")` |
| `SPACE$(n)` | n spaces. | `PRINT "[" + SPACE$(4) + "]"` |
| `SPLIT(s$, delim$, [limit])` | Split string to array. | `arr = SPLIT("a,b,c",",")` |
| `STR$(number)` | Number to string. | `PRINT STR$(3.14)` |
| `TRIM$(string$)` | Trim both ends. | `PRINT TRIM$(" hi ")` |
| `UCASE$(string$)` | To uppercase. | `PRINT UCASE$("abc")` |
| `STARTSWITH(s$, pre$)` | -1 if s$ starts with pre$, else 0. | `IF STARTSWITH("cat","c") THEN ...` |
| `ENDSWITH(s$, suf$)` | -1 if s$ ends with suf$, else 0. | `IF ENDSWITH("cat","t") THEN ...` |
| `CONTAINS(s$, sub$)` | -1 if s$ contains sub$, else 0. | `IF CONTAINS("dog","o") THEN ...` |
| `LEN(value)` | Number of chars in value as string. | `PRINT LEN("abc")` |

---

## 🔢 MATH FUNCTIONS

| Function | Description | Example |
|----------|-------------|---------|
| `ABS(number)` | Absolute value. | `PRINT ABS(-5)` |
| `ATN(number)` | Arctangent (radians). | `PRINT ATN(1)` |
| `ATAN2(y,x)` | Arctangent(y/x). | `PRINT ATAN2(1,1)` |
| `CEIL(number)` | Round up. | `PRINT CEIL(2.1)` |
| `COS(number)` | Cosine (radians). | `PRINT COS(3.14)` |
| `DEGREES(rad)` | Radians to degrees. | `PRINT DEGREES(3.14)` |
| `EXP(number)` | e^number. | `PRINT EXP(2)` |
| `FIX(number)` | Truncate decimal. | `PRINT FIX(2.9)` |
| `FLOOR(number)` | Round down. | `PRINT FLOOR(2.9)` |
| `INT(number)` | Integer part. | `PRINT INT(2.7)` |
| `LOG(number)` | Natural log. | `PRINT LOG(10)` |
| `MAX(a, b, ...)` | Largest value. | `PRINT MAX(1,2,3)` |
| `MIN(a, b, ...)` | Smallest value. | `PRINT MIN(1,2,3)` |
| `MOD(a, b)` | Remainder. | `PRINT MOD(7,3)` |
| `POWER(a,b)` | a to the b power. | `PRINT POWER(2,3)` |
| `RADIANS(deg)` | Degrees to radians. | `PRINT RADIANS(180)` |
| `RND([max])` | Random float (0-1) or int (1-max). | `PRINT RND()` / `PRINT RND(6)` |
| `ROUND(num, [dec])` | Round to decimals. | `PRINT ROUND(3.1415,2)` |
| `SGN(num)` | Sign: 1, 0, or -1. | `PRINT SGN(-10)` |
| `SIN(num)` | Sine (radians). | `PRINT SIN(3.14)` |
| `SQR(num)` | Square root. | `PRINT SQR(9)` |
| `TAN(num)` | Tangent (radians). | `PRINT TAN(0.5)` |
| `VAL(s$)` | String to number. | `PRINT VAL("123.45")` |

---

## 🗃️ ARRAY & HASH FUNCTIONS

| Function | Description | Example |
|----------|-------------|---------|
| `ARRAY(...)` | Create array from args. | `arr = ARRAY(1,2,3)` |
| `ARRAY_JOIN(arr, delim$)` | Join array into string. | `PRINT ARRAY_JOIN(arr, "-")` |
| `ARRAY_SIZE(arr)` | Number of elements. | `PRINT ARRAY_SIZE(arr)` |
| `FIND(arr, value)` | Index of value, or -1. | `PRINT FIND(arr, "b")` |
| `UBOUND(arr)` | Highest index, or -1. | `PRINT UBOUND(arr)` |
| `HASH_COUNT(hash)` | Number of keys in hash. | `PRINT HASH_COUNT(h)` |
| `HASH_DELETE(hash, key$)` | Remove key from hash. | `HASH_DELETE(h, "city")` |
| `HASH_EXISTS(hash, key$)` | -1 if key exists, 0 if not. | `IF HASH_EXISTS(h,"name") THEN ...` |
| `HASH_JOIN(h1, h2, ...)` | Merge hashes (later wins). | `newh = HASH_JOIN(h1, h2)` |
| `HASH_KEYS(hash)` | Array of keys. | `keys = HASH_KEYS(h)` |
| `HASH_RENAME(hash, old$, new$)` | Rename hash key. | `HASH_RENAME(h,"old","new")` |
| `HASH_VALUES(hash)` | Array of values. | `vals = HASH_VALUES(h)` |
| `IS_ARRAY(var)` | -1 if ARRAY, 0 if not. | `IF IS_ARRAY(arr) THEN ...` |
| `IS_HASH(var)` | -1 if HASH, 0 if not. | `IF IS_HASH(h) THEN ...` |

---

## 📅 DATE & TIME FUNCTIONS

| Function | Description | Example |
|----------|-------------|---------|
| `DATE$()` | Current date as "YYYY-MM-DD". | `PRINT DATE$()` |
| `DATEADD(date$, days)` | Add days to date. | `PRINT DATEADD("2025-01-01",7)` |
| `DATEDIFF(date1$, date2$)` | Days between dates. | `PRINT DATEDIFF("2025-01-10","2025-01-01")` |
| `DAY(date$)` | Day of month. | `PRINT DAY("2025-09-24")` |
| `MONTH(date$)` | Month number. | `PRINT MONTH("2025-09-24")` |
| `YEAR(date$)` | Year number. | `PRINT YEAR("2025-09-24")` |
| `TIME$()` | Current time as "HH:MI:SS". | `PRINT TIME$()` |
| `WEEKDAY(date$)` | Day of week (1=Sun, 7=Sat). | `PRINT WEEKDAY("2025-09-24")` |
| `FORMATDATE$(date$,mask$)` | Format date string. | `PRINT FORMATDATE$("20250924","YYYY-MM-DD")` |

---

## 🔗 URL FUNCTIONS

| Function | Description | Example |
|----------|-------------|---------|
| `URL_FILENAME$(url$)` | Returns filename from URL. | `PRINT URL_FILENAME$("https://site.com/files/a.txt")` |
| `URL_PATH$(url$)` | Returns directory from URL. | `PRINT URL_PATH$("https://site.com/files/a.txt")` |
| `URL_HOSTNAME$(url$)` | Returns hostname. | `PRINT URL_HOSTNAME$("https://site.com/files/a.txt")` |
| `URL_SCHEME$(url$)` | Returns scheme (http, https, etc). | `PRINT URL_SCHEME$("https://site.com/files/a.txt")` |

---

## 🛈 INFORMATION & TYPE FUNCTIONS

| Function | Description | Example |
|----------|-------------|---------|
| `COMMAND$(i)` | Returns command-line arg at index. | `PRINT COMMAND$(1)` |
| `ENVIRON$(name$)` | Gets value of environment variable. | `PRINT ENVIRON$("HOME")` |

---

## 🧱 JSON FUNCTIONS

| Function | Description | Example |
|----------|-------------|---------|
| `JSON_SERIALIZE$(hash_or_array, [indent], [options...])` | Converts a hash or array to JSON string with options for indent, sort, case. | `PRINT JSON_SERIALIZE$(h, 2)` |

---

**Note:**  
- All functions can be used in assignments or expressions.  
- Arrays/hashes are returned as native types, not strings.  
- Return values: `-1` for true, `0` for false in boolean contexts.

---
