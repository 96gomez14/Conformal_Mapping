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

def distance(p1, p2):
    '''
    Helper method for calculating the
    Euclidean distance between the two
    given points.
    '''
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)


def client(host, neighbor_ports, DV, DV_lock):
    '''
    Sets up and tears down a TCP connection, over
    which the calling host sends its personal DV
    to its neighbors, in the event that the DV has
    been altered since they last received it.
    '''
    neighbors = neighbor_ports.keys()
    cp_dv = copy_DV(DV, DV_lock, host)
    msg = host + " " + str(cp_dv)
    for neighbor in neighbors:
        serverName = gethostname()
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect((serverName, neighbor_ports[neighbor]))
        clientSocket.send(msg)
        clientSocket.close()

def server(host, serverSocket, rtable, DV_lock, personal_host_ports, f_lock):
    while(1):
        connectionSocket, addr = serverSocket.accept()
        n_DVstr = connectionSocket.recv(512)    #Should cover the max size of data transported over the socket
        connectionSocket.close()
        n_DV = ast.literal_eval(n_DVstr[3:])    # Converts the string back to dict
        sending_host = n_DVstr[:2]   # The sending host's name in the message
        rtable[sending_host] = n_DV
        nkeys = n_DV.keys()
        DV_lock.acquire()
        for key in nkeys:
            if n_DV[key][0] < rtable[host][key][0]:
                rtable[host]['changed'] = True  # Lets the corresponding client
                rtable[host][key][0] = n_DV[key][0]  # socket thread for this host
                rtable[host][key][1] = sending_host
        DV_lock.release()                   # know to send out to neighbors

def SC_inverse(w, Zs, Bs):
    '''
    Function for computing the Schwarz-Christoffel inverse
    for a given point within our polygon; maps from the
    original network graph to the disk.
    '''
    prodx = 1
    prody = 1
    n = len(Zs)
    for i in range(n):
        prodx = prodx * (w[0] - zs[i][0])**bs[i]
        prody = prody * (w[1] - zs[i][1])**bs[i]

    return (prodx, prody)


def conformal_mapping(nodes_dict):
    '''
    This function is called to start our
    utilization of our conformal mapping.
    '''
    tangent_angles = [0.5, 0.5, 0.5, -0.5, -0.5, 0.5, 0.5, 0.5]
    circle_vertices = [(-0.98993, 0.14155),(-0.99478, 0.10202), (-0.99480, 0.10184), (-0.99978, - 0.02078), (0.97883, -0.20466), (0.99872, -0.05063), (0.99873, -0.05041), (1.00000, 0.00000)]

    node_names = nodes_dict.keys()
    server_sockets = {}    # Array of sockets, each corresponding to a different node in the network
    serverPort= 64000
    host_ports = {}
    for node_name in node_names:   # Since these threads all run on the same machine, we
        host_ports[node_name] = serverPort   # are just varying ports over the hosts
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.bind(('', serverPort))
        serverSocket.listen(1)
        server_sockets[node_name] = serverSocket
        serverPort += 1

    for node_name in node_names:
        t = Thread(target= server, args=(nodes_dict, node_name, server_sockets[node_name], tangent_angles, circle_vertices))
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

    src = net.nameToNode["sta2"]        # source node
    dst = net.nameToNode["sta7"].IP()   # destination node IP address
    #conformal_mapping(net.nameToNode)

    info("*** Running CLI\n")
    CLI_wifi(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()
