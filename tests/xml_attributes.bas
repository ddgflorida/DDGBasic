REM Flat LOAD XML loads the record element's attributes as columns. Failed checks raise errors.
DATABASE OPEN ":memory:"
LOAD XML "data/books_attr.xml" CREATE TABLE b OPTIONS "record_tag=book"
REM id clashes with a child element called id, so the attribute column is id_attr
IF (SELECT id_attr FROM b WHERE title = 'Dune') <> "b1" THEN ERROR 1, "attribute column"
IF (SELECT lang FROM b WHERE title = 'Dune') <> "en" THEN ERROR 1, "second attribute"
IF (SELECT status FROM b WHERE title = 'Emma') <> "new" THEN ERROR 1, "namespaced attribute"
IF (SELECT id FROM b WHERE title = 'Emma') <> "9780141439587" THEN ERROR 1, "child element of the same name"
IF (SELECT COUNT(*) FROM b WHERE title = 'Untitled' AND id_attr IS NULL) <> 1 THEN ERROR 1, "missing attribute"
LOAD XML "data/books_attr.xml" CREATE TABLE no_attrs OPTIONS "record_tag=book, attributes=false"
IF (SELECT COUNT(*) FROM pragma_table_info('no_attrs') WHERE name IN ('id_attr', 'lang', 'status')) <> 0 THEN ERROR 1, "attributes=false"
PRINT "xml_attributes: all checks passed"
REM EXPECT: xml_attributes: all checks passed
