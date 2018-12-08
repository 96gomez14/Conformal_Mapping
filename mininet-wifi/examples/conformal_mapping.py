#!/usr/bin/python

import sys

from mininet.log import setLogLevel, info
from mn_wifi.link import wmediumd, adhoc
from mn_wifi.cli import CLI_wifi
from mn_wifi.net import Mininet_wifi
from mn_wifi.wmediumdConnector import interference

from socket import *
from threading import Thread, Lock
import time
import ast
import scipy.integrate as integrate
import math

RANGE = 100      # Communication radio range for each node

def distance(p1, p2):
    '''
    Helper method for calculating the
    Euclidean distance between the two
    given points.
    '''
    operand1 = p2[0] - p1[0]
    operand2 = p2[1] - p1[1]
    return math.sqrt((operand1)**2 + (operand2)**2)


def SC_inverse_x(x):
    '''
    Function for computing the derivative of the
    Schwarz-Christoffel inverse for the x-coordinate of
    a given point within our polygon; maps from the
    original network graph to the disk.
    '''
    # The turning angles for my boundary graph's vertices
    Bs = [0.5, 0.5, 0.5, -0.5, -0.5, 0.5, 0.5, 0.5]
    # Coordinates for the set boundary points on our disk
    Zs = [-0.98993, -0.99478, -0.99480, -0.99978, 0.97883, 0.99872, 0.99873, 1.00000]
    prodx = 1
    n = len(Zs)
    for i in range(n):
        negatex = False
        if (x - Zs[i]) < 0:
            negatex = True
        prodx = prodx * math.fabs((x - Zs[i]))**Bs[i]
        if negatex == True:
            prodx = prodx * -1

    return prodx

def SC_inverse_y(y):
    '''
    Function for computing the derivative of the
    Schwarz-Christoffel inverse for the y-coordinate of
    a given point within our polygon; maps from the
    original network graph to the disk.
    '''
    # The turning angles for my boundary graph's vertices
    Bs = [0.5, 0.5, 0.5, -0.5, -0.5, 0.5, 0.5, 0.5]
    # Coordinates for the set boundary points on our disk
    Zs = [0.14155, 0.10202, 0.10184, -0.02078, 0.20466, -0.05063, -0.05041, 0.00000]
    prody = 1
    n = len(Zs)
    for i in range(n):
        negatey = False
        if (y - Zs[i]) < 0:
            negatey = True
        prody = prody * math.fabs((y - Zs[i]))**Bs[i]
        if negatey == True:
            prody = prody * -1

    return prody


def client(closest_neighbor_port, client_socket):
    '''
    Sets up and tears down a TCP connection, over
    which the calling host sends its personal DV
    to its neighbors, in the event that the DV has
    been altered since they last received it.
    '''
    server_name = gethostname()
    client_socket.connect((server_name, closest_neighbor_port))
    client_socket.send("ping")
    client_socket.close()

def server(nodes_dict, node_name, dst_node, server_socket, host_ports):
    w_0 = (3.15, 10.65)     # The approximate centroid of our MANET's polygonal boundary
    node_names = nodes_dict.keys()
    n = len(node_names)
    this_server_socket = server_socket
    this = nodes_dict[node_name]
    #while(1):
    this_pos = this.params['position'][:2]
    dst_pos = dst_node.params["position"][:2]
    dst_circ_pos_x = integrate.quad(lambda x: SC_inverse_x(x), w_0[0], dst_pos[0])[0]
    dst_circ_pos_y = integrate.quad(lambda y: SC_inverse_y(y), w_0[1], dst_pos[1])[0]
    connection_socket, addr = this_server_socket.accept()
    connection_socket.close()
    min_dist = 2**32        # Represents a distance that must be greater than all successive distances
    closest_neighbor_port = None
    while closest_neighbor_port == None:    # It could be that after traversing all nodes, we run into a temporary local minimum
        for i in range(n):
            if node_names[i] != node_name:
                neighbor = nodes_dict[node_names[i]]
                neighbor_pos = neighbor.params["position"][:2]
                if distance(this_pos, neighbor_pos) <= RANGE:       # We use real coordinates for finding in-range neighbors,
                    if neighbor.IP() == dst_node.IP():              # because the nodes must be in range of each other in the
                        print("pong")                               # actual network.
                        return
                    else:
                        neighbor_circ_pos_x = integrate.quad(lambda x: SC_inverse_x(x), w_0[0], neighbor_pos[0])[0]
                        neighbor_circ_pos_y = integrate.quad(lambda y: SC_inverse_y(y), w_0[1], neighbor_pos[1])[0]
                        disk_distance = distance((dst_circ_pos_x, dst_circ_pos_y), (neighbor_circ_pos_x, neighbor_circ_pos_y))
                        if min_dist > disk_distance:
                            min_dist = disk_distance
                            closest_name = node_names[i]
                            closest_neighbor_port = host_ports[closest_name]

    client(closest_neighbor_port, this_server_socket)


def conformal_mapping(src_node, dst_node, nodes_dict):
    '''
    This function is called to start our
    utilization of our conformal mapping.
    '''
    node_names = nodes_dict.keys()
    server_sockets = {}    # Array of sockets, each corresponding to a different node in the network
    serverPort= 42000
    host_ports = {}
    for node_name in node_names:   # Since these threads all run on the same machine, we
        host_ports[node_name] = serverPort   # are just varying ports over the hosts
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.bind(('', serverPort))
        serverSocket.listen(1)
        server_sockets[node_name] = serverSocket
        serverPort += 1

    for node_name in node_names:
        t = Thread(target= server, args=(nodes_dict, node_name, dst_node, server_sockets[node_name], host_ports))
        t.start()

    n = len(node_names)
    closest_neighbor_port = None
    min_dist = 2**32

    # TODO  Make a helper function for the below code: it is identical in two different spots
    w_0 = (3.15, 10.65)
    src_pos = src_node.params["position"][:2]
    dst_pos = dst_node.params["position"][:2]
    dst_circ_pos_x = integrate.quad(lambda x: SC_inverse_x(x), w_0[0], dst_pos[0])[0]
    dst_circ_pos_y = integrate.quad(lambda y: SC_inverse_y(y), w_0[1], dst_pos[1])[0]
    while closest_neighbor_port == None:
        for i in range(n):
            if node_names[i] != src_node.name:
                neighbor = nodes_dict[node_names[i]]
                neighbor_pos = neighbor.params["position"][:2]
                if distance(src_pos, neighbor_pos) <= RANGE:
                    if neighbor.IP() == dst_node.IP():
                        print("pong")
                        return
                    else:
                        neighbor_circ_pos_x = integrate.quad(lambda x: SC_inverse_x(x), w_0[0], neighbor_pos[0])[0]
                        neighbor_circ_pos_y = integrate.quad(lambda y: SC_inverse_y(y), w_0[1], neighbor_pos[1])[0]
                        disk_distance = distance((dst_circ_pos_x, dst_circ_pos_y), (neighbor_circ_pos_x, neighbor_circ_pos_y))
                        if min_dist > disk_distance:
                            min_dist = disk_distance
                            closest_name = node_names[i]
                            closest_neighbor_port = host_ports[closest_name]

    src_socket = server_sockets[src_node.name]
    t = Thread(target= client, args= (closest_neighbor_port, src_socket))
    t.start()


def topology():
    "Create a network."
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)

    info("*** Creating nodes\n")
    net.addStation('sta1', mac='00:00:00:00:00:02', ip='10.0.0.2/8',
                   min_x=10, max_x=200, min_y=10, max_y=200, min_v=5, max_v=10)
    net.addStation('sta2', mac='00:00:00:00:00:03', ip='10.0.0.3/8',
                   min_x=50, max_x=200, min_y=10, max_y=80, min_v=1, max_v=5)
    net.addStation('sta3', mac='00:00:00:00:00:04', ip='10.0.0.4/8',
                   min_x=50, max_x=200, min_y=10, max_y=80, min_v=1, max_v=5)
    net.addStation('sta4', mac='00:00:00:00:00:05', ip='10.0.0.5/8',
                   min_x=10, max_x=200, min_y=10, max_y=80, min_v=1, max_v=5)
    net.addStation('sta5', mac='00:00:00:00:00:06', ip='10.0.0.6/8',
                   min_x=10, max_x=200, min_y=130, max_y=200, min_v=1, max_v=5)
    net.addStation('sta6', mac='00:00:00:00:00:07', ip='10.0.0.7/8',
                   min_x=50, max_x=200, min_y=130, max_y=200, min_v=1, max_v=5)
    net.addStation('sta7', mac='00:00:00:00:00:08', ip='10.0.0.8/8',
                   min_x=50, max_x=200, min_y=130, max_y=200, min_v=1, max_v=5)
    net.addStation('sta8', mac='00:00:00:00:00:09', ip='10.0.0.9/8',
                   min_x=10, max_x=200, min_y=10, max_y=200, min_v=1, max_v=5)

    net.setPropagationModel(model="logDistance", exp=4)

    net.plotGraph(max_x=300, max_y=300)

    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    net.setMobilityModel(time=0, model='RandomWayPoint',
                        seed=1, ac_method='ssf')
    info("*** Starting network\n")
    net.build()

    src_node = net.nameToNode["sta2"]        # source node
    dst_node = net.nameToNode["sta7"]   # destination node
    conformal_mapping(src_node, dst_node, net.nameToNode)

    info("*** Running CLI\n")
    CLI_wifi(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()
