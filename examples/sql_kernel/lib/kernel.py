# Example SQL kernel, mimicking a SQL terminal
# and connected to a SQLite in-memory database

__all__ = ("SqlKernel",)

import itertools
import logging
import operator
import sqlite3

import sqlparse

import callysto

_logger = logging.getLogger(__name__)

class SqlKernel (callysto.BaseKernel):
    implementation_name = "SQL Kernel"
    implementation_version = "0.0 (SQLite %s)" % sqlite3.sqlite_version

    language_name = "sql"
    language_mimetype = "application/sql"
    language_version = "SQL:2011"
    language_file_extension = ".sql"

    def do_startup_ (self, **kwargs):
        self._database = sqlite3.connect(":memory:")

    def do_shutdown_ (self, will_restart):
        self._database.close()

    def do_execute_ (self, code):
        try:
            statements = sqlparse.split(code)
            n_statements = len(statements)

            for (statement_n, statement) in enumerate(statements):
                if (n_statements > 1):
                    prefix = "statement %d of %d: " % (
                        statement_n+1, n_statements)
                else:
                    prefix = ''

                statement = sqlparse.format(
                    statement,
                    identifier_case = "lower",
                    keyword_case = "upper",
                    reindent = True,
                    strip_comments = True)

                # execute the statement
                cursor = self._database.cursor()
                cursor.execute(statement)

                # commit any change
                self._database.commit()

                status_message = ""

                # if the database says rows have been affected,
                # we forward this information to the user
                if (cursor.rowcount > 0):
                    status_message = "%d %s affected; " % (
                        cursor.rowcount,
                        callysto.utils.plural("row", cursor.rowcount))

                # if the database returns a result set,
                # we show it as a CSV table with header
                if (cursor.description is not None):
                    header = map(operator.itemgetter(0), cursor.description)
                    table = [header]
                    for row in cursor:
                        table.append(row)

                    nrows = len(table) - 1
                    status_message += "%d %s returned" % (
                        nrows, callysto.utils.plural("row", nrows))

                    yield (callysto.MIME_TYPE.CSV_WITH_HEADER, table)

                else:
                    status_message += "no rows returned"

                if (0 < statement_n < n_statements):
                    yield '\n'

                yield prefix + status_message

        except Exception as exception:
            self._database.rollback()
            raise exception

if (__name__ == "__main__"):
    SqlKernel.launch(debug = True)
