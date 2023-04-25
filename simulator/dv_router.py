"""
Your awesome Distance Vector router for CS 168

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

import sim.api as api
from cs168.dv import RoutePacket, \
    Table, TableEntry, \
    DVRouterBase, Ports, \
    FOREVER, INFINITY


class DVRouter(DVRouterBase):
    # A route should time out after this interval
    ROUTE_TTL = 15

    # Dead entries should time out after this interval
    GARBAGE_TTL = 10

    # -----------------------------------------------
    # stage 6 and 7:At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # stage 9:Determines if you send poison for expired routes
    POISON_EXPIRED = False

    # stage 10:Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # stage 10:Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = False

    # stage 10用，port到RoutePacket(host，latency）,记录从端口port发出的最新路由表，
    # 一定注意port指的是从那个端口发的RoutePacket，不是指路由表里指出下一跳的端口
    record = {}

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (self.SPLIT_HORIZON and self.POISON_REVERSE), \
            "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        # 主要有两个函数get_all_ports：获得该路由器的所有端口；get_latency(port):从该端口到直接相连主机的距离
        self.ports = Ports()

        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self

        self.record = {}

    # 往该路由器的路由表中添加一项，在主机和该路由器连接时和handle_link_up一起被调用
    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(
        ), "Link should be up, but is not."

        # TODO: fill this in!
        t = self.table
        Latency = self.ports.get_latency(port)
        t[host] = TableEntry(dst=host, port=port, latency=Latency, expire_time=FOREVER)

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        # TODO: fill this in!
        t = self.table
        flag = 0
        dst_port = 0
        # 遍历self的路由表，找是否有packet的dst,并且能到达（latency<INFINITY)
        for host, entry in t.items():
            if (host == packet.dst and entry.latency < INFINITY):
                flag = 1
                dst_port = entry.port
        if (flag == 1):
            self.send(packet, dst_port, False)  # 最后一项为false表示非泛洪，只发给一个端口;否则port那里是个list

    # 为实现stage 10新增的函数，判断这个RoutePacket是否被更新或没发过
    def is_new(self, port, RoutePacket):
        r = self.record
        host = RoutePacket.destination
        latency = RoutePacket.latency
        if ((port, host) in r.keys() and r[(port, host)] == latency):
            return False
        else:
            return True

    # 为实现stage 10新增的函数,维护record
    def update_record(self, port, RoutePacket):
        r = self.record
        host = RoutePacket.destination
        latency = RoutePacket.latency
        if (self.is_new(port, RoutePacket)):  # 需要更新或增项
            r[(port, host)] = latency

    # 当TIMER_INTERVAL到了或其他，会定期调用这个函数（force=TRUE)
    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        ##############################  分割线以下是stage6~10要做的   ##############################
        stage 6:当self.SPLIT_HORIZON==true,要实现水平分割：
                If you are using a route to destination D through neighbor N, don‘t advertise destination D to neighbor N

        stage 7:当self.self.POISON_REVERSE==true,要实现毒性逆转：
                If you are using a route to destination D through neighbor N, advertise destination D to neighbor N as unreachable
                水平分割和毒性逆转不会同时实现，这俩都是防环路（让路由器不收到从自己发送出去的循环路由而产生错误路由）的，毒性逆转更强

        stage 10:核心思想是根据网络的动态改变实现更新，而不仅仅依赖定时器定期更新
                在其他函数中一旦有更新，就调用force为False的send_routes
                这里要实现force为False的send_routes

        """
        # TODO: fill this in!
        t = self.table
        packet_list = []  # 所有要发的路由表（准确的说，是RoutePacket）
        port_list = []  # 所有要转发的端口
        map = {}  # 水平分割和毒性逆转用，从host到port的字典,这个port就是路由表里对应下一跳的port

        # stage 10用，(port,host)到latency,记录从端口port发出的最新的路由表，
        # 逻辑上应该是port到（host,latency),把host放到键值是为了方便实现
        # 一定注意port指的是从那个端口发的RoutePacket，不是指路由表里指出下一跳的端口
        r = self.record

        for host, entry in t.items():
            packet_list.append(RoutePacket(host, entry.latency))
            map[host] = entry.port

        if (single_port == None):  # 往所有端口发
            port_list = self.ports.get_all_ports()
        else:  # 只用往single_port发
            port_list.append(single_port)

        for port in port_list:
            for item in packet_list:
                pport = map[item.destination]
                # 毒性逆转：如果要通过port到host，把那个host的路由项设成INDINITY发给这个port
                if (self.POISON_REVERSE and port == pport):
                    tmp = RoutePacket(item.destination, INFINITY)
                    if (force == True):
                        self.send(tmp, port, False)
                    elif (self.is_new(port, tmp)):
                        self.send(tmp, port, False)
                    self.update_record(port, tmp)

                # 水平分割：如果要通过port到host,那个host的路由项不要发给这个port
                elif (self.SPLIT_HORIZON and port == pport):
                    pass

                else:
                    if (force == True):
                        self.send(item, port, False)
                    elif (self.is_new(port, item)):
                        self.send(item, port, False)
                    self.update_record(port, item)

    def expire_routes(self):
        """
        Clears out expired routes from table.
        #####################################################
        stage 9:Poisoning Expired Routes，目的是配合毒性逆转
        当self.POISON_EXPIRED==true,把过期无效的路由的latency设为无穷，同时让它在路由表里再呆一会，方便毒性传播
        """
        # TODO: fill this in!
        t = self.table
        if (self.POISON_EXPIRED):  # stage 9的要求
            for host, entry in t.items():
                if (api.current_time() >= entry.expire_time and entry.expire_time < FOREVER):
                    t[host] = TableEntry(dst=host, port=entry.port, latency=INFINITY,
                                         expire_time=api.current_time() + self.ROUTE_TTL)


        else:  # 否则，过期的直接删除
            to_del = []  # 字典不能在遍历时删除，所以先记录下所有要删表项的host
            for host, entry in t.items():
                if (api.current_time() >= entry.expire_time and entry.expire_time < FOREVER):
                    to_del.append(host)

            for i in to_del:
                del t[i]

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        计算以当前邻居作为下一跳的这些目的地的延迟，如果延迟降低，则直接选择；
        如果延迟增加了或不变，只更新原来以当前邻居为下一跳的目的地的延迟。
        注意TableEnrty is immutable,每次更新要新建一个，不能直接改
        #################################################################################
        stage 8:Counting to Infinity
        如果有毒广告(延迟无穷大)与当前路由的目的地和端口匹配，则将entry 的latency设为无穷，且不要recharge the timer
        即，如果原来通过当前邻居可达的目的地在检查当前邻居路由表之后变得不可达了，则将这个目的地记为不可达。

        stage 10:必要时调用send_routes
        """
        # TODO: fill this in!
        new_latency = route_latency + self.ports.get_latency(port)
        t = self.table
        flag = 0  # 是否更新
        poison = 0  # stage 8用
        expire_time = 0  # stage 8 用
        if route_dst in t:
            entry = t[route_dst]
            if (new_latency < entry.latency):
                flag = 1
            elif (entry.port == port):
                flag = 1
                if (route_latency >= INFINITY):
                    poison = 1
                    expire_time = entry.expire_time
        else:  # 路由表里没有这项，需要增加这项
            flag = 1

        if (flag):
            if (poison):
                t[route_dst] = TableEntry(dst=route_dst, port=port, latency=INFINITY,
                                          expire_time=expire_time)
            else:
                t[route_dst] = TableEntry(dst=route_dst, port=port, latency=new_latency,
                                          expire_time=api.current_time() + self.ROUTE_TTL)

        # stage 10:因为处理完RoutePacket后路由表可能更新，末尾加上这句，有更新了立刻发RoutePacket
        self.send_routes(False, None)

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.
        连接建立时被调用
        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        ####################################################################
        stage 10:当SEND_ON_LINK_UP==true,
        调用send_routes给新建连接的那个邻居发自己所有的路由表，方便新邻居赶紧跟上
        """
        self.ports.add_port(port, latency)

        # TODO: fill in the rest!
        if (self.SEND_ON_LINK_UP):
            self.send_routes(True, port)

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router does down.

        :param port: the port number used by the link.
        :returns: nothing.
        #####################################################################
        stage 10:当self.POISON_ON_LINK_DOWN==true
        连接释放会导致路由变化，先把会用到port的所有路由改为无穷，再调用send_routes给所有端口发更新为无穷的路由项
        remove any routes that go through that link -and poison and immediately send any routes that need to be updated
        """
        self.ports.remove_port(port)
        # TODO: fill this in!
        t = self.table
        if (self.POISON_ON_LINK_DOWN):
            for host, entry in t.items():
                if (entry.port == port):
                    t[host] = TableEntry(dst=host, port=entry.port, latency=INFINITY,
                                         expire_time=api.current_time() + self.ROUTE_TTL)
            self.send_routes(False, None)

    # Feel free to add any helper methods!
