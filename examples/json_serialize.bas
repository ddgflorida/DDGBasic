REM --- JSON_SERIALIZE$ Examples ---

REM 1. Create a HASH variable to work with
DIM person AS HASH
person("name") = "Jane Doe"
person("city") = "New York"
person("id") = 12345
person("is_active") = -1 ' -1 is TRUE in BASIC

PRINT "--- Original HASH variable ---"
PRINT person
PRINT ""

REM 2. Example 1: Default Compact Serialization (Uppercase Keys)
REM This is ideal for internal data transfer or logging.
PRINT "--- 1. Compact JSON (default) ---"
compact_json$ = JSON_SERIALIZE$(person)
PRINT compact_json$
PRINT ""

REM 3. Example 2: Pretty-Printed JSON
REM Using an indent of 4 spaces for human readability.
PRINT "--- 2. Pretty-Printed with 4-space indent ---"
pretty_json$ = JSON_SERIALIZE$(person, 4)
PRINT pretty_json$
PRINT ""

REM 4. Example 3: Pretty-Printed and Sorted JSON
REM Same as above, but with keys sorted alphabetically.
PRINT "--- 3. Pretty-Printed, Sorted ---"
sorted_json$ = JSON_SERIALIZE$(person, 4, "SORT_KEYS")
PRINT sorted_json$
PRINT ""

REM 5. Example 4: Generating JSON for an External API (Lowercase)
REM This uses the "LOWERCASE_KEYS" option to match external requirements.
PRINT "--- 4. Compact JSON with Lowercase Keys for an API ---"
api_json_lower$ = JSON_SERIALIZE$(person, 0, "LOWERCASE_KEYS")
PRINT api_json_lower$
PRINT ""

REM 6. Example 5: Generating JSON for a modern Web API (camelCase)
REM This uses the "CAMELCASE_KEYS" option, which is very common.
PRINT "--- 5. Pretty-Printed JSON with camelCase Keys ---"
api_json_camel$ = JSON_SERIALIZE$(person, 2, "CAMELCASE_KEYS")
PRINT api_json_camel$
PRINT ""

END