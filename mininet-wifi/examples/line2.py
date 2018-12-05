#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Controller,OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

def topology():

    net = Mininet( controller=Controller, link=TCLink, switch=OVSKernelSwitch )

    print "*** Creating nodes"
    h1 = net.addHost( 'h1', mac='00:00:00:00:00:01', ip='10.0.0.1/8' )
    sta1 = net.addStation( 'sta1', mac='00:00:00:00:00:02', ip='10.0.0.2/8', range='20' )
    ap1 = net.addBaseStation( 'ap1', ssid= 'ap1-ssid', mode= 'g', channel= '1', position='30,50,0', range='30' )
    ap2 = net.addBaseStation( 'ap2', ssid= 'ap2-ssid', mode= 'g', channel= '1', position='90,50,0', range='30' )
    ap3 = net.addBaseStation( 'ap3', ssid= 'ap3-ssid', mode= 'g', channel= '1', position='130,50,0', range='30' )
    c1 = net.addController( 'c1', controller=Controller )

    print "*** Associating and Creating links"
    net.addLink(ap1, h1)
    net.addLink(ap1, ap2)
    net.addLink(ap2, ap3)

    print "*** Starting network"
    net.build()
    c1.start()
    ap1.start( [c1] )
    ap2.start( [c1] )
    ap3.start( [c1] )

    net.plotGraph(max_x=160, max_y=160)

    net.startMobility(startTime=0, AC='ssf')
    net.mobility('sta1', 'start', time=20, position='1,50,0')
    net.mobility('sta1', 'stop', time=79, position='159,50,0')
    net.stopMobility(stopTime=80)

    print "*** Running CLI"
    CLI( net )

    print "*** Stopping network"
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    topology()
