# **DbBasic Command Reference**

This document provides a quick reference to all available commands in the DbBasic language.

| Statement Keyword        | Description                                             |
|-------------------------|--------------------------------------------------------|
| ANALYZE CSV             | Provides a detailed statistical report on a CSV file, including delimiter detection, header presence, and column data types. |
| ANALYZE FIXED           | Analyzes a fixed-width text file, automatically guessing column breaks if not specified, and reports on the layout. |
| ANALYZE JSON            | Analyzes a JSON file, reporting on its structure, record count, and the consistency of object keys. |
| ANALYZE JSONL           | Analyzes a JSON Lines file, reporting on structural consistency, and counting valid and invalid JSON objects. |
| ANALYZE TEXT            | Provides a statistical analysis of a plain text file, including character, word, and line counts, encoding, and newline style. |
| ANALYZE XML             | Analyzes an XML file to determine its structure, infer the primary record tag, and list its fields. |
| BELL                    | Emits an audible system beep sound.                    |
| BROWSER                 | Opens a specified URL in the system's default web browser. |
| CHAIN                   | Transfers program execution to a different DbBasic script, optionally preserving variables. |
| CHDIR                   | Changes the current working directory.                  |
| CLOSE                   | Closes a specific file handle or all open file handles. |
| COPY ... AS             | Copies a source file to a destination file.             |
| DATABASE                | Manages the database connection, allowing you to open a file-based database or switch the database engine (SQLite/DuckDB). |
| DESCRIBE                | Displays the CREATE TABLE statement for an existing database table. |
| DIM                     | Declares a new variable as an ARRAY or a HASH.          |
| DO ... LOOP             | Defines a block of code that executes repeatedly, with optional WHILE or UNTIL conditions at the beginning or end. |
| DUMP                    | A debugging command to print the internal state of the interpreter, such as tokens, variables, or labels. |
| END                     | Terminates the program execution.                       |
| ERROR                   | Triggers a user-defined runtime error with a specific error code and optional message. |
| EXECUTE                 | Executes a SQL statement that is dynamically constructed in a string variable. |
| EXIT                    | Immediately exits the current loop structure (FOR, DO, or WHILE). |
| FETCH                   | Retrieves data from a URL via HTTP GET or POST, storing the result in a variable or file. |
| FILES                   | Lists files and directories in the filesystem, similar to DIR or ls, with options for recursion and details. |
| FOR ... NEXT            | Defines a loop that iterates a set number of times, over the results of a SQL query, or through records in a CSV, JSON, JSONL, or FILES list. |
| FOR EACH ... NEXT       | Iterates over each key in a HASH variable.              |
| FORM ... ENDFORM        | Defines the layout and elements of a text-based user interface (TUI) form. |
| GOSUB ... RETURN        | Jumps to a labeled subroutine and returns to the next statement after the GOSUB call. |
| GOTO                    | Unconditionally jumps program execution to a specified label. |
| IF ... THEN ... ELSE ... END IF | Executes blocks of code conditionally.           |
| INPUT                   | Prompts the user for input from the console and stores it in a variable. |
| KILL                    | Deletes a file from the filesystem.                     |
| LET                     | Assigns a value to a variable (the LET keyword is optional). |
| LINE INPUT              | Reads a single line of text from an open file into a variable. |
| LOAD                    | Loads data from a file (CSV, JSON, JSONL, XML, HTML, FIXED, EXCEL, TEXT) into a database table. |
| MKDIR                   | Creates a new directory.                                |
| NAME ... AS             | Renames a file.                                         |
| ON ERROR GOTO           | Specifies a label to jump to when a runtime error occurs. |
| OPEN                    | Opens a file for reading, writing, or appending, assigning it a file handle. |
| OPENFORM                | Displays a previously defined FORM to the user for interaction. |
| PARSE JSON              | Parses a JSON-formatted string into a HASH or ARRAY variable. |
| POP                     | Removes the last element from an array, optionally storing it in a variable. |
| PRINT                   | Outputs text, variables, or expressions to the console or an open file. |
| PUSH                    | Adds a new element to the end of an array.              |
| READ FILE               | Reads the entire content of a text file into a single string variable. |
| REDIM                   | Resizes a previously declared ARRAY.                    |
| RESUME                  | Used within an error-handling routine to resume program execution at the statement after the one that caused the error. |
| REVERSE                 | Reverses the order of elements in an array.             |
| RMDIR                   | Removes an empty directory.                             |
| RUN                     | Executes another DbBasic script as a subroutine and returns control to the calling script upon completion. |
| SET                     | Configures global settings for the interpreter, such as OUTPUT redirection or error handling behavior. |
| SHELL                   | Executes a command in the underlying operating system shell. |
| SHIFT                   | Removes the first element from an array, optionally storing it in a variable. |
| SHOW                    | Displays database schema information, such as SHOW TABLES or SHOW INDEXES. |
| SORT                    | Sorts an array in-place, with an optional key for sorting arrays of hashes. |
| SPLICE                  | Modifies an array by removing, replacing, and/or adding elements at a specific index. |
| SQL Statement           | Any line starting with a SQL keyword (e.g., SELECT, INSERT, UPDATE) is executed directly against the current database. |
| TROFF                   | Turns off (Trace Off) the line-by-line execution trace. |
| TRON                    | Turns on (Trace On) a line-by-line execution trace for debugging. |
| UNSHIFT                 | Adds a new element to the beginning of an array.        |
| UNZIP                   | Extracts files from a zip archive into a specified directory. |
| WHILE ... WEND          | Executes a block of code as long as a specified condition is true. |
| WRITE                   | Writes a comma-separated list of expressions to the console or a file, automatically quoting strings. |
| ZIP                     | Creates a zip archive from a list of specified files.   |

---

