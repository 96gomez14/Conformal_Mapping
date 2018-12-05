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

def all_equal(table, tablelocks):
    '''
    Helper function that simply checks whether,
    around this time, each host has not changed
    its own DV in its personal routing table, since
    another period has elapsed.
    '''
    hosts = table.keys()
    count = 0
    for host in hosts:
        tablelocks[host].acquire()
        if not table[host]['changed']:
            count += 1
        tablelocks[host].release()
    return count == len(hosts)

def print_tables(routing_table, hosts):
    '''
    Prints the contents of each node's DV,
    as this is the thing that they personally
    alter as needed, when they receive possible
    changes from their immediate neighbors.
    '''
    print("The following three-tuples are of the form (destination, distance, next).")
    for host in hosts:
        s = host
        for host2 in hosts:
            s += " (" + host2 + ', ' + str(routing_table[host][host2][0]) + ', ' + str(routing_table[host][host2][1]) + ') '
        print(s)

def copy_DV(dv, dv_lock, host):
    '''
    Creates a deep copy of the calling
    node's personal distance vector, taken
    from its own routing table. This avoids
    the coupled solution of having to pass
    locks for one host's distance vector, to
    different hosts. Furthermore, we can afford
    to do this, because the size of the routing
    tables is constant with the number of hosts.
    '''
    cp_dv = {}
    dv_lock.acquire()
    keys = dv.keys()
    keys.remove('changed')
    for key in keys:
        cp_dv[key] = dv[key]
    dv_lock.release()
    return cp_dv

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
        flock.acquire()
        f = open("weights.txt", "r")
        lines = f.readlines()
        f.close()
        flock.release()
        for line in lines:
            spl = line.split()
            neighbor = None
            if spl[0] == host:
                neighbor = spl[1]
            elif spl[1] == host:
                neighbor = spl[0]
            if neighbor != None:
                DV_lock.acquire()
                if rtable[host][neighbor] > int(spl[2]):
                    rtable[host]['changed'] = True
                    rtable[host][neighbor][0] = int(spl[2])
                    rtable[host][neighbor][1] = neighbor
                DV_lock.release()
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

def riplite(hosts, links):
    '''
    This function is called in the startup
    code for Part C. From here, we start
    each host's server process, which runs
    continuously, and we periodically start
    and end client threads for each node, so
    as to send updates if the weights in the file
    have been changed.
    '''
    file_str = "weights.txt"
    f = open(file_str, "r")
    lines = f.readlines()
    f.close()
    glob_routing_table = {}
    for host in hosts:          # First loop in initialization pseudocode
        glob_routing_table[host] = {}
        for column in hosts:
            glob_routing_table[host][column] = [2**32, None]
        glob_routing_table[host][host] = [0, None]    # Setting the (dist, next) values for each host's path to itself
        glob_routing_table[host]['changed'] = False

    for host in hosts:          # Finishing initialization of global weights
        for line in lines:
            spl = line.split()
            if spl[0] == host:
                glob_routing_table[host][spl[1]] = [int(spl[2]), spl[1]]
            elif spl[1] == host:
                glob_routing_table[host][spl[0]] = [int(spl[2]), spl[0]]

    server_sockets = {}    # Array of sockets, each corresponding to a different node in the network
    serverPort= 64000
    host_ports = {}
    for host in hosts:   # Since these threads all run on the same machine, we
        host_ports[host] = serverPort   # are just varying ports over the hosts
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.bind(('', serverPort))
        serverSocket.listen(1)
        server_sockets[host] = serverSocket
        serverPort += 1

    host_tablelocks = {}
    for host in hosts:
        host_tablelocks[host] = Lock()

    flock = Lock()
    glob_host_ports = {}
    for host in hosts:      # Second loop in initialization pseudocode
        flock.acquire()
        f = open("weights.txt", "r")
        lines = f.readlines()
        f.close()
        flock.release()
        altered_table = False
        personal_routing_table = {}
        personal_routing_table[host] = {}
        for host2 in hosts:
            personal_routing_table[host][host2] = glob_routing_table[host][host2]
        glob_host_ports[host] = {}
        for line in lines:
            spl = line.split()
            neighbor = None
            if spl[0] == host:
                neighbor = spl[1]
            elif spl[1] == host:
                neighbor = spl[0]
            personal_routing_table[neighbor] = {}
            for host2 in hosts:
                personal_routing_table[neighbor][host2] = None
            if neighbor != None:
                glob_host_ports[host][neighbor] = host_ports[neighbor]
        t = Thread(target= server, args=(host, server_sockets[host], personal_routing_table, host_tablelocks[host], glob_host_ports[host], flock))

    for host in hosts:
        t = Thread(target= client, args= (host, glob_host_ports[host], glob_routing_table[host], host_tablelocks[host]))
        t.start()

    start_time = time.time()
    noChangeCount = 0
    while 1:
        curr_time = time.time()
        if curr_time - start_time >= 30 and not all_equal(glob_routing_table, host_tablelocks):
            noChangeCount = 0
            for host in hosts:
                host_tablelocks[host].acquire()
                t = None
                if glob_routing_table[host]['changed']:
                    t = Thread(target= client, args= (host, glob_host_ports[host], glob_routing_table[host], host_tablelocks[host]))
                host_tablelocks[host].release()
                if t != None:
                    t.start()
            start_time = time.time()
        elif curr_time - start_time >= 30:
            noChangeCount += 1
            if noChangeCount == 3:
                print_tables(glob_routing_table, hosts)
                break
            start_time = time.time()

def topology():
    "Create a network."
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)

    info("*** Creating nodes\n")
    net.addStation('sta1', mac='00:00:00:00:00:02', ip='10.0.0.2/8',
                   min_x=10, max_x=200, min_y=10, max_y=200, min_v=5, max_v=10)
    net.addStation('sta2', mac='00:00:00:00:00:03', ip='10.0.0.3/8',
                   min_x=50, max_x=200, min_y=10, max_y=80, min_v=1, max_v=5)
    net.addStation('sta3', mac='00:00:00:00:00:03', ip='10.0.0.4/8',
                   min_x=50, max_x=200, min_y=10, max_y=80, min_v=1, max_v=5)
    net.addStation('sta4', mac='00:00:00:00:00:03', ip='10.0.0.5/8',
                   min_x=10, max_x=200, min_y=10, max_y=80, min_v=1, max_v=5)
    net.addStation('sta5', mac='00:00:00:00:00:03', ip='10.0.0.6/8',
                   min_x=10, max_x=200, min_y=130, max_y=200, min_v=1, max_v=5)
    net.addStation('sta6', mac='00:00:00:00:00:03', ip='10.0.0.7/8',
                   min_x=50, max_x=200, min_y=130, max_y=200, min_v=1, max_v=5)
    net.addStation('sta7', mac='00:00:00:00:00:03', ip='10.0.0.8/8',
                   min_x=50, max_x=200, min_y=130, max_y=200, min_v=1, max_v=5)
    net.addStation('sta8', mac='00:00:00:00:00:03', ip='10.0.0.9/8',
                   min_x=10, max_x=200, min_y=10, max_y=200, min_v=1, max_v=5)

    net.setPropagationModel(model="logDistance", exp=4)

    net.plotGraph(max_x=200, max_y=200)
    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

#    net.plotGraph(max_x=300, max_y=300)

    net.setMobilityModel(time=0, model='RandomWayPoint', 
                        seed=1, ac_method='ssf')
    info("*** Starting network\n")
    net.build()

    info("*** Running CLI\n")
    CLI_wifi(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()
