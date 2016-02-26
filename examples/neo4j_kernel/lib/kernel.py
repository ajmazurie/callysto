"""
Example Neo4j kernel, mimicking a CYPHER terminal
and connected to a Neo4j database instance
"""

__all__ = (
    "Neo4jKernel",)

import logging
import re
import urlparse

import py2neo
import pydotplus

import callysto
import callysto.renderers.graphviz

_logger = logging.getLogger(__name__)

renderer = callysto.renderers.graphviz.GraphvizRenderer()

class Neo4jKernel (callysto.BaseKernel):
    implementation_name = "Neo4j Kernel"
    implementation_version = "0.0 (py2neo %s)" % py2neo.__version__

    language_name = "cypher"
    language_file_extension = ".cypher"

    def connect_to (self, code, **kwargs):
        """ Usage: connect-to <URL> [--user STRING] [--password STRING]

            Options:
                URL                Neo4j server URL
                --user STRING      Neo4j server username (optional)
                --password STRING  Neo4j server password (optional)

            Note that --user and --password, if provided, will
            override any credential found in the URL itself.
        """
        # parse the URL, setting aside credentials (if any)
        URL = urlparse.urlparse(kwargs["<URL>"])

        url = "%s://%s%s" % (URL.scheme, URL.netloc, URL.path)
        _logger.debug("connecting to Neo4j server at %s" % url)

        # authenticate the connection if credentials are provided
        username = kwargs.get("--user", URL.username)
        password = kwargs.get("--password", URL.password)

        if (username is not None) and (password is not None):
            _logger.debug("authenticating with user '%s'" % username)
            py2neo.authenticate(URL.netloc, username, password)
            _logger.debug("authenticating: done")

        self._database = py2neo.Graph(url)
        _logger.debug("connecting: done (Neo4j server %s)" % \
            '.'.join(map(str, self._database.neo4j_version)))

    def set_node_label (self, code, **kwargs):
        """ Usage: set-node-label <PROPERTY>

            Options:
                <PROPERTY>  Name of a node property to use as label when
                            displaying graphs. '_id' (default) will use
                            the node's internal identifiers; 'none' will
                            show no label
        """
        self._node_label_property = kwargs["<PROPERTY>"]

    def set_edge_label (self, code, **kwargs):
        """ Usage: set-edge-label <PROPERTY>

            Options:
                <PROPERTY>  Name of a edge property to use as label when
                            displaying graphs. '_type' (default) will use
                            the edge's type; 'none' will show no label
        """
        self._edge_label_property = kwargs["<PROPERTY>"]

    def do_startup_ (self, **kwargs):
        # by default, connects anonymously to http://localhost:7474/db/data/
        self._database = py2neo.Graph()
        self.declare_pre_flight_command(
            "connect-to", self.connect_to)

        self._node_label_property = "_id"
        self.declare_pre_flight_command(
            "set-node-label", self.set_node_label)

        self._edge_label_property = "_type"
        self.declare_pre_flight_command(
            "set-edge-label", self.set_edge_label)

        self.register_renderer(
            renderer.render, renderer.MIME_TYPES)

        self.declare_pre_flight_command(
            "set-layout-program", renderer.set_layout_program)

        self.declare_pre_flight_command(
            "set-output-format", renderer.set_output_format)

        self.declare_pre_flight_command(
            "reset-graph-properties", renderer.reset_graph_properties)
        self.declare_pre_flight_command(
            "set-graph-property", renderer.set_graph_property)

        self.declare_pre_flight_command(
            "reset-node-properties", renderer.reset_node_properties)
        self.declare_pre_flight_command(
            "set-node-property", renderer.set_node_property)

        self.declare_pre_flight_command(
            "reset-edge-properties", renderer.reset_edge_properties)
        self.declare_pre_flight_command(
            "set-edge-property", renderer.set_edge_property)

        self.magic_commands.prefix = '!'

    def do_execute_ (self, code):
        # we remove any comment
        statements = re.sub(re.compile(r"//.*?\n" ), '', code)

        # neo4j doesn't allow multiple statements per transaction;
        # hence we send these statements individually, if any
        statements = re.split(r"(?<!\\);", statements)

        # we remove any empty line
        statements = filter(
            lambda x: x != '', map(lambda x: x.strip(), statements))
        n_statements = len(statements)

        for (statement_n, statement) in enumerate(statements):
            _logger.debug("statement %d/%d: %s" % (
                statement_n+1, n_statements, statement))

            if (n_statements > 1):
                prefix = "statement %d of %d: " % (statement_n+1, n_statements)
            else:
                prefix = ''

            # send a Cypher command to the Neo4j server, then
            # get the results as a py2neo.cypher.RecordList object
            results = self._database.cypher.execute(statement)

            if (len(results) == 0):
                if (0 < statement_n < n_statements):
                    yield '\n'

                yield prefix + "no rows returned"
                continue

            # return the results as a graph, if
            # there is at least one node to show
            g = results.to_subgraph()
            n_nodes, n_edges = g.order, g.size

            if (n_nodes > 0):
                # transform the subgraph object into a Graphviz DOT document
                dot = pydotplus.Dot(graph_type = "digraph")

                for node in g.nodes:
                    node_kwargs = {}

                    if (self._node_label_property == "_id"):
                        node_kwargs["label"] = node.ref

                    elif (self._node_label_property != "none"):
                        try:
                            label = node.properties[self._node_label_property]
                            if (label is not None):
                                node_kwargs["label"] = label
                        except:
                            raise Exception("Unknown node property: %s" % \
                                self._node_label_property)

                    dot.add_node(pydotplus.Node(
                        node.ref,
                        **node_kwargs))

                for edge in g.relationships:
                    edge_kwargs = {}

                    if (self._edge_label_property == "_type"):
                        edge_kwargs["label"] = edge.type

                    elif (self._edge_label_property != "none"):
                        try:
                            label = edge.properties[self._edge_label_property]
                            if (label is not None):
                                edge_kwargs["label"] = label
                        except:
                            raise Exception("Unknown edge property: %s" % \
                                self._edge_label_property)

                    dot.add_edge(pydotplus.Edge(
                        edge.start_node.ref,
                        edge.end_node.ref,
                        **edge_kwargs))

                yield ("text/vnd.graphviz", dot.to_string())
                yield "%s%d %s, %d %s returned" % (prefix,
                    n_nodes, callysto.utils.plural("node", n_nodes),
                    n_edges, callysto.utils.plural("edge", n_edges))

            # if not, return the results as a table
            else:
                header = results.columns
                table = [header]
                for row in results:
                    table.append([row[column] for column in header])

                yield (callysto.MIME_TYPE.CSV_WITH_HEADER, table)
                yield "%s%d %s returned" % (prefix,
                    len(results), callysto.utils.plural("row", len(results)))

if (__name__ == "__main__"):
    Neo4jKernel.launch(debug = True)
