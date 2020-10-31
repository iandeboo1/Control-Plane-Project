import queue
import threading
import pickle
from rprint import print


## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)
    
    ##get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None
        
    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)
            
        
## Implements a network layer packet.
class NetworkPacket:
    ## packet encoding lengths 
    dst_S_length = 5
    prot_S_length = 1
    
    ##@param dst: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst, prot_S, data_S):
        self.dst = dst
        self.data_S = data_S
        self.prot_S = prot_S
        
    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()
        
    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise('%s: unknown prot_S option: %s' %(self, self.prot_S))
        byte_S += self.data_S
        return byte_S
    
    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0 : NetworkPacket.dst_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.dst_S_length : NetworkPacket.dst_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise('%s: unknown prot_S field: %s' %(self, prot_S))
        data_S = byte_S[NetworkPacket.dst_S_length + NetworkPacket.prot_S_length : ]        
        return self(dst, prot_S, data_S)
    

    

## Implements a network host for receiving and transmitting data
class Host:
    
    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False #for thread termination
    
    ## called when printing the object
    def __str__(self):
        return self.addr
       
    ## create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst, data_S):
        p = NetworkPacket(dst, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out') #send packets always enqueued successfully
        
    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))
       
    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return
        


## Implements a multi-interface router
class Router:
    
    ##@param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        #save neighbors and interfaces on which we connect to them
        self.cost_D = cost_D    # {neighbor: {interface: cost}}
        #TODO: set up the routing table for connected hosts

        self.rt_tbl_D = {}      # {destination: {router: cost}}
        self.fwd_tbl_D = {}     # {destination: interface}
        for neighbor in cost_D:
            for interface in cost_D[neighbor]:
                self.rt_tbl_D[neighbor] = {self.name: cost_D[neighbor][interface]}
                # initialize forwarding table with neighbors
                self.fwd_tbl_D[neighbor] = interface
        # add self to routing table
        self.rt_tbl_D[self.name] = {self.name: 0}
        print('%s: Initialized routing table' % self)
        self.print_routes()

        
    ## Print routing table
    def print_routes(self):
        #TODO: print the routes as a two dimensional table

        destinations_L = []
        routers_L = []
        sample_inner_dict = None    # used to determine known routers

        for destination in self.rt_tbl_D:
            sample_inner_dict = self.rt_tbl_D[destination]
            destinations_L.append(destination)
        for router in sample_inner_dict:
            routers_L.append(router)
        # print header row
        for i in range(len(destinations_L) + 1):
            if i == 0:
                print('╒══════', end='')
            elif i == (len(destinations_L)):
                print('╤══════╕')
            else:
                print('╤══════',end='')
        print('| ' + self.name + '   |', end='')
        for destination in self.rt_tbl_D:
            print('   ' + destination + ' |', end='')
        for i in range(len(destinations_L) + 1):
            if i == 0:
                print('\n╞══════', end='')
            elif i == (len(destinations_L)):
                print('╪══════╡')
            else:
                print('╪══════',end='')
        # print body rows
        for i in range(len(routers_L)):
            # print row header
            print('| ' + routers_L[i] + '   |', end='')
            for j in range(len(destinations_L)):
                # print cost values
                print('    ' + str(self.rt_tbl_D[destinations_L[j]][routers_L[i]]) + ' |', end='')
                # {'H2': {'RB': 3, 'RA': 0}, 'RA': {'RB': 1}, 'RA': 0, 'RB': {'RB': 0, 'RA': 1}, 'H1': {'RB': 0, 'RA': 1}
            if (i != (len(routers_L)) - 1):
                for i in range(len(destinations_L) + 1):
                    if i == 0:
                        print('\n├──────', end='')
                    elif i == (len(destinations_L)):
                        print('┼──────┤')
                    else:
                        print('┼──────', end='')
            else:
                for i in range(len(destinations_L) + 1):
                    if i == 0:
                        print('\n╘══════', end='')
                    elif i == (len(destinations_L)):
                        print('╧══════╛')
                    else:
                        print('╧══════', end='')


    ## called when printing the object
    def __str__(self):
        return self.name


    ## look through the content of incoming interfaces and 
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            #get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            #if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p,i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))
            

    ## forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        try:
            # TODO: Here you will need to implement a lookup into the 
            # forwarding table to find the appropriate outgoing interface
            # for now we assume the outgoing interface is 1

            interface = self.fwd_tbl_D[p.dst]
            self.intf_L[interface].put(p.to_byte_S(), 'out', True)
            # I removed the 'to interface %d' portion of the below print because I could find no way to
            # determine the interface it would be arriving on at the next router/host
            print('%s: forwarding packet "%s" on interface %d' % \
                (self, p, interface))
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self):
        # TODO: Send out a routing table update

        #create a routing table update packet
        routing_table_bytes = pickle.dumps(self.rt_tbl_D)
        p = NetworkPacket(0, 'control', routing_table_bytes.decode('latin1'))

        for neighbor in self.cost_D:
            if (neighbor.startswith('R')):
                # sends updates to all neighbors that are routers
                for interface in self.cost_D[neighbor]:
                    try:
                        print('%s: sending routing update "%s" from interface %d' % (self, p, int(interface)))
                        self.intf_L[int(interface)].put(p.to_byte_S(), 'out', True)
                    except queue.Full:
                        print('%s: packet "%s" lost on interface %d' % (self, p, int(interface)))
                        pass


    ## forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        #TODO: add logic to update the routing tables and
        # possibly send out routing updates

        print('%s: Received routing update %s from interface %d' % (self, p, i))
        routing_table_msg = pickle.loads(p.data_S.encode('latin1'))
        # examine incoming routing table
        for destination in routing_table_msg:
            # find unknown destinations
            if destination not in self.rt_tbl_D.keys():
                self.rt_tbl_D[destination] = {self.name: 0}
                self.fwd_tbl_D[destination] = 99        # placeholder value until next-hop is known
            # examine known routers in incoming routing table
            for router in routing_table_msg[destination]:
                if router in self.cost_D.keys():
                    # router is a neighbor of self
                    self.rt_tbl_D[destination][router] = routing_table_msg[destination][router]
                    for rt_tbl_destination in self.rt_tbl_D:
                        if rt_tbl_destination not in routing_table_msg.keys():
                            self.rt_tbl_D[rt_tbl_destination][router] = 0
        # Bellman-Ford equation
        for destination in self.rt_tbl_D:
            if destination != self.name:
                prev_value = self.rt_tbl_D[destination][self.name]
                min_cost = self.rt_tbl_D[destination][self.name]
                min_cost_next_hop = None
                for router in self.rt_tbl_D[destination]:
                    if router != self.name and self.rt_tbl_D[destination][router] != 0:
                        # look at every other known router in network
                        cost_to_dest = self.rt_tbl_D[router][self.name] + self.rt_tbl_D[destination][router]
                        if min_cost == 0 or cost_to_dest < min_cost:
                            min_cost = cost_to_dest
                            min_cost_next_hop = router
                if min_cost != prev_value:
                    # cost value has changed
                    self.rt_tbl_D[destination][self.name] = min_cost
                    for interface in self.cost_D[min_cost_next_hop]:
                        self.fwd_tbl_D[destination] = interface
                        break
                    self.send_routes()


    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return 