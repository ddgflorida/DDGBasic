# DbBasic: A Data-Centric BASIC Interpreter

![Language](https://img.shields.io/badge/language-BASIC-blue.svg)
![Backend](https://img.shields.io/badge/backend-Python-green.svg)
![Status](https://img.shields.io/badge/status-Active-brightgreen.svg)

DbBasic is a custom, modern dialect of the BASIC programming language, built from the ground up in Python. It is designed with a strong focus on data processing, file manipulation, and direct database interaction, making it a powerful tool for scripting and data analysis tasks.
You can think of it as either SQLite/DuckDb wrapped in a procedural language, or a BASIC with direct SQLite/DuckDb support.

---

## ✨ Key Features

DbBasic combines the simplicity of classic BASIC syntax with powerful, modern features for today's data-driven world.

* ### Dual Database Engines
    * **SQLite & DuckDB Support:** Seamlessly switch between the world's most deployed database engine (**SQLite**) for general-purpose tasks and a high-performance analytical engine (**DuckDB**) for complex queries.
    * **SQL:** Directly embed SQL statements, iterate over resultsets.
    * **Engine Switching:** Use the `DATABASE ENGINE [SQLITE|DUCKDB]` command to change the backend at any time within a script.

* ### Powerful Data Ingestion & Transformation
    * **`LOAD` Command:** Ingest data directly from `.csv`, `fixed`, `.json`,`.jsonl`, `xml`, and `.xls`/`.xlsx` (**Excel**) files into database tables or for file-to-file conversion.
    * **Advanced Options:** The `LOAD` command includes a rich `OPTIONS` string to handle headers, delimiters, and powerful transformations.
    * **Field Manipulation:** Select, rename (`fields=[Name] as N`), and exclude (`fields=*,-[Name]`) columns on the fly during data loading.

* ### Modern Connectivity & Tooling
    * **`FETCH` Command:** Download data directly from web URLs via GET or POST requests, with support for file uploads and custom headers.
    * **`SHELL` Command:** Execute shell commands directly from the script to interact with the underlying operating system.
    * **Data Analysis:** Use `ANALYZE [CSV|JSON|JSONL|FIXED|TEXT|XML]` commands to get detailed statistical reports and schema information about local files.
    * **Format Conversion:** Use LOAD command combined with SET OUTPUT/FORMAT [format] with a SELECT statement to convert files to different formats.

* ### Rich Language & SQL Integration
    * **Full Control Flow:** Includes robust, nestable control structures like `IF...THEN...ELSE...END IF`, `FOR...TO...NEXT`, `WHILE...WEND`, and `FOR EACH`.
    * **`EXIT` Statements:** Reliably exit any loop (`EXIT FOR`, `EXIT WHILE`), even from within nested blocks.
    * **Direct SQL Execution:** Run any SQL query directly. The interpreter supports transactions (`BEGIN`, `COMMIT`, `ROLLBACK`) and logical checks like `IF EXISTS (...)`.
    * **Embedded Subqueries:** Use scalar SQL subqueries directly in assignment statements (e.g., `LET count = (SELECT COUNT(*) FROM my_table)`).
    * **Modern Data Types:** Includes support for `HASH` (dictionary) and dynamic `ARRAY` data structures, with a rich library of built-in functions.

---

## 🚀 Quick Start Example

The following DbBasic script demonstrates several key features: it downloads a CSV file, loads it into a DuckDB in-memory table, and queries the result.

```basic
REM --- Set engine to DuckDB for high-speed analytics ---
DATABASE ENGINE DUCKDB
DATABASE OPEN ":memory:"

REM --- Download a CSV and create a table from it in one command ---
PRINT "Fetching and loading data..."
CREATE TABLE domains AS SELECT * FROM read_csv_auto('https://raw.githubusercontent.com/cisagov/dotgov-data/main/current-full.csv');

REM --- Run a query on the loaded data ---
PRINT "Top 5 States with the most .gov domains:"
SELECT State, COUNT(*) AS DomainCount
FROM domains
GROUP BY State
ORDER BY DomainCount DESC
LIMIT 5;

DATABASE CLOSE
END






