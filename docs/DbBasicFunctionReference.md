# **DbBasic Function Reference**

This document provides a reference for all built-in functions available in the DbBasic language. Functions are grouped by category.

---

## **📁 File System Functions**

* `CURDIR$()`  
  * Returns the current working directory as a string.  
* `DISKSPACE(path$)`  
  * Returns the number of free bytes on the disk containing the specified path.  
* `EOF(file_num)`  
  * Returns true (`-1`) if the end of the specified file handle has been reached, otherwise false (`0`).  
* `FILE_EXISTS(path$)`  
  * Returns true (`-1`) if the specified file or directory path exists, otherwise false (`0`).  
* `FILEATTR(path$)`  
  * Returns a number representing the file's attributes (e.g., read-only, directory).  
* `FILESIZE(path$)`  
  * Returns the size of the specified file in bytes. Returns `-1` if the file doesn't exist.  
* `FILETIME(path$)`  
  * Returns the last modification timestamp of the file as a string (e.g., "YYYY-MM-DD HH:MI:SS").  
* `FREEFILE()`  
  * Returns the next available integer for use as a file handle.

---

## **📝 String Functions**

* `ASC(string$)`  
  * Returns the ASCII code of the first character in the string.  
* `CHR$(code)`  
  * Returns the character corresponding to the given ASCII `code`.  
* `FORMATDATE$(date$, format_mask$)`  
  * Formats a date string according to a specified mask (e.g., "YYYY-MM-DD").  
* `HEX$(number)`  
  * Returns the hexadecimal representation of a number as a string.  
* `INSTR([start_pos,] haystack$, needle$)`  
  * Finds the starting position of `needle$` within `haystack$`. Returns `0` if not found.  
* `JSON_SERIALIZE$(variable, [indent], [options...])`  
  * Converts a DbBasic `HASH` or `ARRAY` into a JSON formatted string.  
* `LCASE$(string$)`  
  * Converts a string to all lowercase characters.  
* `LEFT$(string$, length)`  
  * Returns the first `length` characters from the left of the string.  
* `LTRIM$(string$)`  
  * Removes whitespace from the beginning (left side) of a string.  
* `MID$(string$, start_pos, [length])`  
  * Returns a substring of a specified `length` starting from `start_pos`.  
* `OCT$(number)`  
  * Returns the octal representation of a number as a string.  
* `PADLEFT$(text$, length, pad_char$)`  
  * Pads a string on the left to a total `length` using `pad_char$`.  
* `PADRIGHT$(text$, length, pad_char$)`  
  * Pads a string on the right to a total `length` using `pad_char$`.  
* `PROPER$(string$)`  
  * Converts a string to title case (e.g., "hello world" becomes "Hello World").  
* `REPEAT$(string$, count)`  
  * Returns a string consisting of `string$` repeated `count` times.  
* `REPLACE$(source$, old$, new$, [count], [ignore_case])`  
  * Replaces occurrences of `old$` with `new$` in the `source$` string.  
* `REVERSE$(string$)`  
  * Reverses the order of characters in a string.  
* `RIGHT$(string$, length)`  
  * Returns the last `length` characters from the right of the string.  
* `RTRIM$(string$)`  
  * Removes whitespace from the end (right side) of a string.  
* `SPACE$(count)`  
  * Returns a string consisting of `count` spaces.  
* `SPLIT(string$, delimiter$, [limit])`  
  * Splits a string by a `delimiter$` and returns an `ARRAY` of substrings.  
* `STR$(number)`  
  * Converts a number to its string representation.  
* `TRIM$(string$)`  
  * Removes whitespace from both the beginning and end of a string.  
* `UCASE$(string$)`  
  * Converts a string to all uppercase characters.

---

## **🔢 Math Functions**

* `ABS(number)`  
  * Returns the absolute value of a number.  
* `ATN(number)`  
  * Returns the arctangent of a number in radians.  
* `ATAN2(y, x)`  
  * Returns the arctangent of `y/x` in radians.  
* `CEIL(number)`  
  * Rounds a number up to the nearest integer.  
* `COS(number)`  
  * Returns the cosine of an angle given in radians.  
* `DEGREES(radians)`  
  * Converts an angle from radians to degrees.  
* `EXP(number)`  
  * Returns e (the base of natural logarithms) raised to the power of `number`.  
* `FIX(number)`  
  * Truncates the decimal part of a number.  
* `FLOOR(number)`  
  * Rounds a number down to the nearest integer.  
* `INT(number)`  
  * Returns the integer portion of a number by rounding down (same as `FLOOR`).  
* `LOG(number)`  
  * Returns the natural logarithm of a number.  
* `MAX(num1, num2, ...)`  
  * Returns the largest number from a list of arguments.  
* `MIN(num1, num2, ...)`  
  * Returns the smallest number from a list of arguments.  
* `MOD(number1, number2)`  
  * Returns the remainder of `number1` divided by `number2`.  
* `POWER(base, exponent)`  
  * Returns the value of `base` raised to the power of `exponent`.  
* `RADIANS(degrees)`  
  * Converts an angle from degrees to radians.  
* `RND([max_val])`  
  * Returns a random number. If `max_val` is provided, returns an integer between 1 and `max_val`. Otherwise, returns a float between 0 and 1\.  
* `ROUND(number, [decimals])`  
  * Rounds a number to a specified number of `decimals`.  
* `SGN(number)`  
  * Returns the sign of a number (`-1` for negative, `0` for zero, `1` for positive).  
* `SIN(number)`  
  * Returns the sine of an angle given in radians.  
* `SQR(number)`  
  * Returns the square root of a number.  
* `TAN(number)`  
  * Returns the tangent of an angle given in radians.  
* `VAL(string$)`  
  * Converts a string representation of a number into a numeric value.

---

## **🗃️ Array & Hash Functions**

* `ARRAY(...)`  
  * A constructor that creates and returns a new `ARRAY` from the provided arguments.  
* `ARRAY_JOIN(array, delimiter$)`  
  * Concatenates the elements of an `array` into a single string, separated by `delimiter$`.  
* `ARRAY_SIZE(array)`  
  * Returns the total number of elements in an `array`.  
* `FIND(array, value)`  
  * Returns the zero-based index of the first occurrence of `value` in an `array`. Returns `-1` if not found.  
* `HASH_COUNT(hash)`  
  * Returns the number of key-value pairs in a `hash`.  
* `HASH_DELETE(hash, key$)`  
  * Deletes a key-value pair from a `hash`.  
* `HASH_EXISTS(hash, key$)`  
  * Returns true (`-1`) if the `key$` exists in the `hash`, otherwise false (`0`).  
* `HASH_JOIN(hash1, hash2, ...)`  
  * Merges two or more hashes into a new `hash`. Keys from later hashes overwrite earlier ones.  
* `HASH_KEYS(hash)`  
  * Returns an `ARRAY` containing all the keys from a `hash`.  
* `HASH_RENAME(hash, old_key$, new_key$)`  
  * Renames a key in a `hash`.  
* `HASH_VALUES(hash)`  
  * Returns an `ARRAY` containing all the values from a `hash`.  
* `UBOUND(array)`  
  * Returns the upper bound (the highest index) of an `array`. Returns `-1` for an empty array.

---

## **📅 Date & Time Functions**

* `DATE$()`  
  * Returns the current system date as a "YYYY-MM-DD" string.  
* `DATEADD(date$, days)`  
  * Adds a specified number of `days` to a `date$` and returns the new date string.  
* `DATEDIFF(date1$, date2$)`  
  * Returns the number of days between two date strings.  
* `DAY(date$)`  
  * Returns the day of the month (1-31) from a date string.  
* `MONTH(date$)`  
  * Returns the month (1-12) from a date string.  
* `TIME$()`  
  * Returns the current system time as an "HH:MI:SS" string.  
* `WEEKDAY(date$)`  
  * Returns the day of the week as a number (1 for Sunday, 7 for Saturday).  
* `YEAR(date$)`  
  * Returns the year from a date string.

---

## **ℹ️ Information & Type Functions**

* `COMMAND$(index)`  
  * Returns the command-line argument at the specified `index` position.  
* `CONTAINS(string$, substring$)`  
  * Returns true (`-1`) if `string$` contains `substring$`, otherwise false (`0`).  
* `ENDSWITH(string$, suffix$)`  
  * Returns true (`-1`) if `string$` ends with `suffix$`, otherwise false (`0`).  
* `ENVIRON$(var_name$)`  
  * Returns the value of a system environment variable.  
* `IS_ARRAY(variable)`  
  * Returns true (`-1`) if the `variable` is an `ARRAY`, otherwise false (`0`).  
* `IS_HASH(variable)`  
  * Returns true (`-1`) if the `variable` is a `HASH`, otherwise false (`0`).  
* `ISALNUM(string$)`  
  * Returns true (`-1`) if all characters in the string are alphanumeric, otherwise false (`0`).  
* `ISALPHA(string$)`  
  * Returns true (`-1`) if all characters in the string are alphabetic, otherwise false (`0`).  
* `ISDIGIT(string$)`  
  * Returns true (`-1`) if all characters in the string are digits, otherwise false (`0`).  
* `LEN(value)`  
  * Returns the number of characters in the string representation of a value.  
* `STARTSWITH(string$, prefix$)`  
  * Returns true (`-1`) if `string$` starts with `prefix$`, otherwise false (`0`).

