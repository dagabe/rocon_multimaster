#!/usr/bin/env python
#
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_multimaster/master/rocon_gateway_graph/LICENSE
#
'''
  This code does not effect the runtime of gateways at all - it is used for
  debugging and monitoring purposes only.
'''
##############################################################################
# Imports
##############################################################################

import roslib
roslib.load_manifest('rocon_gateway')
import rospy
import gateway_msgs.srv
from master_api import LocalMaster
import rosgraph
from rosgraph.impl.graph import Edge, EdgeList

##############################################################################
# Graph
##############################################################################


class Graph(object):
    '''
    Utility class for polling statistics from a running gateway-hub network.
    '''

    def __init__(self):
        '''
        Creates the polling topics necessary for updating statistics
        about the running gateway-hub network.
        '''
        self._last_update = 0
        self._gateway_namespace = None
        self._local_gateway = None
        self._remote_gateways = None
        self.gateway_nodes = []  # Gateway nodes
        self.flipped_nodes = []  # Flip connection nodes (i.e. topic name)
        self.pulled_nodes = []
        self.pulled_edges = []  # Gateway-Topic edges
        self.gateway_edges = []  # Gateway-Gateway edges
        self.flipped_edges = []  # All unconnected node-topics or topic-nodes

        # Rubbish to clear out once rocon_gateway_graph is integrated
        self.bad_nodes = []

        if self._resolve_gateway_namespace():
            self.configure()

    def configure(self):
        self._gateway_info = rospy.ServiceProxy(self.gateway_namespace + '/gateway_info', gateway_msgs.srv.GatewayInfo)
        self._remote_gateway_info = rospy.ServiceProxy(self.gateway_namespace + '/remote_gateway_info', gateway_msgs.srv.RemoteGatewayInfo)

    def update(self):
        if not self._resolve_gateway_namespace():
            return
        req = gateway_msgs.srv.GatewayInfoRequest()
        self._local_gateway = self._gateway_info(req)
        req = gateway_msgs.srv.RemoteGatewayInfoRequest()
        req.gateways = []
        self._remote_gateways = self._remote_gateway_info(req).gateways
        self._last_update = rospy.get_rostime()
        # Gateways
        self.gateway_nodes.append(self._local_gateway.name)
        self.gateway_nodes.extend([remote_gateway.name for remote_gateway in self._remote_gateways])
        # Edges
        self.pulled_edges = EdgeList()
        self.gateway_edges = EdgeList()
        self.pulled_edges = EdgeList()
        self.flipped_edges = EdgeList()
        # Check local gateway
        for remote_rule in self._local_gateway.flipped_connections:
            self.gateway_edges.add(Edge(self._local_gateway.name, remote_rule.gateway))
            # this adds a bloody magic space, to help disambiguate node names from topic names
            connection_id = rosgraph.impl.graph.topic_node(remote_rule.rule.name + '-' + remote_rule.rule.type)
            self.flipped_nodes.append(connection_id)
            self.flipped_edges.add(Edge(self._local_gateway.name, connection_id))
            self.flipped_edges.add(Edge(connection_id, remote_rule.gateway))
        for remote_rule in self._local_gateway.pulled_connections:
            connection_id = rosgraph.impl.graph.topic_node(remote_rule.rule.name + '-' + remote_rule.rule.type)
            self.pulled_nodes.append(connection_id)
            self.pulled_edges.add(Edge(self._local_gateway.name, connection_id))
            self.pulled_edges.add(Edge(connection_id, remote_rule.gateway))
        for rule in self._local_gateway.public_interface:
            print "pulled edge: %s->%s" % (self._local_gateway.name, connection_id)
            connection_id = rosgraph.impl.graph.topic_node(rule.name + '-' + rule.type)
            self.pulled_nodes.append(connection_id)
            self.pulled_edges.add(Edge(self._local_gateway.name, connection_id))
        # Check remote gateways
        # TODO add flipped and pulled here.
        for remote_gateway in self._remote_gateways:
            for remote_rule in remote_gateway.flipped_interface:
                connection_id = rosgraph.impl.graph.topic_node(remote_rule.rule.name + '-' + remote_rule.rule.type)
                self.flipped_nodes.append(connection_id)
                self.gateway_edges.add(Edge(remote_gateway.name, connection_id))
                self.gateway_edges.add(Edge(connection_id, remote_rule.gateway))
            for remote_rule in remote_gateway.pulled_interface:
                connection_id = rosgraph.impl.graph.topic_node(remote_rule.rule.name + '-' + remote_rule.rule.type)
                self.pulled_nodes.append(connection_id)
                self.pulled_edges.add(Edge(remote_rule.gateway, connection_id))
                self.pulled_edges.add(Edge(connection_id, remote_gateway.name))


    def _resolve_gateway_namespace(self):
        '''
          Checks if the gateway namespace was found and if not
          attempts to resolve it.
        '''
        if self._gateway_namespace:
            return
        master = LocalMaster()
        self.gateway_namespace = master.findGatewayNamespace()
        if not self.gateway_namespace:
            rospy.logerr("Gateway Graph: could not find a local gateway - did you start it?")
        return self.gateway_namespace
