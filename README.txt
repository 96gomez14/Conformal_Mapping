My code is held at Conformal_Mapping/mininet-wifi/mn_wifi/examples/conformal_mapping.py.

In my code, I call topology(), to create the topology of my wireless network, such that each of my MANET's eight wireless nodes are constrained to certain subdomains. That is, they have set boundaries for how far vertically and horizonatally, even within the entire C-shaped domain. 

Among my eight nodes, I set one to be the source and one to be the destination of my routing. Even though I do not explicitly set the position for my nodes, I pick the node constrained to the top half of the domain (sta2) to be the source, and the node constrained to the bottom of the domain to be the destination (sta7).

Simply run 
		sudo python conformal_mapping.py 
