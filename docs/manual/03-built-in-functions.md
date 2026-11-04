# Chapter 3: Built-in Functions

This chapter is the complete reference for the functions built into the DbBasic interpreter. It covers every function implemented in `Interpreter._execute_function` in `src/dbbasic.py`, which is **124 functions**. It also covers the **15 extra SQL functions** that DbBasic registers inside SQLite queries; these are described separately in [Functions available inside SQL (SQLite)](#functions-available-inside-sql-sqlite).

The examples in this chapter were run against the interpreter, and the output shown is what it printed. Output from functions that depend on the clock, the file system or the environment (`DATE$`, `FILETIME`, `CURDIR$` and so on) will differ on your machine.

Related chapters:

- Chapter 1, Language Fundamentals: data types, variables, arrays, hashes and operators.
- Chapter 2, Control Flow & Procedures: user-defined `FUNCTION`s and `SORT ... WITH`.
- Chapter 4, Database, SQL & Output: SQL statements and `PRINT USING`, which uses the same mask engine as `FORMAT$`.
- Chapter 6, Files, System, Network & UI: `OPEN`, `LINE INPUT`, `CLOSE` and other statements that work with the file functions.

---

## Contents

- [3.1 How function calls work](#31-how-function-calls-work)
- [3.2 Alphabetical index](#32-alphabetical-index)
- [3.3 String functions](#33-string-functions)
- [3.4 Numeric and math functions](#34-numeric-and-math-functions)
- [3.5 Date and time functions](#35-date-and-time-functions)
- [3.6 Array and hash functions](#36-array-and-hash-functions)
- [3.7 Higher-order functions (FILTER, MAP, REDUCE)](#37-higher-order-functions-filter-map-reduce)
- [3.8 JSON functions](#38-json-functions)
- [3.9 URL and HTML encoding functions](#39-url-and-html-encoding-functions)
- [3.10 File and directory functions](#310-file-and-directory-functions)
- [3.11 System and information functions](#311-system-and-information-functions)
- [3.12 Type and utility functions](#312-type-and-utility-functions)
- [3.13 FORMAT$ mask syntax](#313-format-mask-syntax)
- [3.14 FORMATDATE$ mask tokens](#314-formatdate-mask-tokens)
- [3.15 Functions available inside SQL (SQLite)](#functions-available-inside-sql-sqlite)
- [3.16 Implementation notes and discrepancies](#316-implementation-notes-and-discrepancies)

---

## 3.1 How function calls work

**Names and case.** Function names are not case-sensitive: `left$("abc", 2)` and `LEFT$("abc", 2)` are the same call. By convention, a name that ends in `$` returns a string. Functions without `$` return a number, an array, a hash, or (for a few, such as `FILETIME` and `NOW`) a string.

**Parentheses.** A function call needs parentheses, even when it has no arguments: `NOW()`. There are five exceptions. `DATE$`, `TIME$`, `FREEFILE`, `RND` and `CURDIR$` can be written with or without `()`. If you write any other function name without parentheses, such as `PRINT NOW`, DbBasic reads it as a variable and prints `0`.

**How a call is recognised.** The expression parser (`_parse_factor`) handles a call like this:

1. If the name belongs to a user-defined `FUNCTION` and is followed by `(`, the user function is called. **User-defined functions therefore take precedence over built-ins that have the same name.**
2. Otherwise, the name is looked up as a variable. If it is followed by `(` and the variable does not hold an array or a hash, the call goes to the built-in function dispatcher. If a variable with that name holds an array or hash, `name(x)` is treated as an index or key lookup instead of a function call.
3. An unknown name produces `Runtime Error: Unknown function: NAME`.

`ARRAY` is a reserved keyword, and the parser recognises `ARRAY(...)` as a special case.

**Boolean results.** Predicate functions return **-1 for true and 0 for false**, following BASIC convention. When a test such as `IF CONTAINS(a$, "x") THEN` is evaluated, any non-zero value counts as true.

**Numbers are floating point.** Every numeric result is a Python `float`. `PRINT` shows whole-number floats without the decimal part, but some functions convert numbers to text with Python's `str()` and so show the `.0`. These are `LEN`, `ARRAY_JOIN`, string-criteria `FILTER`, and any string function that is given a number. For example, `LEN(10)` is `4` because the text is `"10.0"`. If you need integer text, convert first with `STR$` and `TRIM$`, or with `FORMAT$`.

**Indexing.** String positions are **1-based**. This applies to `MID$`, `INSTR`, `INSTRREV` and `EXTRACT$`. Array indexes are **0-based**. This applies to `a(0)`, `FIND` and `UBOUND`.

**Argument checking.** Many functions check how many arguments they receive and stop with a clear message, for example `REPEAT$ requires 2 arguments.` Some of the simplest ones (`LEFT$`, `RIGHT$`, `MID$`, `UCASE$`, `LCASE$`, `HEX$`, `OCT$`, `SPACE$`, `STR$`, `VAL`, `INT`, `FIX`, the trigonometric functions, `EXP`, `LOG`, `SGN`, `SQR` and the date-part functions) do not check. If you leave out an argument, those functions fail with a raw Python error such as `list index out of range`. The math functions do not convert strings to numbers, so pass strings through `VAL` first. Math domain errors, such as `SQR(-1)` or `LOG(0)`, stop the program with `Runtime Error: math domain error`.

**Function references.** `FILTER`, `MAP`, `REDUCE` and `SORT ... WITH` accept a bare function name (no parentheses) as an argument. The name can be a user-defined function or any built-in listed in this chapter. See [3.7](#37-higher-order-functions-filter-map-reduce).

---

## 3.2 Alphabetical index

| Function | Category | Returns | Summary |
|---|---|---|---|
| [`ABS`](#fn-abs) | Math | Number | Absolute value |
| [`ARRAY`](#fn-array) | Array | Array | Build an array from its arguments |
| [`ARRAY_JOIN`](#fn-array_join) | Array | String | Join array elements with a delimiter |
| [`ARRAY_SIZE`](#fn-array_size) | Array | Number | Number of elements |
| [`ASC`](#fn-asc) | String | Number | Character code of the first character |
| [`ATAN2`](#fn-atan2) | Math | Number | Arctangent of y/x, quadrant-aware |
| [`ATN`](#fn-atn) | Math | Number | Arctangent |
| [`BASENAME$`](#fn-basename-str) | File | String | File-name part of a path |
| [`CARDINAL$`](#fn-cardinal-str) | String | String | Number in English words |
| [`CEIL`](#fn-ceil) | Math | Number | Round up |
| [`CENTER$`](#fn-center-str) | String | String | Centre text in a field |
| [`CHR$`](#fn-chr-str) | String | String | Character for a code point |
| [`COMMAND$`](#fn-command-str) | System | String | Command-line argument |
| [`CONTAINS`](#fn-contains) | String | Boolean | Substring test |
| [`COS`](#fn-cos) | Math | Number | Cosine |
| [`CURDIR$`](#fn-curdir-str) | File | String | Current working directory |
| [`DATE$`](#fn-date-str) | Date | String | Today as `YYYY-MM-DD` |
| [`DATEADD`](#fn-dateadd) | Date | String | Add days to a date |
| [`DATEDIFF`](#fn-datediff) | Date | Number | Days between two dates |
| [`DATESERIAL`](#fn-dateserial) | Date | String | Build a date from Y, M, D |
| [`DAY`](#fn-day) | Date | Number | Day of month |
| [`DAYSINMONTH`](#fn-daysinmonth) | Date | Number | Days in a month |
| [`DAYSINYEAR`](#fn-daysinyear) | Date | Number | 365 or 366 |
| [`DEGREES`](#fn-degrees) | Math | Number | Radians to degrees |
| [`DISKSPACE`](#fn-diskspace) | File | Number | Free bytes on a volume |
| [`ENDSWITH`](#fn-endswith) | String | Boolean | Suffix test |
| [`ENVIRON$`](#fn-environ-str) | System | String | Environment variable |
| [`EOF`](#fn-eof) | File | Boolean | End-of-file test on a handle |
| [`EXP`](#fn-exp) | Math | Number | e to the power x |
| [`EXTRACT$`](#fn-extract-str) | String | String | Nth field of a delimited string |
| [`FILE_EXISTS`](#fn-file_exists) | File | Boolean | Path exists |
| [`FILEATTR`](#fn-fileattr) | File | Number | Attribute bit mask |
| [`FILESIZE`](#fn-filesize) | File | Number | Size in bytes |
| [`FILETIME`](#fn-filetime) | File | String | Modification time |
| [`FILTER`](#fn-filter) | Higher-order | Array | Keep elements that match |
| [`FIND`](#fn-find) | Array | Number | 0-based index of a value |
| [`FIX`](#fn-fix) | Math | Number | Truncate toward zero |
| [`FLOOR`](#fn-floor) | Math | Number | Round down |
| [`FORMAT$`](#fn-format-str) | String | String | Format a value with a mask |
| [`FORMATDATE$`](#fn-formatdate-str) | Date | String | Reformat a date string |
| [`FREEFILE`](#fn-freefile) | File | Number | Next free file handle |
| [`HASH_COUNT`](#fn-hash_count) | Hash | Number | Number of keys |
| [`HASH_DELETE`](#fn-hash_delete) | Hash | Number | Remove a key |
| [`HASH_EXISTS`](#fn-hash_exists) | Hash | Boolean | Key test |
| [`HASH_JOIN`](#fn-hash_join) | Hash | Hash | Merge hashes |
| [`HASH_KEYS`](#fn-hash_keys) | Hash | Array | Keys as an array |
| [`HASH_RENAME`](#fn-hash_rename) | Hash | Boolean | Rename a key |
| [`HASH_VALUES`](#fn-hash_values) | Hash | Array | Values as an array |
| [`HEX$`](#fn-hex-str) | String | String | Hexadecimal text |
| [`HOUR`](#fn-hour) | Date | Number | Hour from `HH:MM:SS` |
| [`HTMLDECODE$`](#fn-htmldecode-str) | Encoding | String | Decode HTML entities |
| [`HTMLENCODE$`](#fn-htmlencode-str) | Encoding | String | Escape HTML |
| [`INSTR`](#fn-instr) | String | Number | 1-based position of a substring |
| [`INSTRREV`](#fn-instrrev) | String | Number | Last position of a substring |
| [`INT`](#fn-int) | Math | Number | Floor |
| [`IS_ARRAY`](#fn-is_array) | Type | Boolean | Value is an array |
| [`IS_HASH`](#fn-is_hash) | Type | Boolean | Value is a hash |
| [`ISALNUM`](#fn-isalnum) | String | Boolean | All letters or digits |
| [`ISALPHA`](#fn-isalpha) | String | Boolean | All letters |
| [`ISDATE`](#fn-isdate) | Date | Boolean | Parses as a date |
| [`ISDIGIT`](#fn-isdigit) | String | Boolean | All digits |
| [`ISLEAP`](#fn-isleap) | Date | Boolean | Leap year test |
| [`ISNUMERIC`](#fn-isnumeric) | String | Boolean | Parses as a number |
| [`JSON_SERIALIZE$`](#fn-json_serialize-str) | JSON | String | Hash or array to JSON |
| [`LCASE$`](#fn-lcase-str) | String | String | Lower case |
| [`LEFT$`](#fn-left-str) | String | String | Leftmost characters |
| [`LEN`](#fn-len) | String | Number | Length of the text form |
| [`LOG`](#fn-log) | Math | Number | Natural logarithm |
| [`LTRIM$`](#fn-ltrim-str) | String | String | Trim the left side |
| [`MAP`](#fn-map) | Higher-order | Array | Transform every element |
| [`MAX`](#fn-max) | Math | Number | Largest argument |
| [`MID$`](#fn-mid-str) | String | String | Substring |
| [`MIN`](#fn-min) | Math | Number | Smallest argument |
| [`MINUTE`](#fn-minute) | Date | Number | Minute from a time string |
| [`MOD`](#fn-mod) | Math | Number | Remainder |
| [`MONTH`](#fn-month) | Date | Number | Month number |
| [`MONTHCAL$`](#fn-monthcal-str) | Date | String | Text calendar for a month |
| [`MONTHNAME$`](#fn-monthname-str) | Date | String | Month name |
| [`NOW`](#fn-now) | Date | String | Current date and time |
| [`NVL`](#fn-nvl) | Utility | Any | First non-empty argument |
| [`OCT$`](#fn-oct-str) | String | String | Octal text |
| [`ORDINAL$`](#fn-ordinal-str) | String | String | Ordinal in English words |
| [`PADLEFT$`](#fn-padleft-str) | String | String | Left-pad to a width |
| [`PADRIGHT$`](#fn-padright-str) | String | String | Right-pad to a width |
| [`PARSEJSON`](#fn-parsejson) | JSON | Hash or Array | Parse JSON text |
| [`PATHNAME$`](#fn-pathname-str) | File | String | Directory part of a path |
| [`POWER`](#fn-power) | Math | Number | x to the power y |
| [`PROPER$`](#fn-proper-str) | String | String | Title Case |
| [`RADIANS`](#fn-radians) | Math | Number | Degrees to radians |
| [`REDUCE`](#fn-reduce) | Higher-order | Any | Fold an array |
| [`REPEAT$`](#fn-repeat-str) | String | String | Repeat a string |
| [`REPLACE$`](#fn-replace-str) | String | String | Replace substrings |
| [`REVERSE$`](#fn-reverse-str) | String | String | Reverse a string |
| [`RIGHT$`](#fn-right-str) | String | String | Rightmost characters |
| [`RND`](#fn-rnd) | Math | Number | Random number |
| [`ROUND`](#fn-round) | Math | Number | Round to decimals |
| [`RTRIM$`](#fn-rtrim-str) | String | String | Trim the right side |
| [`SECOND`](#fn-second) | Date | Number | Second from a time string |
| [`SGN`](#fn-sgn) | Math | Number | Sign |
| [`SIN`](#fn-sin) | Math | Number | Sine |
| [`SOUNDEX$`](#fn-soundex-str) | String | String | Soundex code |
| [`SPACE$`](#fn-space-str) | String | String | A run of spaces |
| [`SPLIT`](#fn-split) | String / Array | Array | Split into an array |
| [`SQR`](#fn-sqr) | Math | Number | Square root |
| [`STARTSWITH`](#fn-startswith) | String | Boolean | Prefix test |
| [`STR$`](#fn-str-str) | String | String | Number to text, in PRINT style |
| [`STRIPHTML$`](#fn-striphtml-str) | Encoding | String | Remove HTML tags |
| [`TAN`](#fn-tan) | Math | Number | Tangent |
| [`TIME$`](#fn-time-str) | Date | String | Time as `HH:MM:SS` |
| [`TRIM$`](#fn-trim-str) | String | String | Trim both sides |
| [`TYPENAME$`](#fn-typename-str) | Type | String | Type name of a value |
| [`UBOUND`](#fn-ubound) | Array | Number | Highest index |
| [`UCASE$`](#fn-ucase-str) | String | String | Upper case |
| [`URL_FILENAME$`](#fn-url_filename-str) | Encoding / URL | String | File name in a URL |
| [`URL_HOSTNAME$`](#fn-url_hostname-str) | Encoding / URL | String | Host name in a URL |
| [`URL_PATH$`](#fn-url_path-str) | Encoding / URL | String | Directory part of a URL path |
| [`URL_SCHEME$`](#fn-url_scheme-str) | Encoding / URL | String | Scheme of a URL |
| [`URLDECODE$`](#fn-urldecode-str) | Encoding | String | Decode `%xx` and `+` |
| [`URLENCODE$`](#fn-urlencode-str) | Encoding | String | Percent-encode text |
| [`VAL`](#fn-val) | Math / Type | Number | Text to number |
| [`WEEKDAY`](#fn-weekday) | Date | Number | Day of week (1=Sunday) |
| [`WEEKDAYNAME$`](#fn-weekdayname-str) | Date | String | Weekday name (see the notes) |
| [`YEAR`](#fn-year) | Date | Number | Year |
| [`YEARCAL$`](#fn-yearcal-str) | Date | String | Text calendar for a year |

SQL-side functions (usable only inside SQLite statements): `CHARINDEX`, `ENDS_WITH`, `INITCAP`, `INSTR`, `LEFT$`, `LPAD`, `REPLICATE`, `REVERSE`, `RIGHT$`, `RPAD`, `SOUNDEX`, `SPLIT_PART`, `STARTS_WITH`, `STUFF` and `TRANSLATE`. See [3.15](#functions-available-inside-sql-sqlite).

---

## 3.3 String functions

<a id="fn-left-str"></a>
### LEFT$

`LEFT$(s$, n)` returns a **String**.

Returns the first `n` characters of `s$`. If `n` is larger than the length of the string, the whole string is returned. A negative `n` drops characters from the end (Python slice behaviour): `LEFT$("abc", -1)` is `"ab"`. A number passed as `s$` is first converted to text in float form (`"10.0"`). The function does not check its arguments.

```basic
PRINT "[" + LEFT$("Hello World", 5) + "]"
PRINT "[" + LEFT$("Hi", 10) + "]"
```
```
[Hello]
[Hi]
```

<a id="fn-right-str"></a>
### RIGHT$

`RIGHT$(s$, n)` returns a **String**.

Returns the last `n` characters of `s$`. **Edge case:** `RIGHT$(s$, 0)` returns the *whole* string rather than an empty string, because it is implemented as `s[-0:]`. The SQL version of `RIGHT$` returns `""` for 0.

```basic
PRINT "[" + RIGHT$("Hello World", 5) + "]"
PRINT "[" + RIGHT$("Hello", 0) + "]"
```
```
[World]
[Hello]
```

<a id="fn-mid-str"></a>
### MID$

`MID$(s$, start [, length])` returns a **String**.

Returns a substring that begins at the 1-based position `start`. If you leave out `length`, the rest of the string is returned. If `start` is past the end of the string, the result is `""`. A `start` of 0 or less gives unexpected results (`MID$("Hello", 0, 2)` returns `""`), so always use positions from 1.

```basic
PRINT "[" + MID$("Hello World", 7) + "]"
PRINT "[" + MID$("Hello World", 7, 3) + "]"
PRINT "[" + MID$("abc", 5, 2) + "]"
```
```
[World]
[Wor]
[]
```

<a id="fn-ucase-str"></a>
### UCASE$

`UCASE$(s$)` returns a **String**: `s$` converted to upper case.

<a id="fn-lcase-str"></a>
### LCASE$

`LCASE$(s$)` returns a **String**: `s$` converted to lower case.

```basic
PRINT "[" + UCASE$("MiXed") + "]"
PRINT "[" + LCASE$("MiXed") + "]"
```
```
[MIXED]
[mixed]
```

<a id="fn-proper-str"></a>
### PROPER$

`PROPER$(s$)` returns a **String**.

Converts `s$` to title case with Python's `str.title()`. The first letter of each word is upper-cased and the remaining letters are lower-cased. Any character that is not a letter starts a new word, so `o'neil` becomes `O'Neil`.

```basic
PRINT "[" + PROPER$("hello wORLD o'neil") + "]"
```
```
[Hello World O'Neil]
```

<a id="fn-cardinal-str"></a>
### CARDINAL$

`CARDINAL$(number)` returns a **String**: the number in English words. Negative numbers start with `negative`. Digits after the decimal point are spelled one at a time after `point`. Numbers up to the quintillions are supported. A non-numeric argument gives `CARDINAL$ requires a number`.

<a id="fn-ordinal-str"></a>
### ORDINAL$

`ORDINAL$(number)` returns a **String**: the ordinal form of a whole number in English words (`first`, `twenty-first`, `one hundredth`). A number with a fractional part gives `ORDINAL$ requires a whole number`.

```basic
PRINT CARDINAL$(1234)
PRINT CARDINAL$(-5); " | "; CARDINAL$(3.14); " | "; CARDINAL$(1000000)
PRINT ORDINAL$(1); " "; ORDINAL$(12); " "; ORDINAL$(21); " "; ORDINAL$(40); " "; ORDINAL$(100); " "; ORDINAL$(1001)
```
```
one thousand two hundred thirty-four
negative five | three point one four | one million
first twelfth twenty-first fortieth one hundredth one thousand first
```

<a id="fn-center-str"></a>
### CENTER$

`CENTER$(s$, width [, pad$])` returns a **String**.

Centres `s$` in a field `width` characters wide. `pad$` sets the fill character (default: a space) and must be exactly one character, otherwise you get an error. If the padding cannot be split evenly, the extra character goes on the **left**. If `width` is less than or equal to the length of `s$`, the string is returned unchanged and is not truncated.

```basic
PRINT "[" + CENTER$("Hi", 8) + "]"
PRINT "[" + CENTER$("Hi", 9, "*") + "]"
PRINT "[" + CENTER$("abc", 2) + "]"
```
```
[   Hi   ]
[****Hi***]
[abc]
```

<a id="fn-padleft-str"></a>
### PADLEFT$

`PADLEFT$(s$, length, pad$)` returns a **String**.

Right-justifies `s$` in a field `length` characters wide by adding copies of `pad$` on the left. All three arguments are required. Only the first character of `pad$` is used; if `pad$` is empty, a space is used. If `s$` is already longer than `length`, it is returned unchanged and is not truncated.

<a id="fn-padright-str"></a>
### PADRIGHT$

`PADRIGHT$(s$, length, pad$)` returns a **String**. It works like `PADLEFT$` but adds the padding on the right.

```basic
PRINT "[" + PADLEFT$("42", 6, "0") + "]"
PRINT "[" + PADRIGHT$("ab", 5, ".") + "]"
PRINT "[" + PADLEFT$("toolong", 3, "0") + "]"
```
```
[000042]
[ab...]
[toolong]
```

<a id="fn-trim-str"></a>
### TRIM$

`TRIM$(s$ [, chars$])` returns a **String**.

Removes whitespace from both ends of `s$`. If you supply `chars$`, any of the characters in `chars$` are removed from both ends instead. `chars$` is a *set* of characters, not a substring.

<a id="fn-ltrim-str"></a>
### LTRIM$

`LTRIM$(s$ [, chars$])` returns a **String**. It works like `TRIM$` but trims only the left side.

<a id="fn-rtrim-str"></a>
### RTRIM$

`RTRIM$(s$ [, chars$])` returns a **String**. It works like `TRIM$` but trims only the right side.

```basic
PRINT "[" + TRIM$("  hi  ") + "]"
PRINT "[" + TRIM$("xxhixx", "x") + "]"
PRINT "[" + LTRIM$("  hi  ") + "]"
PRINT "[" + LTRIM$("000123", "0") + "]"
PRINT "[" + RTRIM$("  hi  ") + "]"
PRINT "[" + RTRIM$("hi!!!", "!") + "]"
```
```
[hi]
[hi]
[hi  ]
[123]
[  hi]
[hi]
```

<a id="fn-len"></a>
### LEN

`LEN(value)` returns a **Number**.

Returns the number of characters in the text form of `value`. Numbers are converted with Python `str()`, so `LEN(10)` is 4 (`"10.0"`). An array is measured by its Python text form, so `LEN(ARRAY(1, 2))` is 10. Use `ARRAY_SIZE` to count array elements.

```basic
PRINT LEN("Hello")
PRINT LEN(12.5)
PRINT LEN(10)
```
```
 5
 4
 4
```

<a id="fn-instr"></a>
### INSTR

`INSTR(haystack$, needle$)` or `INSTR(start, haystack$, needle$)` returns a **Number**.

Returns the 1-based position of the first occurrence of `needle$` in `haystack$`, or 0 if it is not found. In the three-argument form the **start position comes first**, as in classic BASIC, and the search begins at that 1-based position. A start of 0 or less is treated as 1. The search is case-sensitive.

> The SQL version of `INSTR` takes the start position as the *third* argument. See [3.15](#functions-available-inside-sql-sqlite).

```basic
PRINT INSTR("hello world", "o")
PRINT INSTR(6, "hello world", "o")
PRINT INSTR("hello", "z")
```
```
 5
 8
 0
```

<a id="fn-instrrev"></a>
### INSTRREV

`INSTRREV(haystack$, needle$ [, start])` returns a **Number**.

Returns the 1-based position of the **last** occurrence of `needle$`, or 0 if it is not found. If you supply `start`, only the first `start` characters of `haystack$` are searched, so the match must end at or before position `start`. Note that `start` is the *third* argument here.

```basic
PRINT INSTRREV("hello world", "o")
PRINT INSTRREV("hello world", "o", 7)
PRINT INSTRREV("a/b/c", "/")
PRINT INSTRREV("hello", "z")
```
```
 8
 5
 4
 0
```

<a id="fn-startswith"></a>
### STARTSWITH

`STARTSWITH(s$, prefix$)` returns a **Boolean** (-1 or 0). Case-sensitive.

<a id="fn-endswith"></a>
### ENDSWITH

`ENDSWITH(s$, suffix$)` returns a **Boolean** (-1 or 0). Case-sensitive.

<a id="fn-contains"></a>
### CONTAINS

`CONTAINS(s$, substring$)` returns a **Boolean** (-1 or 0). Case-sensitive.

```basic
PRINT STARTSWITH("filename.txt", "file")
PRINT ENDSWITH("filename.txt", ".csv")
PRINT CONTAINS("filename.txt", "name")
```
```
-1
 0
-1
```

<a id="fn-extract-str"></a>
### EXTRACT$

`EXTRACT$(s$, position [, delimiter$])` returns a **String**.

Splits `s$` on `delimiter$` (default: a comma) and returns field number `position`, counting from 1. If `position` is 0, negative or past the last field, the result is `""`. Empty fields are kept.

```basic
PRINT "[" + EXTRACT$("a,b,c", 2) + "]"
PRINT "[" + EXTRACT$("a;b;c", 3, ";") + "]"
PRINT "[" + EXTRACT$("a,b,c", 9) + "]"
```
```
[b]
[c]
[]
```

<a id="fn-split"></a>
### SPLIT

`SPLIT(s$, delimiter$ [, limit])` returns an **Array** of strings.

Splits `s$` on `delimiter$`. Empty fields are kept. If `delimiter$` is `""`, the string is split into single characters. `limit` sets the *maximum number of elements*: the last element holds the rest of the string. `limit` must be greater than 0, otherwise you get `Runtime Error: Limit must be > 0`.

```basic
s = SPLIT("a,b,,c", ",")
PRINT ARRAY_SIZE(s); "[" + s(2) + "]"
s2 = SPLIT("k=v=w", "=", 2)
PRINT ARRAY_SIZE(s2); "[" + s2(1) + "]"
s3 = SPLIT("abc", "")
PRINT ARRAY_SIZE(s3); s3(1)
```
```
 4[]
 2[v=w]
 3b
```

<a id="fn-replace-str"></a>
### REPLACE$

`REPLACE$(s$, old$, new$ [, count [, ignore_case]])` returns a **String**.

Replaces occurrences of `old$` with `new$`.

- `count` sets the maximum number of replacements. Use -1 (the default) for all of them. `count` = 0 makes no replacements.
- If `ignore_case` is non-zero, matching ignores case. To use `ignore_case`, you must also pass `count`; use -1 for "all".

```basic
PRINT "[" + REPLACE$("a-b-c-d", "-", "+") + "]"
PRINT "[" + REPLACE$("a-b-c-d", "-", "+", 2) + "]"
PRINT "[" + REPLACE$("Cat cat CAT", "cat", "dog", -1, 1) + "]"
PRINT "[" + REPLACE$("Cat cat CAT", "cat", "dog", 1, 1) + "]"
```
```
[a+b+c+d]
[a+b+c-d]
[dog dog dog]
[dog cat CAT]
```

<a id="fn-reverse-str"></a>
### REVERSE$

`REVERSE$(s$)` returns a **String** with the characters of `s$` in reverse order.

<a id="fn-repeat-str"></a>
### REPEAT$

`REPEAT$(s$, count)` returns a **String**: `s$` repeated `count` times. A `count` of 0 or less returns `""`.

<a id="fn-space-str"></a>
### SPACE$

`SPACE$(n)` returns a **String** of `n` spaces.

```basic
PRINT "[" + REVERSE$("abc") + "]"
PRINT "[" + REPEAT$("ab", 3) + "]"
PRINT "[" + SPACE$(3) + "]"
```
```
[cba]
[ababab]
[   ]
```

<a id="fn-chr-str"></a>
### CHR$

`CHR$(code)` returns a **String**: the character for Unicode code point `code`. Values above 127 are allowed; `CHR$(9731)` is `☃`.

<a id="fn-asc"></a>
### ASC

`ASC(s$)` returns a **Number**: the code point of the first character of `s$`. The argument must be a non-empty string, otherwise you get `ASC requires one non-empty string argument.`

```basic
PRINT "[" + CHR$(65) + "]"
PRINT ASC("ABC")
```
```
[A]
 65
```

<a id="fn-hex-str"></a>
### HEX$

`HEX$(n)` returns a **String**: `INT(n)` written in lower-case hexadecimal, without a prefix. **Edge case:** negative numbers come out wrong. `HEX$(-255)` returns `"xff"` because Python's `-0xff` is cut after two characters.

<a id="fn-oct-str"></a>
### OCT$

`OCT$(n)` returns a **String**: `n` written in octal, without a prefix. It has the same problem with negative numbers as `HEX$`.

```basic
PRINT "[" + HEX$(255) + "]"
PRINT "[" + OCT$(8) + "]"
PRINT "[" + HEX$(-255) + "]"
```
```
[ff]
[10]
[xff]
```

<a id="fn-str-str"></a>
### STR$

`STR$(value)` returns a **String**.

Converts a number to text the same way `PRINT` shows it. Whole numbers have no decimal part, and **zero and positive numbers get a leading space**, which is reserved for the sign. Negative numbers start with `-`. Floating-point noise is not rounded away. A string argument is returned unchanged.

```basic
PRINT "[" + STR$(42) + "]"
PRINT "[" + STR$(-42) + "]"
PRINT "[" + STR$(3.5) + "]"
PRINT "[" + STR$(0.1 + 0.2) + "]"
PRINT "[" + STR$("abc") + "]"
```
```
[ 42]
[-42]
[ 3.5]
[ 0.30000000000000004]
[abc]
```

To get text without the leading space, use `TRIM$(STR$(n))`. For a fixed format, use `FORMAT$`.

<a id="fn-format-str"></a>
### FORMAT$

`FORMAT$(value, mask$)` returns a **String**.

Formats a single number or string using a `PRINT USING`-style mask. Exactly two arguments are required. The full mask syntax is described in [3.13](#313-format-mask-syntax).

```basic
PRINT "[" + FORMAT$(1234.567, "#,##0.00") + "]"
PRINT "[" + FORMAT$(1234.5, "$#,##0.00") + "]"
PRINT "[" + FORMAT$(42, "00000") + "]"
PRINT "[" + FORMAT$(0.256, "0.00%") + "][" + FORMAT$(42, "### units") + "]"
```
```
[1,234.57]
[$1,234.50]
[00042]
[25.60%][ 42 units]
```

<a id="fn-soundex-str"></a>
### SOUNDEX$

`SOUNDEX$(s$)` returns a **String**.

Returns the four-character Soundex code of `s$`, made of the first letter followed by three digits. It returns an empty value if `s$` is empty or does not start with a letter A-Z. In this implementation, vowels do **not** separate repeated codes, so a few names differ from the standard American Soundex (for example `Tymczak` gives `T520` instead of `T522`). The same code is used by the SQL `SOUNDEX` function.

```basic
PRINT "[" + SOUNDEX$("Robert") + "]"
PRINT "[" + SOUNDEX$("Rupert") + "]"
PRINT "[" + SOUNDEX$("Ashcraft") + "]"
```
```
[R163]
[R163]
[A261]
```

<a id="fn-isalpha"></a>
### ISALPHA

`ISALPHA(s$)` returns a **Boolean**: -1 if `s$` is non-empty and every character is a letter. Unicode letters count.

<a id="fn-isdigit"></a>
### ISDIGIT

`ISDIGIT(s$)` returns a **Boolean**: -1 if `s$` is non-empty and every character is a digit. A sign or a decimal point makes it false.

<a id="fn-isalnum"></a>
### ISALNUM

`ISALNUM(s$)` returns a **Boolean**: -1 if `s$` is non-empty and every character is a letter or a digit.

<a id="fn-isnumeric"></a>
### ISNUMERIC

`ISNUMERIC(value)` returns a **Boolean**.

Returns -1 if `value` can be converted to a number with Python `float()`. Leading and trailing spaces, signs, decimals and exponents (`"-3e2"`) are accepted, and so are the special words `"nan"` and `"inf"`. Thousands separators (`"1,000"`) and the empty string are rejected.

```basic
PRINT ISALPHA("abc"); ISALPHA("ab1"); ISALPHA("")
PRINT ISDIGIT("123"); ISDIGIT("12.3"); ISDIGIT("-1")
PRINT ISALNUM("abc123"); ISALNUM("abc 123")
PRINT ISNUMERIC("12.5"); ISNUMERIC("-3e2"); ISNUMERIC("abc"); ISNUMERIC(""); ISNUMERIC(" 7 ")
PRINT ISNUMERIC("nan"); ISNUMERIC("1,000")
```
```
-1 0 0
-1 0 0
-1 0
-1-1 0 0-1
-1 0
```

---

## 3.4 Numeric and math functions

All of these return a **Number** (a float). Arguments must already be numbers. A string argument causes a Python type error, so use `VAL` to convert first.

<a id="fn-abs"></a>
### ABS

`ABS(x)` returns the absolute value of `x`.

<a id="fn-sgn"></a>
### SGN

`SGN(x)` returns -1, 0 or 1 depending on the sign of `x`.

```basic
PRINT ABS(-7.5)
PRINT SGN(-3); SGN(0); SGN(9)
```
```
 7.5
-1 0 1
```

<a id="fn-int"></a>
### INT

`INT(x)` returns the largest whole number less than or equal to `x` (floor). `INT(-3.7)` is -4.

<a id="fn-fix"></a>
### FIX

`FIX(x)` truncates `x` toward zero. `FIX(-3.7)` is -3.

<a id="fn-floor"></a>
### FLOOR

`FLOOR(x)` rounds down. It is the same as `INT`.

<a id="fn-ceil"></a>
### CEIL

`CEIL(x)` rounds up to the next whole number.

```basic
PRINT INT(3.7); INT(-3.7)
PRINT FIX(3.7); FIX(-3.7)
PRINT FLOOR(-2.5); CEIL(-2.5); CEIL(2.1)
```
```
 3-4
 3-3
-3-2 3
```

<a id="fn-round"></a>
### ROUND

`ROUND(x [, decimals])` rounds `x` to `decimals` decimal places (default 0).

ROUND uses Python's `round()`, which applies **banker's rounding**: an exact .5 rounds to the nearest even number. Binary floating-point representation also affects results; for example, `2.675` is stored as slightly less than 2.675, so it rounds to 2.67. A negative `decimals` rounds to tens, hundreds and so on.

```basic
PRINT ROUND(2.5); ROUND(3.5); ROUND(2.675, 2); ROUND(1234.5678, 2); ROUND(1234.5678, -2)
PRINT ROUND(0.5); ROUND(1.5); ROUND(-2.5)
```
```
 2 4 2.67 1234.57 1200
 0 2-2
```

<a id="fn-mod"></a>
### MOD

`MOD(a, b)` returns the remainder of `a / b`, using Python `%`. The result has the **same sign as the divisor** `b`, so `MOD(-7, 3)` is 2. Fractional values work.

```basic
PRINT MOD(17, 5); MOD(-7, 3); MOD(7.5, 2)
```
```
 2 2 1.5
```

<a id="fn-power"></a>
### POWER

`POWER(x, y)` returns `x` raised to the power `y`. It is equivalent to the `^` operator.

<a id="fn-sqr"></a>
### SQR

`SQR(x)` returns the square root of `x`. A negative `x` causes `Runtime Error: math domain error`.

```basic
PRINT POWER(2, 10); POWER(9, 0.5)
PRINT SQR(16)
```
```
 1024 3
 4
```

<a id="fn-exp"></a>
### EXP

`EXP(x)` returns e raised to the power `x`.

<a id="fn-log"></a>
### LOG

`LOG(x)` returns the **natural** logarithm of `x`. There is no base-10 function; use `LOG(x) / LOG(10)`. An `x` of 0 or less causes a math domain error.

```basic
PRINT EXP(1)
PRINT LOG(100)
PRINT LOG(EXP(2))
```
```
 2.718281828459045
 4.605170185988092
 2
```

<a id="fn-min"></a>
### MIN

`MIN(a, b, ...)` returns the smallest of its arguments.

<a id="fn-max"></a>
### MAX

`MAX(a, b, ...)` returns the largest of its arguments.

Both need **at least two** numeric arguments. Arrays are not accepted, so use `REDUCE(arr, MAX)` instead. Mixing strings and numbers causes an error (`'<' not supported between instances of 'str' and 'float'`).

```basic
PRINT MIN(4, 2, 8); MAX(4, 2, 8)
```
```
 2 8
```

<a id="fn-sin"></a>
### SIN

`SIN(x)` returns the sine of `x`, in radians.

<a id="fn-cos"></a>
### COS

`COS(x)` returns the cosine of `x`, in radians.

<a id="fn-tan"></a>
### TAN

`TAN(x)` returns the tangent of `x`, in radians.

<a id="fn-atn"></a>
### ATN

`ATN(x)` returns the arctangent of `x`, in radians.

<a id="fn-atan2"></a>
### ATAN2

`ATAN2(y, x)` returns the arctangent of `y/x`, in radians, using the signs of both arguments to pick the correct quadrant.

<a id="fn-degrees"></a>
### DEGREES

`DEGREES(radians)` converts radians to degrees.

<a id="fn-radians"></a>
### RADIANS

`RADIANS(degrees)` converts degrees to radians.

There is no `PI` constant. Use `ATN(1) * 4`.

```basic
PRINT ATN(1) * 4
PRINT SIN(0); COS(0); TAN(0)
PRINT DEGREES(3.141592653589793)
PRINT RADIANS(180)
PRINT ATAN2(1, 1)
```
```
 3.141592653589793
 0 1 0
 180
 3.141592653589793
 0.7853981633974483
```

<a id="fn-rnd"></a>
### RND

`RND` or `RND()` returns a random float in the range 0 ≤ x < 1. `RND(n)` returns a random **whole number from 1 to n** inclusive. `RND(n)` requires `n` ≥ 1; `RND(0)` stops with `RND arg must be >= 1`. More than one argument is an error. No statement for seeding the generator is documented.

```basic
r = RND(6)
IF r >= 1 AND r <= 6 AND INT(r) = r THEN PRINT "rnd6 ok"
PRINT RND(1)
```
```
rnd6 ok
 1
```

<a id="fn-val"></a>
### VAL

`VAL(s$)` returns a **Number**.

Converts text to a number with Python `float()`. Surrounding whitespace and exponents are accepted. **Unlike classic BASIC, VAL does not read a leading numeric prefix.** `VAL("12abc")` returns 0. Any text that cannot be converted, including `""`, returns 0 without an error. If `s$` is already a number, it is returned unchanged.

```basic
PRINT VAL("3.14"); VAL("abc"); VAL(""); VAL("12abc"); VAL(" 5 ")
PRINT VAL("1e3")
```
```
 3.14 0 0 0 5
 1000
```

---

## 3.5 Date and time functions

DbBasic stores dates as **strings**. Different functions accept different input formats:

| Accepted input | Functions |
|---|---|
| `YYYY-MM-DD` or `YYYYMMDD` **only** (strict) | `DATEADD`, `DATEDIFF`, `YEAR`, `MONTH`, `DAY`, `WEEKDAY` |
| `YYYY-MM-DD`, `MM/DD/YYYY`, `MM-DD-YYYY`, `YYYY/MM/DD`, `YYYYMMDD` | `ISDATE` |
| The `ISDATE` formats plus `YYYY-MM-DD HH:MM:SS` (auto-detected), or any format given by an input mask | `FORMATDATE$` |
| `HH:MM:SS` text split on `:` | `HOUR`, `MINUTE`, `SECOND` |

If you pass another format, for example `"07/04/2024"`, to one of the strict functions, the program stops with `Runtime Error: Invalid date format: 07/04/2024`. To use such a date, normalise it first: `FORMATDATE$(d$, "YYYY-MM-DD")`.

Functions that return a date always return `YYYY-MM-DD`.

<a id="fn-date-str"></a>
### DATE$

`DATE$` or `DATE$()` returns a **String**: the current local date as `YYYY-MM-DD`.

<a id="fn-time-str"></a>
### TIME$

`TIME$` or `TIME$()` returns a **String**: the current local time as `HH:MM:SS` in 24-hour form.

<a id="fn-now"></a>
### NOW

`NOW()` returns a **String**: the current local date and time as `YYYY-MM-DD HH:MM:SS`. The parentheses are required; plain `NOW` is read as a variable.

```basic
PRINT DATE$
PRINT TIME$
PRINT NOW()
```
```
2026-11-04
14:35:09
2026-11-04 14:35:09
```
(Sample output; the values depend on the clock.)

<a id="fn-dateadd"></a>
### DATEADD

`DATEADD(date$, days)` returns a **String** (`YYYY-MM-DD`).

Adds `days` to `date$`. `days` is converted to a whole number and can be negative. There is no month or year arithmetic.

```basic
PRINT "[" + DATEADD("2024-02-27", 3) + "]"
PRINT "[" + DATEADD("20240301", -1) + "]"
```
```
[2024-03-01]
[2024-02-29]
```

<a id="fn-datediff"></a>
### DATEDIFF

`DATEDIFF(date1$, date2$)` returns a **Number**: `date1$ - date2$` in days. The result is negative when `date1$` is the earlier date. The two arguments can use different strict formats.

```basic
PRINT DATEDIFF("2024-03-01", "2024-02-01")
PRINT DATEDIFF("2024-01-01", "2024-12-25")
PRINT DATEDIFF("2024-12-25", "20240101")
```
```
 29
-359
 359
```

<a id="fn-year"></a>
### YEAR

`YEAR(date$)` returns a **Number**: the year.

<a id="fn-month"></a>
### MONTH

`MONTH(date$)` returns a **Number**: the month, 1 to 12.

<a id="fn-day"></a>
### DAY

`DAY(date$)` returns a **Number**: the day of the month, 1 to 31.

<a id="fn-weekday"></a>
### WEEKDAY

`WEEKDAY(date$)` returns a **Number**: the day of the week, where **1 = Sunday** and 7 = Saturday.

```basic
PRINT YEAR("2024-07-04"); MONTH("2024-07-04"); DAY("2024-07-04")
PRINT YEAR("20240704")
PRINT WEEKDAY("2024-07-04")
PRINT WEEKDAY("2024-07-07")
PRINT WEEKDAY("2024-07-06")
```
```
 2024 7 4
 2024
 5
 1
 7
```
(4 July 2024 was a Thursday, 7 July a Sunday and 6 July a Saturday.)

<a id="fn-hour"></a>
### HOUR

`HOUR(time$)` returns a **Number**.

<a id="fn-minute"></a>
### MINUTE

`MINUTE(time$)` returns a **Number**.

<a id="fn-second"></a>
### SECOND

`SECOND(time$)` returns a **Number**.

These functions take a time (`HH:MM:SS`) or a datetime (`YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DDTHH:MM:SS`). For a datetime they use the time part. They split it on `:` and return the first, second or third part as a number. A missing or non-numeric part gives 0.

```basic
PRINT HOUR("14:35:09"); MINUTE("14:35:09"); SECOND("14:35:09")
PRINT HOUR("2024-07-04 14:35:09")
PRINT MINUTE("2024-07-04T14:35:09")
```
```
 14 35 9
 14
 35
```

<a id="fn-dateserial"></a>
### DATESERIAL

`DATESERIAL(year, month, day)` returns a **String** (`YYYY-MM-DD`). Values outside the valid range, such as month 13 or 30 February, cause `Invalid arguments for DATESERIAL.` They are not rolled over into the next month or year.

```basic
PRINT "[" + DATESERIAL(2024, 7, 4) + "]"
```
```
[2024-07-04]
```

<a id="fn-isdate"></a>
### ISDATE

`ISDATE(s$)` returns a **Boolean**. It returns -1 if `s$` is a valid calendar date in one of these formats: `YYYY-MM-DD`, `MM/DD/YYYY`, `MM-DD-YYYY`, `YYYY/MM/DD` or `YYYYMMDD`. A valid result does not mean the strict date functions will accept the string.

```basic
PRINT ISDATE("2024-07-04"); ISDATE("07/04/2024"); ISDATE("2024-02-30"); ISDATE("July 4")
```
```
-1-1 0 0
```

<a id="fn-isleap"></a>
### ISLEAP

`ISLEAP(year)` returns a **Boolean**: -1 for a Gregorian leap year.

<a id="fn-daysinyear"></a>
### DAYSINYEAR

`DAYSINYEAR(year)` returns a **Number**: 365 or 366.

<a id="fn-daysinmonth"></a>
### DAYSINMONTH

`DAYSINMONTH(month, year)` returns a **Number**. The documented order is month first, but `DAYSINMONTH(year, month)` also works: if the first argument is greater than 12 and the second is 1 to 12, they are swapped. `MONTHCAL$` takes (year, month).

```basic
PRINT DAYSINMONTH(2, 2024); DAYSINMONTH(2, 2023); DAYSINMONTH(2024, 2)
PRINT DAYSINYEAR(2024); DAYSINYEAR(1900)
PRINT ISLEAP(2000); ISLEAP(1900)
```
```
 29 28 29
 366 365
-1 0
```

<a id="fn-monthname-str"></a>
### MONTHNAME$

`MONTHNAME$(month)` returns a **String**: the English month name. `month` must be 1 to 12, otherwise you get `Month number must be between 1 and 12.`

<a id="fn-weekdayname-str"></a>
### WEEKDAYNAME$

`WEEKDAYNAME$(n)` returns a **String**: an English weekday name. `n` must be 1 to 7.

The numbering matches `WEEKDAY`: **1 = Sunday, 2 = Monday, ..., 7 = Saturday**, so `WEEKDAYNAME$(WEEKDAY(d$))` gives the name of the day `d$` falls on.

```basic
PRINT "[" + MONTHNAME$(7) + "]"
PRINT "[" + WEEKDAYNAME$(1) + "][" + WEEKDAYNAME$(5) + "][" + WEEKDAYNAME$(7) + "]"
PRINT WEEKDAYNAME$(WEEKDAY("2024-07-04"))
```
```
[July]
[Sunday][Thursday][Saturday]
Thursday
```

<a id="fn-monthcal-str"></a>
### MONTHCAL$

`MONTHCAL$(year, month)` returns a **String**: a multi-line text calendar from Python's `calendar.month()`, with weeks starting on Monday.

<a id="fn-yearcal-str"></a>
### YEARCAL$

`YEARCAL$(year)` returns a **String**: a three-column text calendar for the whole year.

```basic
PRINT MONTHCAL$(2024, 2)
```
```
   February 2024
Mo Tu We Th Fr Sa Su
          1  2  3  4
 5  6  7  8  9 10 11
12 13 14 15 16 17 18
19 20 21 22 23 24 25
26 27 28 29
```

<a id="fn-formatdate-str"></a>
### FORMATDATE$

`FORMATDATE$(date$, output_mask$ [, input_mask$])` returns a **String**.

Parses `date$` and writes it out using `output_mask$`.

- If you leave out `input_mask$`, DbBasic tries these formats in order: `YYYY-MM-DD`, `MM/DD/YYYY`, `MM-DD-YYYY`, `YYYY/MM/DD`, `YYYYMMDD`, `YYYY-MM-DD HH:MM:SS`. If none matches, you get `Invalid or unrecognized date string provided to FORMATDATE$`.
- If you supply `input_mask$`, it uses the same tokens as the output mask, and `date$` must match it exactly.

See [3.14](#314-formatdate-mask-tokens) for the tokens.

```basic
PRINT "[" + FORMATDATE$("2024-07-04", "MM/DD/YYYY") + "]"
PRINT "[" + FORMATDATE$("07/04/2024", "YYYYMMDD") + "]"
PRINT "[" + FORMATDATE$("2024-07-04 14:35:09", "DD.MM.YY HH:MI:SS") + "]"
PRINT "[" + FORMATDATE$("04-07-2024", "YYYY-MM-DD", "DD-MM-YYYY") + "]"
PRINT "[" + FORMATDATE$("2024-07-04", "%A, %B DD, YYYY") + "]"
```
```
[07/04/2024]
[20240704]
[04.07.24 14:35:09]
[2024-07-04]
[Thursday, July 04, 2024]
```

---

## 3.6 Array and hash functions

Arrays are 0-based Python lists. Hashes are ordered dictionaries with string keys. How keys are matched depends on `SET HASH_KEYS PRESERVE_CASE | IGNORE_CASE`; the default is `PRESERVE_CASE`. In `IGNORE_CASE` mode, keys are stored and looked up in upper case. Arrays and hashes are passed by reference, so `HASH_DELETE` and `HASH_RENAME` **change the hash you pass in**.

<a id="fn-array"></a>
### ARRAY

`ARRAY(v1, v2, ...)` returns an **Array** containing its arguments, in order. `ARRAY()` returns an empty array. Elements can have mixed types.

<a id="fn-array_size"></a>
### ARRAY_SIZE

`ARRAY_SIZE(arr)` returns a **Number**: the number of elements.

<a id="fn-ubound"></a>
### UBOUND

`UBOUND(arr)` returns a **Number**: the highest valid index, which is `ARRAY_SIZE(arr) - 1`. For an empty array it returns -1. A non-array argument causes `UBOUND requires one array argument.`

```basic
a = ARRAY("red", "green", "blue")
PRINT ARRAY_SIZE(a); UBOUND(a)
e = ARRAY()
PRINT ARRAY_SIZE(e); UBOUND(e)
PRINT a(0)
```
```
 3 2
 0-1
red
```

<a id="fn-find"></a>
### FIND

`FIND(arr, value)` returns a **Number**: the **0-based** index of the first element equal to `value`, or -1 if there is none. Comparison is exact and type-sensitive, so the string `"2"` does not match the number 2.

<a id="fn-array_join"></a>
### ARRAY_JOIN

`ARRAY_JOIN(arr, delimiter$)` returns a **String**.

Joins the elements of `arr` with `delimiter$`. Both arguments are required. Each element is converted with Python `str()`, so numbers appear as `1.0`.

```basic
PRINT FIND(a, "green"); FIND(a, "pink")
PRINT "[" + ARRAY_JOIN(a, ", ") + "]"
n = ARRAY(1, 2.5, 3)
PRINT "[" + ARRAY_JOIN(n, "|") + "]"
PRINT FIND(n, 2.5)
```
```
 1-1
[red, green, blue]
[1.0|2.5|3.0]
 1
```

<a id="fn-hash_count"></a>
### HASH_COUNT

`HASH_COUNT(h)` returns a **Number**: the number of keys.

<a id="fn-hash_exists"></a>
### HASH_EXISTS

`HASH_EXISTS(h, key$)` returns a **Boolean**. The key is normalised according to the `HASH_KEYS` mode, so in `PRESERVE_CASE` mode the test is case-sensitive. Dot access, such as `h.name`, is always case-insensitive.

<a id="fn-hash_keys"></a>
### HASH_KEYS

`HASH_KEYS(h)` returns an **Array** of the keys, in insertion order.

<a id="fn-hash_values"></a>
### HASH_VALUES

`HASH_VALUES(h)` returns an **Array** of the values, in insertion order.

<a id="fn-hash_rename"></a>
### HASH_RENAME

`HASH_RENAME(h, old$, new$)` returns a **Boolean**. It returns -1 if the key was renamed and 0 if `old$` was not found. If `new$` already exists as a different key, you get `Cannot rename key: new key '...' already exists.` The renamed key moves to the **end** of the key order.

<a id="fn-hash_delete"></a>
### HASH_DELETE

`HASH_DELETE(h, key$)` returns a **Number**. It removes `key$` if it exists. It **always returns 0**, whether or not the key was present.

These hash functions are functions, not statements. You must use the result, for example `r = HASH_DELETE(h, "city")`. A bare `HASH_DELETE(h, "city")` line fails with `Expected token RPAREN but got COMMA`.

```basic
h = PARSEJSON("{""name"":""Ann"",""age"":30,""ok"":true,""nothing"":null,""tags"":[""x"",""y""]}")
PRINT HASH_COUNT(h)
PRINT HASH_EXISTS(h, "name"); HASH_EXISTS(h, "NAME"); HASH_EXISTS(h, "zip")
PRINT "[" + ARRAY_JOIN(HASH_KEYS(h), ",") + "]"
PRINT ARRAY_SIZE(HASH_VALUES(h))
PRINT HASH_RENAME(h, "age", "years"); HASH_RENAME(h, "nope", "x")
PRINT h.years
r = HASH_DELETE(h, "nothing")
PRINT r; HASH_COUNT(h)
```
```
 5
-1 0 0
[name,age,ok,nothing,tags]
 5
-1 0
 30
 0 4
```

<a id="fn-hash_join"></a>
### HASH_JOIN

`HASH_JOIN(h1, h2 [, h3 ...])` returns a new **Hash** that merges two or more hashes. When a key appears in more than one hash, the value from the **later** hash wins, but the key keeps its first position. The hashes you pass in are not changed. Every argument must be a hash.

```basic
h1 = PARSEJSON("{""a"":1,""b"":2}")
h2 = PARSEJSON("{""b"":20,""c"":30}")
PRINT JSON_SERIALIZE$(HASH_JOIN(h1, h2))
```
```
{"a": 1, "b": 20, "c": 30}
```

---

## 3.7 Higher-order functions (FILTER, MAP, REDUCE)

These three functions take a **function reference**: the bare name of a user-defined `FUNCTION` or of any built-in in this chapter, written without parentheses or quotes. The parser recognises the reference only when it is the **second argument** and is an identifier that is not followed by `(`. A quoted name, such as `"UCASE$"`, is treated as an ordinary string. For `MAP` and `REDUCE` this is an error; for `FILTER` it becomes a substring criterion.

The examples in this section use these user-defined functions:

```basic
FUNCTION is_even(n)
  is_even = (MOD(n, 2) = 0)
END FUNCTION
FUNCTION dbl(n)
  dbl = n * 2
END FUNCTION
FUNCTION add(acc, n)
  add = acc + n
END FUNCTION
nums = ARRAY(1, 2, 3, 4, 5)
names = ARRAY("apple", "banana", "cherry")
```

<a id="fn-filter"></a>
### FILTER

`FILTER(arr, criteria [, include])` returns an **Array**.

- If `criteria` is a **function reference**, the function is called with each element. An element is kept when the result is truthy, which means non-zero or a non-empty string.
- Otherwise `criteria` is converted to a string, and an element is kept when that string is a **case-sensitive substring** of `str(element)`. Numbers are compared in their `"2.0"` form, so `FILTER(nums, "2")` also matches `12`.
- If `include` is 0, the test is inverted and the elements that do **not** match are returned. The default is to keep matches.

```basic
PRINT ARRAY_JOIN(FILTER(nums, is_even), ",")
PRINT ARRAY_JOIN(FILTER(nums, is_even, 0), ",")
PRINT ARRAY_JOIN(FILTER(names, "an"), ",")
PRINT ARRAY_JOIN(FILTER(names, "an", 0), ",")
PRINT ARRAY_JOIN(FILTER(ARRAY("12", "abc", "3.5"), ISNUMERIC), ",")
```
```
2.0,4.0
1.0,3.0,5.0
banana
apple,cherry
12,3.5
```

<a id="fn-map"></a>
### MAP

`MAP(arr, fn)` returns a new **Array** containing `fn(element)` for each element. `fn` must be a function reference.

```basic
PRINT ARRAY_JOIN(MAP(names, UCASE$), ",")
PRINT ARRAY_JOIN(MAP(nums, dbl), ",")
PRINT ARRAY_JOIN(MAP(names, LEN), ",")
```
```
APPLE,BANANA,CHERRY
2.0,4.0,6.0,8.0,10.0
5.0,6.0,6.0
```

<a id="fn-reduce"></a>
### REDUCE

`REDUCE(arr, fn [, initial])` returns **Any** type.

Folds the array into a single value by calling `acc = fn(acc, element)` for each element. If you supply `initial`, it is the starting accumulator. Otherwise the first element is the starting value and the fold begins with the second element. An empty array with no `initial` causes `REDUCE with no initial value requires a non-empty array.`

```basic
PRINT REDUCE(nums, add)
PRINT REDUCE(nums, add, 100)
PRINT REDUCE(nums, MAX)
```
```
 15
 115
 5
```

---

## 3.8 JSON functions

<a id="fn-parsejson"></a>
### PARSEJSON

`PARSEJSON(json$)` returns a **Hash** or an **Array**, depending on the top-level JSON value.

Nested objects become hashes and nested arrays become arrays. JSON `true` and `false` become -1 and 0, and `null` becomes `""`. If `json$` is empty or contains only whitespace, the result is an empty hash. Invalid JSON stops the program with `Invalid JSON string: <parser message>`. In `IGNORE_CASE` mode, all keys are upper-cased.

```basic
h = PARSEJSON("{""name"":""Ann"",""age"":30,""ok"":true,""nothing"":null,""tags"":[""x"",""y""]}")
PRINT TYPENAME$(h); " "; HASH_COUNT(h)
PRINT h.name; " "; h.age; " "; h.ok; " ["; h.nothing; "]"; " "; TYPENAME$(h.tags)
arr = PARSEJSON("[1,2,{""k"":""v""}]")
PRINT TYPENAME$(arr); ARRAY_SIZE(arr)
em = PARSEJSON("")
PRINT TYPENAME$(em); HASH_COUNT(em)
```
```
HASH  5
Ann  30 -1 [] ARRAY
ARRAY 3
HASH 0
```

<a id="fn-json_serialize-str"></a>
### JSON_SERIALIZE$

`JSON_SERIALIZE$(data [, options...])` returns a **String**.

Converts a hash or array, including nested ones, to JSON text. `data` must be a hash or an array. Floats that are whole numbers are written as integers. You can pass up to four more arguments, in any order:

| Option | Effect |
|---|---|
| a number > 0 | Pretty-print, indenting by that many spaces. 0 means compact output. Only the first number counts. |
| `"SORT_KEYS"` | Sort keys alphabetically, at every level. |
| `"LOWERCASE_KEYS"` | Lower-case **top-level** keys. |
| `"CAMELCASE_KEYS"` | Convert **top-level** `UPPER_SNAKE` keys to `camelCase`. This option takes priority over `LOWERCASE_KEYS`. |

Option names are not case-sensitive. **Automatic filtering:** if a top-level hash has both numeric keys (such as `"1"`) and non-numeric keys, the numeric keys are dropped from the output. Sorting is applied after the case conversion.

```basic
h1 = PARSEJSON("{""a"":1,""b"":2}")
PRINT JSON_SERIALIZE$(h1)
PRINT JSON_SERIALIZE$(ARRAY("red", "green", "blue"))
PRINT JSON_SERIALIZE$(h1, 2)
x = PARSEJSON("{""ZIP_CODE"":""32801"",""CITY_NAME"":""Orlando"",""b"":1}")
PRINT JSON_SERIALIZE$(x, "CAMELCASE_KEYS")
PRINT JSON_SERIALIZE$(x, "LOWERCASE_KEYS", "SORT_KEYS")
PRINT JSON_SERIALIZE$(x, 0, "sort_keys")
```
```
{"a": 1, "b": 2}
["red", "green", "blue"]
{
  "a": 1,
  "b": 2
}
{"zipCode": "32801", "cityName": "Orlando", "b": 1}
{"b": 1, "city_name": "Orlando", "zip_code": "32801"}
{"CITY_NAME": "Orlando", "ZIP_CODE": "32801", "b": 1}
```

---

## 3.9 URL and HTML encoding functions

<a id="fn-urlencode-str"></a>
### URLENCODE$

`URLENCODE$(s$)` returns a **String**.

Encodes `s$` for use in a query string, using Python `quote_plus`. Spaces become `+`, and reserved characters, including `/`, become `%XX`. Non-ASCII characters are encoded as UTF-8 first.

<a id="fn-urldecode-str"></a>
### URLDECODE$

`URLDECODE$(s$)` returns a **String**. It reverses `URLENCODE$`: `+` becomes a space and `%XX` sequences are decoded.

```basic
PRINT "[" + URLENCODE$("a b&c=d/é") + "]"
PRINT "[" + URLDECODE$("a+b%26c%3Dd") + "]"
```
```
[a+b%26c%3Dd%2F%C3%A9]
[a b&c=d]
```

<a id="fn-htmlencode-str"></a>
### HTMLENCODE$

`HTMLENCODE$(s$)` returns a **String**. It escapes `&`, `<`, `>`, `"` and `'`.

<a id="fn-htmldecode-str"></a>
### HTMLDECODE$

`HTMLDECODE$(s$)` returns a **String**. It decodes named and numeric HTML entities.

<a id="fn-striphtml-str"></a>
### STRIPHTML$

`STRIPHTML$(s$)` returns a **String**: the text content of an HTML fragment with all tags removed. It uses BeautifulSoup with the **`lxml`** parser, so the `lxml` package must be installed. Without it you get `Couldn't find a tree builder with the features you requested: lxml.`

```basic
PRINT "[" + HTMLENCODE$("<a href=""x"">Tom & 'Jerry'</a>") + "]"
PRINT "[" + HTMLDECODE$("&lt;b&gt;5 &amp; 6&lt;/b&gt; &copy;") + "]"
PRINT "[" + STRIPHTML$("<p>Hello <b>World</b></p>") + "]"
```
```
[&lt;a href=&quot;x&quot;&gt;Tom &amp; &#x27;Jerry&#x27;&lt;/a&gt;]
[<b>5 & 6</b> ©]
[Hello World]
```

<a id="fn-url_scheme-str"></a>
### URL_SCHEME$

`URL_SCHEME$(url$)` returns a **String**: the scheme, such as `https`.

<a id="fn-url_hostname-str"></a>
### URL_HOSTNAME$

`URL_HOSTNAME$(url$)` returns a **String**: the host name, in lower case, without the port. If the URL has no host, the function returns Python `None`.

<a id="fn-url_path-str"></a>
### URL_PATH$

`URL_PATH$(url$)` returns a **String**: the directory part of the URL path, without the query or fragment.

<a id="fn-url_filename-str"></a>
### URL_FILENAME$

`URL_FILENAME$(url$)` returns a **String**: the last segment of the URL path, without the query or fragment.

```basic
u$ = "https://www.example.com:8080/files/docs/report.pdf?x=1#top"
PRINT "[" + URL_SCHEME$(u$) + "]"
PRINT "[" + URL_HOSTNAME$(u$) + "]"
PRINT "[" + URL_PATH$(u$) + "]"
PRINT "[" + URL_FILENAME$(u$) + "]"
```
```
[https]
[www.example.com]
[/files/docs]
[report.pdf]
```

---

## 3.10 File and directory functions

In the path functions, `~` is expanded to the home directory for `FILE_EXISTS`, `FILESIZE`, `FILETIME` and `FILEATTR`. `DISKSPACE`, `BASENAME$` and `PATHNAME$` do not expand `~`.

<a id="fn-file_exists"></a>
### FILE_EXISTS

`FILE_EXISTS(path$)` returns a **Boolean**: -1 if a file *or directory* exists at `path$`.

<a id="fn-filesize"></a>
### FILESIZE

`FILESIZE(path$)` returns a **Number**: the size in bytes, or -1 if the path cannot be read.

<a id="fn-filetime"></a>
### FILETIME

`FILETIME(path$)` returns a **String**: the last-modified time as local `YYYY-MM-DD HH:MM:SS`, or `""` if the file does not exist.

<a id="fn-fileattr"></a>
### FILEATTR

`FILEATTR(path$)` returns a **Number**: a bit mask of attributes. 1 = read-only (owner write bit not set), 2 = hidden (Windows only), 4 = system (Windows only), 16 = directory. A path that does not exist returns 0, so check `FILE_EXISTS` first.

<a id="fn-diskspace"></a>
### DISKSPACE

`DISKSPACE(path$)` returns a **Number**: the free bytes available to the current user on the volume that holds `path$`, or -1 on error.

```basic
PRINT FILE_EXISTS("f.txt"); FILE_EXISTS("nope.txt")
PRINT FILESIZE("f.txt"); FILESIZE("nope.txt")
PRINT FILETIME("f.txt")
PRINT FILEATTR("f.txt"); FILEATTR("."); FILEATTR("nope")
IF DISKSPACE(".") > 0 THEN PRINT "disk ok"
PRINT DISKSPACE("/no/such/path")
```
```
-1 0
 6-1
2026-11-04 14:35:09
 0 16 0
disk ok
-1
```
(`f.txt` holds `hello` plus a newline. The `FILETIME` value is a sample.)

<a id="fn-basename-str"></a>
### BASENAME$

`BASENAME$(path$)` returns a **String**: the final part of a path. Only the host operating system's separator is recognised, so `\` is not treated as a separator on macOS or Linux.

<a id="fn-pathname-str"></a>
### PATHNAME$

`PATHNAME$(path$)` returns a **String**: the directory part of a path, or `""` if there is none. It has the same separator rule as `BASENAME$`.

```basic
PRINT "[" + BASENAME$("/home/dan/data/report.csv") + "]"
PRINT "[" + PATHNAME$("/home/dan/data/report.csv") + "]"
PRINT "[" + PATHNAME$("report.csv") + "]"
```
```
[report.csv]
[/home/dan/data]
[]
```

<a id="fn-curdir-str"></a>
### CURDIR$

`CURDIR$` or `CURDIR$()` returns a **String**: the absolute path of the current working directory. Passing an argument is an error.

<a id="fn-freefile"></a>
### FREEFILE

`FREEFILE` or `FREEFILE()` returns a **Number**: the lowest file-handle number, starting from 1, that is not currently open.

<a id="fn-eof"></a>
### EOF

`EOF(n)` returns a **Boolean**: -1 if the next read from file handle `#n` would hit end of file. The function looks ahead one character and then puts the file position back. If handle `n` is not open, you get `File #n is not open.` `EOF()` with no argument returns 0.

```basic
PRINT FREEFILE
OPEN "f.txt" FOR INPUT AS #1
PRINT FREEFILE()
PRINT EOF(1)
LINE INPUT #1, l$
PRINT EOF(1)
CLOSE #1
```
```
 1
 2
 0
-1
```

---

## 3.11 System and information functions

<a id="fn-command-str"></a>
### COMMAND$

`COMMAND$(n)` returns a **String**: the `n`th command-line argument after the script name, counting from 1. If `n` is out of range, including 0, the result is `""`.

<a id="fn-environ-str"></a>
### ENVIRON$

`ENVIRON$(name$)` returns a **String**: the value of an environment variable, or `""` if it is not set.

```basic
REM run as:  DBB_TEST=hi python dbbasic.py s6.bas one two
PRINT "[" + COMMAND$(1) + "][" + COMMAND$(2) + "][" + COMMAND$(9) + "]"
PRINT "[" + ENVIRON$("DBB_TEST") + "][" + ENVIRON$("NO_SUCH_VAR_X") + "]"
```
```
[one][two][]
[hi][]
```

`CURDIR$`, `FREEFILE` and `DISKSPACE` are described in [3.10](#310-file-and-directory-functions).

---

## 3.12 Type and utility functions

<a id="fn-typename-str"></a>
### TYPENAME$

`TYPENAME$(value)` returns a **String**: `"STRING"`, `"FLOAT"` (for every number, including integers that come from JSON), `"ARRAY"`, `"HASH"` or `"UNKNOWN"`.

<a id="fn-is_array"></a>
### IS_ARRAY

`IS_ARRAY(value)` returns a **Boolean**.

<a id="fn-is_hash"></a>
### IS_HASH

`IS_HASH(value)` returns a **Boolean**.

```basic
a = ARRAY("red", "green", "blue")
PRINT IS_ARRAY(a); IS_HASH(a); IS_ARRAY("x")
PRINT TYPENAME$(a); " "; TYPENAME$(1); " "; TYPENAME$("s")
```
```
-1 0 0
ARRAY FLOAT STRING
```

<a id="fn-nvl"></a>
### NVL

`NVL(v1, v2 [, v3 ...])` returns **Any** type.

Returns the first argument that is *truthy* and requires at least two arguments. **0, 0.0, `""` and empty arrays or hashes all count as empty**, so `NVL(0, 5)` returns 5. If every argument is empty, the result is `""`.

```basic
PRINT "[" + NVL("", 0, "fallback") + "]"
PRINT NVL(0, 5)
PRINT "[" + NVL("", "") + "]"
PRINT "[" + NVL("first", "second") + "]"
```
```
[fallback]
 5
[]
[first]
```

`VAL`, `STR$` and `ISNUMERIC` are described in the string and math sections.

---

## 3.13 FORMAT$ mask syntax

`FORMAT$` uses the `Formatter` class, which `PRINT USING` also uses (see Chapter 4). `FORMAT$` formats exactly **one** value. The formatter reads the mask from left to right:

1. Literal characters are copied to the output until a character that can start a mask field is found. These characters are `# 0 9 * $ ! & \ < > ^`.
2. The longest valid field at that point is matched and used to format the value.
3. After the value has been formatted, literal mask text is copied until the next field character, so `FORMAT$(42, "### units")` returns `" 42 units"`.
4. A numeric field directly followed by `%` formats the value multiplied by 100: `FORMAT$(0.256, "0.00%")` returns `"25.60%"`.

### Numeric fields

| Mask character | Meaning |
|---|---|
| `#` | Digit position. If there is no digit for it, a space is output. |
| `9` | Same as `#`. |
| `0` | Digit position. If there is no digit for it, `0` is output (zero padding). |
| `.` | Decimal point. The number of `#`, `0` or `9` characters after it sets the number of decimal places. The value is rounded with Python formatting. |
| `,` | Thousands separator. It is shown only when there are digits to its left; otherwise it becomes a space (or `*` with asterisk fill). |
| `$` at the start | Floating dollar sign, placed immediately before the first digit. `$$` behaves the same as `$`. |
| `**` at the start | Asterisk fill: leading spaces become `*`. It can be combined with `$` (`**$`). |
| `^^^^` at the end | Scientific notation, `mantissaE±exponent`. |
| space inside the field | A literal space. |

Overflow: if the integer part has more digits than the mask allows, the extra digits are written out in full. The result is never truncated, and no `%` overflow marker is added.

Negative numbers: a `-` replaces the space just before the first significant character. If there is no spare space, the `-` is put in front.

```basic
PRINT "[" + FORMAT$(1234.567, "#####.##") + "]"
PRINT "[" + FORMAT$(1234.567, "#,##0.00") + "]"
PRINT "[" + FORMAT$(1234567.891, "#,###,##0.00") + "]"
PRINT "[" + FORMAT$(42, "00000") + "]"
PRINT "[" + FORMAT$(42, "99999") + "]"
PRINT "[" + FORMAT$(-42.5, "####.##") + "]"
PRINT "[" + FORMAT$(-1234.5, "$#,##0.00") + "]"
PRINT "[" + FORMAT$(1234.5, "$###,###.##") + "]"
PRINT "[" + FORMAT$(5.5, "$$###.##") + "]"
PRINT "[" + FORMAT$(5.5, "**$###.##") + "]"
PRINT "[" + FORMAT$(-5.5, "**$###.##") + "]"
PRINT "[" + FORMAT$(123456, "##.##") + "]"
PRINT "[" + FORMAT$(0.5, "#.##") + "]"
PRINT "[" + FORMAT$(0, "###") + "]"
PRINT "[" + FORMAT$(99.999, "##.##") + "]"
PRINT "[" + FORMAT$(12345.678, "#.##^^^^") + "]"
PRINT "[" + FORMAT$(-12345.678, "##.##^^^^") + "]"
PRINT "[" + FORMAT$(0.00012, "##.##^^^^") + "]"
```
```
[ 1234.57]
[1,234.57]
[1,234,567.89]
[00042]
[   42]
[ -42.50]
[-$1,234.50]
[  $1,234.50]
[  $5.50]
[**$5.50]
[*-$5.50]
[123456.00]
[0.50]
[  0]
[100.00]
[1.23E+04]
[-1.23E+04]
[ 1.20E-4]
```

Note that a negative exponent is not zero-padded (`E-4`, whereas positive exponents are written `E+04`). Also, `#.##` shows a leading `0` for values below 1.

### String fields

| Mask | Meaning |
|---|---|
| `!` | The first character of the string only. |
| `&` | The whole string. If you repeat it (`&&&&`), the string is left-justified in a field at least as wide as the number of `&` characters. |
| `\  \` | A fixed-width field: two backslashes plus the number of spaces between them. Text is truncated or padded to fit and left-justified. |
| `<\  \`, `>\  \`, `^\  \` | A fixed-width field that is left-justified, right-justified or centred. |

```basic
PRINT "[" + FORMAT$("Hello World", "\    \") + "]"
PRINT "[" + FORMAT$("Hi", ">\    \") + "]"
PRINT "[" + FORMAT$("Hi", "^\    \") + "]"
PRINT "[" + FORMAT$("Hello", "!") + "]"
PRINT "[" + FORMAT$("Hello", "&") + "]"
PRINT "[" + FORMAT$("Hi", "&&&&&") + "]"
PRINT "[" + FORMAT$("Hi", "Name: &") + "]"
```
```
[Hello ]
[    Hi]
[  Hi  ]
[H]
[Hello]
[Hi   ]
[Name: Hi]
```

### Pitfalls

The type of the **value** decides which formatter is used. A string with a numeric mask is returned unchanged. A number with a string mask gives odd results; for example `FORMAT$(7, "&")` returns `"7&"`. Convert the number with `STR$` first.

The digits `0` and `9` and the characters `$ * ! &` start a field even when you meant them as literal text:

```basic
PRINT "[" + FORMAT$(3, "Qty: ###") + "]"
PRINT "[" + FORMAT$(5, "Total = ##") + "]"
PRINT "[" + FORMAT$(5, "Item 9: ##") + "]"
PRINT "[" + FORMAT$(5, "Wow! ##") + "]"
PRINT "[" + FORMAT$(3, "### units") + "]"
```
```
[Qty:   3]
[Total =  5]
[Item 5]
[Wow5!]
[  3 ]
```

To add a prefix or suffix, use concatenation, for example `"Qty " + FORMAT$(n, "###") + " units"`, or use backtick interpolation, for example `` `${FORMAT$(n, "###")} units` ``.

---

## 3.14 FORMATDATE$ mask tokens

`FORMATDATE$` converts a DbBasic date mask into a Python `strftime` pattern. **The whole mask is upper-cased first.** The tokens are then replaced in this order:

| Token | Meaning | Example (2024-07-04 14:35:09) |
|---|---|---|
| `YYYY` | 4-digit year | `2024` |
| `YY` | 2-digit year | `24` |
| `MM` | 2-digit month | `07` |
| `DD` | 2-digit day | `04` |
| `HH` | 2-digit hour, 24-hour clock | `14` |
| `MI` | 2-digit minute | `35` |
| `SS` | 2-digit second | `09` |

Everything else is copied through, but because of the upper-casing, literal letters come out in upper case: `"Day: DD"` produces `DAY: 04`. There are no tokens for month names, day names or 12-hour time, and `MON` is copied as literal text. The same tokens are used to read `input_mask$`.

**strftime passthrough (not officially documented).** Python `strftime` directives in the mask are passed through after upper-casing. Directives that are already upper case therefore work, notably `%A` (full weekday name) and `%B` (full month name). Lower-case directives such as `%p`, `%j`, `%a` and `%b` are changed into different directives and give wrong output (for example `%p` gives `P`, and `%j` gives `J`).

```basic
PRINT "[" + FORMATDATE$("2024-07-04", "yyyy/mm/dd") + "]"
PRINT "[" + FORMATDATE$("2024-07-04", "DD MON YYYY") + "]"
PRINT "[" + FORMATDATE$("2024-07-04", "Day: DD") + "]"
PRINT "[" + FORMATDATE$("2024-07-04", "%A, %B DD, YYYY") + "]"
PRINT "[" + FORMATDATE$("2024-07-04 14:35:09", "%I:MI %p") + "]"
```
```
[2024/07/04]
[04 MON 2024]
[DAY: 04]
[Thursday, July 04, 2024]
[02:35 P]
```

---

<a id="functions-available-inside-sql-sqlite"></a>
## 3.15 Functions available inside SQL (SQLite)

When the database engine is SQLite (the default), DbBasic registers the user-defined SQL functions below on every connection (`SqliteStringFunctions.register_all`). You can use them in any SQL statement: line-level `SELECT`, `INSERT`, `UPDATE` and so on, and scalar subqueries such as `x$ = (SELECT ...)`. **They are not available after `DATABASE ENGINE DUCKDB`.**

These functions use SQL semantics: booleans are **1 and 0** (not -1 and 0), and they return `NULL` when an argument has the wrong type. For example, `REVERSE(123)` is `NULL` because the argument is not text.

| SQL function | Arguments | Returns | Description |
|---|---|---|---|
| `REVERSE(s)` | 1 | text | Reverses `s`. |
| `STUFF(s, start, length, insert)` | 4 | text | Deletes `length` characters from `s`, starting at the 1-based position `start`, and inserts `insert` in their place. If `start` is out of range, `s` is returned unchanged. |
| `LEFT$(s, n)` | 2 | text | The first `n` characters. |
| `RIGHT$(s, n)` | 2 | text | The last `n` characters. `n` ≤ 0 gives `''`. |
| `LPAD(s, len, pad)` | 3 | text | Left-pads `s` to `len` characters with `pad`, which can be several characters. **Truncates** `s` if it is longer than `len`. |
| `RPAD(s, len, pad)` | 3 | text | Right-pads `s` to `len` characters. Truncates in the same way as `LPAD`. |
| `REPLICATE(s, n)` | 2 | text | `s` repeated `n` times. |
| `CHARINDEX(sub, s)` | 2 | integer | The 1-based position of `sub` in `s`, or 0. Note the argument order: the substring comes first, as in SQL Server. |
| `STARTS_WITH(s, prefix)` | 2 | 1/0 | Prefix test. |
| `ENDS_WITH(s, suffix)` | 2 | 1/0 | Suffix test. |
| `INITCAP(s)` | 1 | text | Title Case, like `PROPER$`. |
| `SPLIT_PART(s, delim, n)` | 3 | text | The `n`th field, counting from 1. Out of range gives `''`. |
| `TRANSLATE(s, from, to)` | 3 | text | Maps each character of `from` to the character in the same position in `to`. `from` and `to` must be the same length, otherwise you get an error. |
| `SOUNDEX(s)` | 1 | text | The same code as `SOUNDEX$`. |
| `INSTR(s, sub)` | 2 | integer | The 1-based position of `sub`, or 0. This replaces SQLite's built-in `instr`, with the same result. |
| `INSTR(s, sub, start)` | 3 | integer | Searches from the 1-based position `start`. A negative `start` counts back from the end of the string, and `start` = 0 returns 0. |
| `INSTR(s, sub, start, nth)` | 4 | integer | The position of the `nth` occurrence at or after `start`, or 0. |

```basic
SELECT REVERSE('DbBasic') AS r, STUFF('Hello World', 7, 5, 'There') AS s, LEFT$('abcdef', 3) AS l, RIGHT$('abcdef', 2) AS rt;
SELECT LPAD('42', 6, '0') AS lp, RPAD('ab', 5, '.') AS rp, REPLICATE('xy', 3) AS rep, CHARINDEX('lo', 'Hello') AS ci, CHARINDEX('z', 'Hello') AS ci0;
SELECT STARTS_WITH('Hello', 'He') AS sw, ENDS_WITH('Hello', 'x') AS ew, INITCAP('hello world') AS ic, SPLIT_PART('a-b-c', '-', 2) AS sp, SPLIT_PART('a-b-c', '-', 9) AS sp9;
SELECT TRANSLATE('hello', 'el', 'ip') AS tr, SOUNDEX('Robert') AS sx, INSTR('banana', 'an') AS i2, INSTR('banana', 'an', 3) AS i3, INSTR('banana', 'an', 1, 2) AS i4, INSTR('banana', 'a', -1) AS ineg;
SELECT LPAD('toolong', 3, '0') AS lpt, RIGHT$('abc', 0) AS r0, REVERSE(123) AS rnum;
x$ = (SELECT REVERSE('abc'))
PRINT x$
```
```
+---------+-------------+-----+----+
|    r    |      s      |  l  | rt |
+---------+-------------+-----+----+
| cisaBbD | Hello There | abc | ef |
+---------+-------------+-----+----+
(1 rows returned)
+--------+-------+--------+----+-----+
|   lp   |  rp   |  rep   | ci | ci0 |
+--------+-------+--------+----+-----+
| 000042 | ab... | xyxyxy | 4  | 0   |
+--------+-------+--------+----+-----+
(1 rows returned)
+----+----+-------------+----+------+
| sw | ew |     ic      | sp | sp9  |
+----+----+-------------+----+------+
| 1  | 0  | Hello World | b  |      |
+----+----+-------------+----+------+
(1 rows returned)
+-------+------+----+----+----+------+
|  tr   |  sx  | i2 | i3 | i4 | ineg |
+-------+------+----+----+----+------+
| hippo | R163 | 2  | 4  | 4  | 6    |
+-------+------+----+----+----+------+
(1 rows returned)
+-----+------+------+
| lpt |  r0  | rnum |
+-----+------+------+
| too |      | NULL |
+-----+------+------+
(1 rows returned)
cba
```

SQLite's own built-in functions (`UPPER`, `LOWER`, `SUBSTR`, `LENGTH`, `REPLACE`, `TRIM`, `ROUND`, `DATE`, `STRFTIME` and so on) remain available as usual. DbBasic built-ins such as `UCASE$` or `FORMAT$` can **not** be called from inside SQL, unless they appear in the table above.

---

## 3.16 Implementation notes and discrepancies

This section lists the places where `README.md` (function table) or `docs/DbBasicFunctionReference.md` differ from what `src/dbbasic.py` actually does, along with implementation quirks worth knowing.

### Documented but not implemented

1. **`CARDINAL$`** and **`ORDINAL$`** (fixed): listed in the README table but missing from the interpreter. Both are now implemented (see [CARDINAL$](#fn-cardinal-str)).

### Documented with the wrong signature or behaviour

2. **`EXTRACT$`**: the README gives `EXTRACT$(string$, before$, after$)` ("substring between before$ and after$"). The implementation is `EXTRACT$(s$, position [, delimiter$])` and returns the Nth delimited field.
3. **`DAYSINMONTH`** (fixed): the README gives `(year, month)` but the code took `(month, year)`. Both orders now work.
4. **`INSTRREV`**: the README gives `INSTRREV([start_pos,] haystack$, needle$)`. The actual signature is `INSTRREV(haystack$, needle$ [, start])`, where `start` limits the end of the search.
5. **`TYPENAME$`**: the README says it returns `"NUMBER"`. It actually returns `"FLOAT"` for all numbers, and `"UNKNOWN"` for other types.
6. **`WEEKDAYNAME$`** (fixed): it mapped 1 to Monday, not Sunday, so it did not match `WEEKDAY`. It now uses 1 = Sunday ... 7 = Saturday.
7. **`FORMAT$`** (fixed): it had no percent support and dropped any text after the field. A numeric field followed by `%` now scales by 100, and trailing literal text is kept (3.13).
8. **`HOUR`, `MINUTE`, `SECOND`** (fixed): `HOUR` returned 0 for a `YYYY-MM-DD HH:MM:SS` datetime. All three now use the time part of a datetime.
9. **`HASH_DELETE` and `HASH_RENAME`**: `DbBasicFunctionReference.md` shows them as statements (`HASH_DELETE(h, "city")`). That form is a syntax error; you must use the result, for example `r = HASH_DELETE(h, "city")`. `HASH_DELETE` always returns 0, so it cannot tell you whether the key existed. Use `HASH_EXISTS` first.
10. **`NVL(value, default)`**: the README describes it as "non-null/non-empty". It actually takes any number of arguments (at least two) and also treats `0` as empty.
11. **`ARRAY_JOIN`**: the code contains a default delimiter of `","`, but it is never used, because the function requires two or three arguments. Any third argument is ignored.
12. **`STR$`**: the documentation says "converts a number to its string representation". It also adds a leading space for zero and positive numbers, as `PRINT` does.

### Missing from `docs/DbBasicFunctionReference.md`

13. The older reference does not mention 33 implemented functions: `CENTER$`, `DATESERIAL`, `DAYSINMONTH`, `DAYSINYEAR`, `EXTRACT$`, `FILTER`, `FORMAT$`, `HOUR`, `HTMLDECODE$`, `HTMLENCODE$`, `INSTRREV`, `ISALNUM`, `ISALPHA`, `ISDATE`, `ISDIGIT`, `ISLEAP`, `ISNUMERIC`, `MAP`, `MINUTE`, `MONTHCAL$`, `MONTHNAME$`, `NOW`, `NVL`, `PARSEJSON`, `REDUCE`, `SECOND`, `SOUNDEX$`, `STRIPHTML$`, `TYPENAME$`, `URLDECODE$`, `URLENCODE$`, `WEEKDAYNAME$` and `YEARCAL$`. Every function in the README table except `CARDINAL$` and `ORDINAL$` is implemented. Neither document describes the SQLite-side functions in [3.15](#functions-available-inside-sql-sqlite).

### Implementation quirks (not documented elsewhere)

14. **`RIGHT$(s$, 0)`** returns the whole string, not `""`. The SQL `RIGHT$` returns `''`.
15. **`HEX$` and `OCT$` with negative numbers** return a malformed result (`HEX$(-255)` returns `"xff"`).
16. **Date input formats are inconsistent.** `DATEADD`, `DATEDIFF`, `YEAR`, `MONTH`, `DAY` and `WEEKDAY` accept only `YYYY-MM-DD` and `YYYYMMDD`, while `ISDATE` and `FORMATDATE$` accept several more formats. `ISDATE("07/04/2024")` is true, but `YEAR("07/04/2024")` stops the program. That error (`Invalid date format: ...`) is a plain Python `ValueError`, without the usual line and column information.
17. **`FORMATDATE$` upper-cases the whole mask**, so literal text changes case. Upper-case `strftime` directives (`%A`, `%B`) happen to work; lower-case ones do not.
18. **Numbers converted to text show `.0`** in `LEN`, `ARRAY_JOIN`, `MAP` results joined as text, and `FILTER` substring matching (`LEN(10)` is 4).
19. **`VAL` does not read numeric prefixes** (`VAL("12abc")` is 0, whereas in classic BASIC it is 12). It does accept `"nan"` and `"inf"`, and so does `ISNUMERIC`.
20. **`SOUNDEX$` and SQL `SOUNDEX`** do not let vowels separate repeated codes, so a few names differ from standard Soundex (`Tymczak` gives `T520`).
21. **`STRIPHTML$` needs the `lxml` package** as well as BeautifulSoup. If it is missing, the function fails at run time.
22. **`INSTR` argument order differs** between DbBasic (`INSTR(start, s$, sub$)`) and SQL (`INSTR(s, sub, start)`).
23. **The SQLite functions are not registered for DuckDB.** SQL that uses `LPAD`, `SPLIT_PART` and so on may fail, or use DuckDB's own versions with different semantics, after `DATABASE ENGINE DUCKDB`.
24. **`FORMAT$` treats the literal characters `0`, `9`, `$`, `*`, `!` and `&` in the mask as field markers**, and a negative exponent in `^^^^` output is not zero-padded (`E-4`).
25. **Argument-count checking is uneven.** Some of the classic functions (`LEFT$`, `MID$`, `INT`, `SIN` and others) do not validate their arguments, so mistakes show up as Python errors (`list index out of range`, `must be real number, not str`).
26. **`HASH_JOIN`'s source code contains an unreachable duplicate block** after its `return`. It is harmless.
27. **Function names usable as references** for `FILTER`, `MAP`, `REDUCE` and `SORT WITH` are found by scanning the source code of `_execute_function` at run time (`_get_builtin_fn_names`). A compiled (Nuitka) build cannot read its source, so it uses the static list `Interpreter.BUILTIN_FN_NAMES`, which contains all 124 built-ins. `compilenuitka.sh` checks that list against the source before building and stops if they differ, so add new functions to it.
