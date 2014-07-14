# encoding: utf-8
from collections import defaultdict
import drawing
from drawing import TILE_SIZE
import utils
import pyglet
from pyglet.window import key, mouse

mouse.x = 0
mouse.y = 0
resource_types = {0: "goods"}


class Trader(object):
    def __init__(self, id, x, y, produces, consumes):
        self.id, self.x, self.y, self.produces, self.consumes = id, x, y, produces, consumes
        self.connections = []
        self.delete = False

    def update(self, dt):
        for connection in self.connections:
            for type, rate in self.produces.items():
                connection.supplyResource(self, type, rate * dt / len(self.connections))

    def draw(self):
        drawing.Trader_draw(resource_types, self.x, self.y, self.produces, self.consumes)


class Node(object):
    type = object()

    def __init__(self, id, x, y):
        self.id, self.x, self.y = id, x, y
        self.nbors = []

    def draw(self):
        drawing.Node_draw(self.x, self.y)

    def isBusy(self):
        return any(loop.graph.getEdge(self, nbor).isBusy() for nbor in self.nbors)

    def __repr__(self):
        return str(self.id)


class Station(Node):
    type = object()

    def __init__(self, id, x, y):
        super(Station, self).__init__(id, x, y)
        self.resources = defaultdict(lambda: defaultdict(lambda: 0))
        self.connections = []
        self.reach = 5

    def draw(self):
        drawing.Station_draw(resource_types, self.x, self.y, self.resources)

    def supplyResource(self, source, type, amount):
        self.resources[source][type] += amount

    def loadResource(self, type, amount):
        for source, resources in self.resources.items():
            if source is None:
                continue
            available = resources.get(type, 0)
            load = min(available, amount)
            resources[type] -= load
            return load
        return 0

    def unloadResource(self, type, amount):
        self.supplyResource(None, type, amount)

    def acceptsResource(self, type):
        return any(type in connection.consumes for connection in self.connections)


class Signal(Node):
    type = object()

    def __init__(self, id, x, y, nw, se):
        super(Signal, self).__init__(id, x, y)
        self.nw_node, self.se_node = nw, se
        self.nw = self.se = True

    def __cmp__(self, other):
        return 1 if (self.x, self.y) > (other.x, other.y) else -1

    def __eq__(self, other):
        return self is other

    def toggleDirection(self):
        if self.nw is not None and self.se is not None:
            self.se = None
        elif self.se is None:
            self.se, self.nw = True, None
        else:
            self.nw = self.se = True

    def draw(self):
        drawing.Signal_draw(self.x, self.y, self.nw, self.se, self.nw_node, self.se_node)


class SoberBoy:
    def __init__(self, graph):
        self.graph = graph

    class DataItem:
        def __init__(self, parent, g, h):
            self.parent = parent
            self.g = g
            self.h = h

    def getPath(self, train):
        if not train.end and train.destination is train.start:
            return []
        if train.end is train.destination:
            return [train.end]
        node_data = {train.end: self.DataItem(None, 0, 0)}
        open_list = [train.end]
        closed_list = []
        current_node = train.end
        last_node = train.start  # For one-way rule
        while True:
            for nbor in current_node.nbors:
                if nbor is train.destination:
                    path = [nbor]
                    node = current_node
                    while node is not train.end:
                        path.append(node)
                        node = node_data[node].parent
                    return list(reversed(path))

                if nbor is last_node or nbor in closed_list:  # Enforce one-way rule (nbor is last_node)
                    continue

                edge = self.graph.getEdge(current_node, nbor)
                if nbor in open_list:
                    g = node_data[current_node].g + edge.length
                    if g < node_data[nbor].g:
                        node_data[nbor].g = g
                        node_data[nbor].parent = current_node
                else:
                    node_data[nbor] = self.DataItem(current_node,
                                                    node_data[current_node].g + edge.length,
                                                    utils.getDistance((train.destination.x, train.destination.y),
                                                                      (nbor.x, nbor.y)))
                open_list.append(nbor)

            open_list.remove(current_node)
            closed_list.append(current_node)
            last_node = current_node

            if not open_list:
                return []

            current_node = sorted([(node_data[node].g + node_data[node].h, node) for node in open_list],
                                  key=lambda x: x[0], reverse=True)[-1][1]


class Edge:
    def __init__(self, lnode, hnode):
        self.lnode, self.hnode = lnode, hnode
        self.length = utils.getNodeDistance(lnode, hnode)
        self.busy = []

    def draw(self):
        drawing.Edge_draw(self.lnode, self.hnode, self.isBusy())

    def isBusy(self):  # Is there a train/wagon on this edge
        return bool(self.busy)

    def isRouteBusy(self):  # Is there a train/wagon on any edge connected by signals
        if self.busy:
            return True
        for last_node, node in ((self.lnode, self.hnode), (self.hnode, self.lnode)):
            if node.type is Signal.type:
                while True:
                    remote_end = node.nw_node if node.nw_node is not last_node else node.se_node
                    if loop.graph.getEdge(node, remote_end).isBusy():
                        return True
                    if remote_end.type is Signal.type:
                        last_node, node = node, remote_end
                    else:
                        break
        return False


class Graph:
    def __init__(self):
        self.nodes = []
        self.edges = {}
        self.next_node_id = 0
        self.dirty = False

    def createNode(self, x, y, cls=None, args=None, kwargs=None):
        self.dirty = True

        cls = Node if cls is None else cls
        args = [] if args is None else args
        kwargs = {} if kwargs is None else kwargs

        node = cls(self.next_node_id, x, y, *args, **kwargs)
        self.next_node_id += 1
        self.nodes.append(node)
        if node.type is Station.type:
            loop.stations_created.append(node)
        return node

    def connectNodes(self, from_, to):
        if from_ is to:
            raise Exception("Cannot connect to self!")

        self.dirty = True
        if to not in from_.nbors:
            from_.nbors.append(to)
        if from_ not in to.nbors:
            to.nbors.append(from_)

        # Update signals nw/se_node
        if from_.type is Signal.type:
            if from_ > to:  # Uses __cmp__
                from_.nw_node = to
            else:
                from_.se_node = to

        if to.type is Signal.type:
            if to > from_:  # Uses __cmp
                to.nw_node = from_
            else:
                to.se_node = from_

        n_edge = (from_, to) if from_.id < to.id else (to, from_)
        if not n_edge in self.edges:
            self.edges[n_edge] = Edge(*n_edge)

    def insertNode(self, point, from_, to, type=Node.type):
        self.dirty = True
        pair = (from_, to) if from_.id < to.id else (to, from_)
        del self.edges[pair]
        if to in from_.nbors:
            from_.nbors.remove(to)
        if from_ in to.nbors:
            to.nbors.remove(from_)
        if type is Signal.type:
            cls = Signal, (from_, to) if from_ < to else (to, from_)  # Uses __cmp__
        elif type is Station.type:
            cls = (Station,)
        else:
            cls = ()
        new_node = self.createNode(point[0], point[1], *cls)
        self.connectNodes(from_, new_node)
        self.connectNodes(new_node, to)
        return new_node

    def prune(self, node):
        if node.type is Signal.type:
            if len(node.nbors) == 1:
                loop.graph.deleteNode(node)
                return True
        elif not node.nbors:
            loop.graph.deleteNode(node)
            return True

    def deleteNode(self, node):
        self.dirty = True
        self.nodes.remove(node)
        if node.type is Signal.type:
            if len(node.nbors) == 2:
                loop.graph.connectNodes(*node.nbors)

        for nbor in node.nbors:
            pair = (node, nbor) if node.id < nbor.id else (nbor, node)
            del self.edges[pair]
            if node in nbor.nbors:
                nbor.nbors.remove(node)
                loop.graph.prune(nbor)
        if node.type is Station.type:
            loop.stations_deleted.append(node)

    def deleteEdge(self, from_, to):
        self.dirty = True
        from_.nbors.remove(to)
        loop.graph.prune(from_)
        to.nbors.remove(from_)
        loop.graph.prune(to)
        pair = (from_, to) if from_.id < to.id else (to, from_)
        del self.edges[pair]

    def replaceNode(self, node, cls):
        new_node = self.createNode(node.x, node.y, cls)
        new_node.nbors = node.nbors[:]
        for nbor in node.nbors:
            self.connectNodes(new_node, nbor)
        self.deleteNode(node)

    def getEdge(self, from_, to):
        return self.edges[(from_, to) if from_.id < to.id else (to, from_)]


class Wagon(object):
    size = 0.5
    loading_speed = 20

    def __init__(self, type=0, capacity=10):
        self.x = self.y = 0
        self.edge = None
        self.type, self.capacity = type, capacity
        self.cargo = 0

    def draw(self):
        drawing.Wagon_draw(self.x, self.y)


class Train(object):
    speed = 20
    size = 0.5

    def __init__(self, edge, start, destination):
        self.edge = edge
        self.destination = destination
        self.origin = start
        self.start = start
        self.end = start
        self.pos = 0.0
        self.x, self.y = self.start.x, self.start.y
        self.dirty = True
        self.path = []
        self.wagons = []
        self.trail = []
        self.addWagon(Wagon())
        self.addWagon(Wagon())
        self.addWagon(Wagon())
        self.addWagon(Wagon())
        self.addWagon(Wagon())

    def addWagon(self, wagon):
        self.wagons.append(wagon)

    def updateCoords(self, dt):
        if self.start is not self.end:  # start == end means train is newly created with no orders
            self.pos += (self.speed * dt) / self.edge.length
            # Move to new edge, or we're at our goal
            if self.pos >= 1:
                if not self.path:
                    # We have reached our goal. Transfer cargo or head to origin
                    if self.end is self.destination:
                        if not self.transferCargo(dt, self.end):  # Transfer cargo if available, then head to origin
                            self.start = self.end = self.destination
                            self.pos = 0
                            self.destination, self.origin = self.origin, self.destination
                            self.trail = []
                            self.edge.busy.remove(self)
                            self.dirty = True
                        else:
                            self.pos = 1  # Wait while transferring cargo
                    # There is no path to our goal, stand still and wait until a path is found
                    else:
                        self.pos = 1
                # Move to new edge
                else:
                    if self.wagons:
                        self.trail.append(self.start)
                    self.start = self.end
                    self.end = self.path[0]
                    del self.path[0]
                    new_edge = loop.graph.getEdge(self.start, self.end)
                    self.pos = (self.pos * self.edge.length - self.edge.length) / new_edge.length
                    self.edge.busy.remove(self)
                    self.edge = new_edge
                    self.edge.busy.append(self)

            # Update the position of the train based on its pos on the edge
            self.x, self.y = utils.getNodePointAlongLine(self.start, self.end, self.pos)

        # Update wagon positions if moving
        if self.start is not self.end:
            offset = 0
            for i, wagon in enumerate(self.wagons):
                offset += wagon.size

                # Get a point on an edge in the trail at offset from the train pos
                edge, start, end, point = self.getPointAlongPath(list(reversed(self.trail)), self.end, self.start,
                                                                 1 - self.pos, offset)
                # Update busy state and clean trail if last wagon
                if wagon.edge != edge:
                    if wagon.edge:
                        wagon.edge.busy.remove(wagon)
                        if self.trail and i == len(self.wagons) - 1:
                            del self.trail[0]
                    wagon.edge = edge
                    edge.busy.append(wagon)

                if point:
                    wagon.x, wagon.y = point

    def transferCargo(self, dt, station):
        working = False  # If loading/unloading, signal to chill at station
        for wagon in self.wagons:
            if station.acceptsResource(wagon.type) and wagon.cargo > 0:  # Unload cargo
                amount = min(wagon.cargo, dt * wagon.loading_speed)
                station.unloadResource(wagon.type, amount)
                wagon.cargo -= amount
                working = True

            space = wagon.capacity - wagon.cargo
            if space > 0:  # Load cargo
                amount = station.loadResource(wagon.type, min(space, dt * wagon.loading_speed))
                if amount:
                    wagon.cargo += amount
                    working = True

        return working

    def getPointAlongPath(self, path, start, end, pos, distance):
        idx = 0
        edge = loop.graph.getEdge(start, end)
        pos += distance / edge.length

        while True:
            if pos > 1:  # Continue to look at next edge
                if idx == len(path):  # No point found, return the place where we got stuck
                    return edge, start, end, None
                new_edge = loop.graph.getEdge(end, path[idx])
                pos = (pos * edge.length - edge.length) / new_edge.length

                edge, start, end = new_edge, end, path[idx]
                idx += 1

            if pos <= 1:  # Point found, return
                return edge, start, end, (utils.getNodePointAlongLine(start, end, pos))

    def draw(self):
        drawing.Train_draw(resource_types, self.x, self.y, self.wagons)

    def update(self, dt):
        self.updateCoords(dt)

    def newPath(self, path):
        if path:
            if self.start is self.end:  # Newly created, has no direction/edge yet
                self.end = path[0]
                self.edge = loop.graph.getEdge(self.start, self.end)
                self.edge.busy.append(self)

            if self.end is path[0]:
                del path[0]
        self.path = path


class MouseTool(object):
    id = "mouse"
    name = "Mouse tool"

    snap_distance = 1
    signal_spacing = 1

    def __init__(self):
        self.reset()

    def reset(self):
        pass

    def click(self, x, y):
        pass

    def update(self, dt):
        self.updateHover()

    def updateHover(self):
        pass

    def rightClick(self, x, y):
        pass

    def keyRelease(self, symbol, modifiers):
        pass

    def draw(self, gui_anchor):
        pass


class TrainTool(MouseTool):
    id = "train"
    name = "Train"
    keymap = {
        key._0: 0, key._1: 1, key._2: 2, key._3: 3, key._4: 4, key._5: 5, key._6: 6, key._7: 7, key._8: 8, key._9: 9
    }

    def reset(self):
        self.hover_node = None
        self.last_node = None
        self.hover_path = None
        self.invalid = True
        self.active_train = None
        self.active_train_num = 0
        self.text = None

    def click(self, x, y):
        if not self.invalid:
            if self.active_train:
                # Active train and a valid new destination: Set destination
                if self.hover_node:
                    self.active_train.destination = self.hover_node
                    self.active_train.dirty = True
            else:
                # Valid node but no last node: Set origin for new train
                if self.hover_node and not self.last_node:
                    self.last_node = self.hover_node

                # Valid origin and destination: Create new train
                elif self.hover_node:
                    to = self.last_node.nbors[0]
                    train = Train(loop.graph.getEdge(self.last_node, to), self.last_node, self.hover_node)
                    loop.trains.append(train)
                    self.last_node = None
                    self.hover_path = None
                    if -1 < loop.trains.index(train) < 9:  # Activate new train in GUI if id <= 9
                        self.active_train_num = loop.trains.index(train) + 1
                        self.active_train = loop.trains[loop.trains.index(train)]

    def update(self, dt):
        self.updateHover()

    def updateHover(self):
        self.hover_pos = None
        self.hover_node = None
        self.hover_path = None
        self.invalid = False
        snap_node = None
        for node in loop.graph.nodes:
            if node.type is not Station.type:  # Snap only to stations
                continue
            dist = utils.getNodeDistance(mouse, node)
            if dist < self.snap_distance:
                if snap_node is None:
                    snap_node = (dist, node)
                elif dist < snap_node[0]:
                    snap_node = (dist, node)

        if snap_node:
            self.hover_node = snap_node[1]
            if self.active_train:
                self.last_node = self.active_train.origin  # Set start of path to train if a train is active
            if self.last_node:
                # Find a path between origin/train and destination
                self.hover_path = loop.pathfinder.getPath(Train(None, self.last_node, self.hover_node))

    def rightClick(self, x, y):
        if self.last_node:
            self.last_node = None

    def draw(self, gui_anchor):
        drawing.TrainTool_draw(window, gui_anchor, self.last_node, self.invalid, self.hover_node, self.hover_path,
                               self.active_train_num, loop.trains)

    def keyRelease(self, symbol, modifiers):
        # 0: New train, 1-9: Activate existing train
        num = self.keymap.get(symbol)
        if num is not None:
            if num == 0:
                self.reset()
                self.active_train = None
                self.active_train_num = 0
            elif num <= len(loop.trains):
                self.reset()
                self.active_train = loop.trains[num - 1]
                self.active_train_num = num


class RouteTool(MouseTool):
    id = "route"
    name = "Route"

    def reset(self):
        self.last_node = None
        self.hover_pos = (0, 0)
        self.hover_edge = None
        self.hover_node = None
        self.invalid = True

    def click(self, x, y):
        if not self.invalid:
            if self.hover_node:
                # Valid node and not back-tracking: Connect nodes
                if self.last_node and self.last_node is not self.hover_node:
                    loop.graph.connectNodes(self.last_node, self.hover_node)
                self.last_node = self.hover_node  # There is a good reason for this :)
            elif self.hover_edge:
                # Valid edge: Insert new node
                new_node = loop.graph.insertNode(self.hover_pos, *self.hover_edge)

                # Last node is not already on clicked edge: Connect new node to last node
                if self.last_node and self.last_node not in self.hover_edge:
                    loop.graph.connectNodes(self.last_node, new_node)
                self.last_node = new_node
            else:
                # No snap: Create a new node, connecting to last node if present
                new_node = loop.graph.createNode(*self.hover_pos)
                if self.last_node:
                    loop.graph.connectNodes(self.last_node, new_node)
                self.last_node = new_node

    def rightClick(self, x, y):
        if self.last_node:
            self.last_node = None

        # Edge, and nothing on its route is busy: Delete it, pruning signal-only edges
        elif not self.invalid and not self.hover_node and self.hover_edge:
            if not loop.graph.getEdge(*self.hover_edge).isRouteBusy():
                loop.graph.deleteEdge(*self.hover_edge)

    def updateHover(self):
        self.invalid = False
        self.hover_edge = None
        self.hover_node = None
        self.hover_pos = None

        if self.last_node:
            # Lock the hover position to an angle from last node
            locked_x, locked_y = utils.getAngleLockedPosition(8, mouse.x - self.last_node.x, mouse.y - self.last_node.y)
            angle_x, angle_y = self.last_node.x + locked_x, self.last_node.y + locked_y
            self.hover_pos = angle_x, angle_y
        else:
            angle_x, angle_y = mouse.x, mouse.y

        # Snap to node
        snap_node = None
        for node in loop.graph.nodes:
            dist = utils.getDistance((angle_x, angle_y), (node.x, node.y))
            if node.type is Signal.type:
                continue

            if dist == 0:
                if snap_node is None:
                    snap_node = (dist, node)
                elif dist < snap_node[0]:
                    snap_node = (dist, node)

        if snap_node:
            self.hover_pos = snap_node[1].x, snap_node[1].y
            self.hover_edge = None
            if self.last_node and snap_node in self.last_node.nbors:  # No back-tracking
                self.invalid = True
            else:
                self.hover_node = snap_node[1]
                if self.hover_node.isBusy():
                    self.invalid = True
                return
        else:
            # Snap to edge
            snap_edge = utils.getPointClosestToEdge(loop.graph.edges.keys(), angle_x, angle_y)
            if snap_edge:
                distance, n_edge, point = snap_edge
                if distance == 0:
                    self.hover_pos = angle_x, angle_y
                    self.hover_edge = n_edge
                    # If too close to a signal or edge is busy, it's invalid
                    if any(utils.getDistance(point, (node.x, node.y)) < self.signal_spacing
                           for node in n_edge if node.type is Signal.type) or loop.graph.getEdge(*n_edge).isBusy():
                        self.invalid = True
                    return
            self.hover_pos = angle_x, angle_y

    def draw(self, gui_anchor):
        drawing.RouteTool_draw(self.hover_pos, self.invalid, self.last_node)


class StationTool(MouseTool):
    id = "station"
    name = "Station"

    def reset(self):
        self.hover_pos = (0, 0)
        self.hover_edge = None
        self.hover_node = None
        self.invalid = True

    def click(self, x, y):
        if not self.invalid:
            # If snapped on Node: Upgrade to Station
            if self.hover_node and self.hover_node.type is Node.type:
                loop.graph.replaceNode(self.hover_node, Station)

            # If snapped on edge: Create station on edge
            elif self.hover_edge:
                loop.graph.insertNode(self.hover_pos, *self.hover_edge + (Station.type,))

            # If not snapped: Create station
            else:
                loop.graph.createNode(*self.hover_pos + (Station,))

    def rightClick(self, x, y):
        if not self.invalid:
            # Delete station, or downgrade to Node if in the middle of route
            if self.hover_node and self.hover_node.type is Station.type:
                if not loop.graph.prune(self.hover_node):
                    loop.graph.replaceNode(self.hover_node, Node)

    def updateHover(self):
        self.invalid = False
        self.hover_edge = None
        self.hover_node = None
        self.hover_pos = None

        # Snap to node
        snap_node = None
        for node in loop.graph.nodes:
            if node.type is Signal.type:
                continue
            dist = utils.getNodeDistance(mouse, node)

            if dist == 0:
                if snap_node is None:
                    snap_node = (dist, node)
                elif dist < snap_node[0]:
                    snap_node = (dist, node)

        if snap_node:
            self.hover_pos = snap_node[1].x, snap_node[1].y
            self.hover_edge = None
            self.hover_node = snap_node[1]
            if self.hover_node.isBusy():
                self.invalid = True
                return
        else:
            # Snap to edge
            snap_edge = utils.getPointClosestToEdge(loop.graph.edges.keys(), mouse.x, mouse.y)
            if snap_edge:
                distance, n_edge, point = snap_edge
                if distance == 0:
                    self.hover_pos = point
                    self.hover_edge = n_edge

                    # If too close to a signal or edge is busy, it's invalid
                    if any(utils.getDistance(point, (node.x, node.y)) < self.signal_spacing
                           for node in n_edge if node.type is Signal.type) or loop.graph.getEdge(*n_edge).isBusy():
                        self.invalid = True
                    return
            self.hover_pos = mouse.x, mouse.y

    def draw(self, gui_anchor):
        drawing.StationTool_draw(self.hover_pos, self.invalid)


class TraderTool(MouseTool):
    id = "trader"
    name = "Trader"

    def reset(self):
        self.hover_pos = (0, 0)
        self.hover_edge = None
        self.hover_node = None
        self.invalid = True

    def click(self, x, y):
        if not self.invalid:
            if not self.hover_node:  # Not snapped: Create new producing trader
                loop.createTrader(x, y, {0: 5}, [])
            else:  # Snapped: Toggle between producer and consumer
                if self.hover_node.produces:
                    self.hover_node.produces = {}
                    self.hover_node.consumes = [0]
                else:
                    self.hover_node.produces = {0: 5}
                    self.hover_node.consumes = []

    def rightClick(self, x, y):
        if not self.invalid:
            if self.hover_node:
                loop.deleteTrader(self.hover_node)

    def updateHover(self):
        self.invalid = False
        self.hover_edge = None
        self.hover_node = None
        self.hover_pos = None

        # Snap to node
        snap_node = None
        for node in loop.traders:
            dist = utils.getNodeDistance(mouse, node)

            if dist == 0:
                if snap_node is None:
                    snap_node = (dist, node)
                elif dist < snap_node[0]:
                    snap_node = (dist, node)

        if snap_node:
            self.hover_pos = snap_node[1].x, snap_node[1].y
            self.hover_edge = None
            self.hover_node = snap_node[1]
        else:
            self.hover_pos = mouse.x, mouse.y

    def draw(self, gui_anchor):
        drawing.TraderTool_draw(self.hover_pos, self.invalid)


class SignalTool(MouseTool):
    id = "signal"
    name = "Signal"

    def reset(self):
        self.hover = None
        self.hover_node = None
        self.hover_pos = (0, 0)
        self.invalid = True

    def click(self, x, y):
        if not self.invalid:
            if self.hover_edge:  # Snapped to edge: Insert new signal
                loop.graph.insertNode(self.hover_pos, *self.hover_edge, type=Signal.type)
            elif self.hover_node:  # Snapped to node: Toggle signal direction
                self.hover_node.toggleDirection()

    def rightClick(self, x, y):
        if self.hover_node and not self.hover_node.isBusy():
            loop.graph.deleteNode(self.hover_node)

    def updateHover(self):
        self.invalid = False
        self.hover_edge = None
        self.hover_node = None
        self.hover_pos = None

        # Snap to node
        snap_node = None
        for node in loop.graph.nodes:
            if not node.type is Signal.type:
                continue
            dist = utils.getNodeDistance(mouse, node)
            if dist < self.snap_distance:
                if snap_node is None:
                    snap_node = (dist, node)
                elif dist < snap_node[0]:
                    snap_node = (dist, node)

        if snap_node is not None:
            self.hover_node = snap_node[1]
            self.hover_pos = snap_node[1].x, snap_node[1].y
        else:
            # Snap to edge
            snap_edge = utils.getPointClosestToEdge(loop.graph.edges.keys(), mouse.x, mouse.y)
            if snap_edge:
                distance, n_edge, point = snap_edge
                if distance < self.snap_distance:
                    self.hover_edge = n_edge
                    self.hover_pos = point
                    # If too close to a signal or edge is busy, it's invalid
                    if any(utils.getDistance(point, (node.x, node.y)) < self.signal_spacing
                           for node in n_edge if node.type is Signal.type) or loop.graph.getEdge(*n_edge).isBusy():
                        self.invalid = True
                    return

    def draw(self, gui_anchor):
        drawing.SignalTool_draw(self.hover_pos, self.invalid)


class Toolbox:
    keymap = {
        key.Q: RouteTool.id,
        key.W: SignalTool.id,
        key.E: TrainTool.id,
        key.R: StationTool.id,
        key.A: TraderTool.id,
    }

    inv_keymap = {id: key for key, id in keymap.items()}
    keynames = {key.Q: "Q", key.W: "W", key.E: "E", key.R: "R", key.A: "A"}

    def __init__(self):
        self.ordered_tools = [RouteTool(), SignalTool(), TrainTool(), StationTool(), TraderTool()]
        self.tools = {tool.id: tool for tool in self.ordered_tools}
        self.active_tool = None
        self.text = None
        self.activateTool(RouteTool.id)

    def activateTool(self, id):
        self.active_tool = self.tools[id]
        self.active_tool.reset()
        text = "\n".join(["%s%s (%s)" %
                          ("*" if tool.id == id else " ",
                           tool.name,
                           self.keynames[self.inv_keymap[tool.id]])
                          for tool in self.ordered_tools])

        self.text = pyglet.text.Label(text,
                                      font_name='Courier',
                                      font_size=12,
                                      x=10, y=window.height-10,
                                      anchor_x='left', anchor_y='top', multiline=True,
                                      width=window.width)

    def update(self, dt):
        self.active_tool.update(dt)

    def draw(self):
        self.text.draw()
        self.active_tool.draw((self.text.x + 20, self.text.y - self.text.content_height - 10))

    def click(self, x, y):
        self.active_tool.click(x, y)

    def rightClick(self, x, y):
        self.active_tool.rightClick(x, y)

    def keyRelease(self, symbol, modifiers):
        if symbol in self.keymap:
            self.activateTool(self.keymap[symbol])
        else:
            self.active_tool.keyRelease(symbol, modifiers)

try:
    config = pyglet.gl.Config(sample_buffers=1, samples=4, depth_size=16, double_buffer=True)
    window = pyglet.window.Window(config=config)
except pyglet.window.NoSuchConfigException:
    window = pyglet.window.Window()


class Loop:
    def __init__(self):
        self.toolbox = Toolbox()
        self.graph = Graph()
        self.pathfinder = SoberBoy(self.graph)
        self.trains = []
        self.traders = []
        self.next_trader_id = 0
        self.traders_dirty = False
        self.stations_created = []
        self.stations_deleted = []

    def draw(self):
        [trader.draw() for trader in self.traders]
        [edge.draw() for edge in self.graph.edges.values()]
        [node.draw() for node in self.graph.nodes]
        self.toolbox.draw()
        [train.draw() for train in self.trains]

    def update(self, dt):
        if self.graph.dirty:
            for train in self.trains:
                train.newPath(self.pathfinder.getPath(train))
                train.dirty = False
            self.graph.dirty = False
        else:
            for train in self.trains:
                if train.dirty:
                    train.newPath(self.pathfinder.getPath(train))
                    train.dirty = False

        self.updateConnections()

        [train.update(dt) for train in self.trains]
        [trader.update(dt) for trader in self.traders]
        self.toolbox.update(dt)

    def createTrader(self, x, y, produces, consumes):
        self.traders_dirty = True
        self.traders.append(Trader(self.next_trader_id, x, y, produces, consumes))
        self.next_trader_id += 1

    def deleteTrader(self, trader):
        self.traders_dirty = True
        trader.delete = True

    def updateConnections(self):
        # Keep Trader.connections and Station.connections up to date

        if self.traders_dirty:
            for trader in self.traders:  # TODO: Mark new traders to reduce footprint
                for station in self.graph.nodes:
                    if station.type is not Station.type:  # Only check Stations
                        continue
                    if trader.delete and trader in station.connections:
                        station.connections.remove(trader)  # Remove deleted trader from station.connections

                    # Make sure nodes within reach are connected
                    if not trader.delete and utils.getNodeDistance(trader, station) < station.reach:
                        if not trader in station.connections:
                            station.connections.append(trader)
                        if not station in trader.connections:
                            trader.connections.append(station)
                if trader.delete:
                    self.traders.remove(trader)

            self.traders_dirty = False
        else:
            if self.stations_created:
                for station in self.stations_created:
                    for trader in self.traders:
                        if utils.getNodeDistance(trader, station) < station.reach:
                            trader.connections.append(station)
                            station.connections.append(trader)
                self.stations_created = []

            if self.stations_deleted:
                for station in self.stations_deleted:
                    for connection in station.connections:
                        connection.remove(station)
                self.stations_deleted = []
loop = Loop()

@window.event
def on_draw():
    window.clear()
    loop.draw()

@window.event
def on_mouse_press(x, y, button, modifiers):
    if button == mouse.LEFT:
        loop.toolbox.click((x + TILE_SIZE / 2) / TILE_SIZE, (y + TILE_SIZE / 2) / TILE_SIZE)
    elif button == mouse.RIGHT:
        loop.toolbox.rightClick((x + TILE_SIZE / 2) / TILE_SIZE, (y + TILE_SIZE / 2) / TILE_SIZE)

@window.event
def on_mouse_motion(x, y, dx, dy):
    mouse.sx = x
    mouse.sy = y
    mouse.x = (x + TILE_SIZE / 2) / TILE_SIZE
    mouse.y = (y + TILE_SIZE / 2) / TILE_SIZE

@window.event
def on_key_press(symbol, modifiers):
    pass

@window.event
def on_key_release(symbol, modifiers):
    loop.toolbox.keyRelease(symbol, modifiers)

def update(dt):
    loop.update(dt)

pyglet.clock.schedule_interval(update, 1/120.0)
pyglet.app.run()