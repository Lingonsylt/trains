# encoding: utf-8
import random
import utils
import pyglet
from pyglet.window import key, mouse
import primitives

TILE_SIZE = 20
mouse.x = 0
mouse.y = 0
circle = primitives.Circle(100, 100, stroke=1, width=10, color=(255, 255, 0, 1))
tiny_circle = primitives.Circle(100, 100, stroke=1, width=4, color=(255, 255, 0, 1))


class Node(object):
    type = object()

    def __init__(self, id, x, y):
        self.id, self.x, self.y = id, x, y
        self.nbors = []

    def draw(self):
        circle.x, circle.y = self.x * TILE_SIZE, self.y * TILE_SIZE
        circle.color = (255, 255, 0, 1)
        circle.render()

    def __repr__(self):
        return str(self.id)


class Signal(Node):
    type = object()

    def __init__(self, id, x, y, nw, se):
        super(Signal, self).__init__(id, x, y)
        self.nw_node, self.se_node = nw, se
        self.nw = self.se = True

    def toggleDirection(self):
        if self.nw is not None and self.se is not None:
            self.se = None
        elif self.se is None:
            self.se = True
            self.nw = None
        else:
            self.nw = True
            self.se = True

    def draw(self):
        if self.nw is not None:
            sx, sy = utils.getPointRelativeLine((self.x * TILE_SIZE, self.y * TILE_SIZE), (-5, -5),
                                                (self.nw_node.x, self.nw_node.y),
                                                (self.se_node.x, self.se_node.y))
            tiny_circle.x = sx
            tiny_circle.y = sy
            if self.nw is True:
                tiny_circle.color = (0, 255, 0, 1)
            else:
                tiny_circle.color = (255, 0, 0, 1)
            tiny_circle.render()

        if self.se is not None:
            sx, sy = utils.getPointRelativeLine((self.x * TILE_SIZE, self.y * TILE_SIZE), (5, 5),
                                                (self.nw_node.x, self.nw_node.y),
                                                (self.se_node.x, self.se_node.y))
            tiny_circle.x = sx
            tiny_circle.y = sy
            if self.se is True:
                tiny_circle.color = (0, 255, 0, 1)
            else:
                tiny_circle.color = (255, 0, 0, 1)
            tiny_circle.render()


class DrunkenBoy:
    def __init__(self, graph):
        self.graph = graph

    def getPath(self, train):
        return self._getPath(train, train.end, train.start, []) + [train.destination]

    def _getPath(self, train, node, last_node, path):
        random_nbors = node.nbors[:]
        random.shuffle(random_nbors)
        for nbor in random_nbors:
            if nbor is last_node:
                continue
            if nbor is train.destination:
                return path
            path.append(nbor)
            return self._getPath(train, nbor, node, path)
        return path


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
        last_node = train.start
        while True:
            for nbor in current_node.nbors:
                if nbor is train.destination:
                    path = [nbor]
                    node = current_node
                    while node is not train.end:
                        path.append(node)
                        node = node_data[node].parent
                    return list(reversed(path))

                if nbor is last_node or nbor in closed_list:
                    continue

                pair = (current_node, nbor) if current_node.id < nbor.id else (nbor, current_node)

                if nbor in open_list:
                    g = node_data[current_node].g + self.graph.nodes_pairs[pair].length
                    if g < node_data[nbor].g:
                        node_data[nbor].g = g
                        node_data[nbor].parent = current_node
                else:
                    node_data[nbor] = self.DataItem(current_node,
                                                    node_data[current_node].g + self.graph.nodes_pairs[pair].length,
                                                    utils.getDistance((train.destination.x, train.destination.y),
                                                                      (nbor.x, nbor.y)))
                open_list.append(nbor)

            open_list.remove(current_node)
            closed_list.append(current_node)
            last_node = current_node

            if not open_list:
                return []

            scored_opens = []
            for node in open_list:
                data = node_data[node]
                scored_opens.append((data.g + data.h, node))
            scored_opens.sort(key=lambda x: x[0], reverse=True)
            current_node = scored_opens.pop()[1]


class Edge:
    def __init__(self, lnode, hnode):
        self.lnode, self.hnode = lnode, hnode
        self.length = utils.getDistance((lnode.x, lnode.y), (hnode.x, hnode.y))
        self.busy = []
        self.line = primitives.Line((lnode.x * TILE_SIZE, lnode.y * TILE_SIZE),
                                    (hnode.x * TILE_SIZE, hnode.y * TILE_SIZE), stroke=1, color=(255, 255, 0, 1))

    def draw(self):
        if self.busy:
            self.line.color = (1, 0.5, 0, 1)
        else:
            self.line.color = (1, 1, 0, 1)
        self.line.render()


class Graph:
    def __init__(self):
        self.nodes = {}
        self.nodes_list = []
        self.nodes_pairs = {}
        self.next_node_id = 0
        self.dirty = False

    def createNode(self, x, y, signal=None):
        self.dirty = True
        node = Node(self.next_node_id, x, y) if not signal else Signal(self.next_node_id, x, y, *signal)
        self.next_node_id += 1
        self.nodes[node.id] = node
        self.nodes_list.append(node)
        return node

    def connectNodes(self, from_, to):
        if from_ is to:
            raise Exception("Cannot connect to self!")

        self.dirty = True
        from_.nbors.append(to)
        to.nbors.append(from_)
        pair = (from_, to) if from_.id < to.id else (to, from_)
        if not pair in self.nodes_pairs:
            self.nodes_pairs[pair] = Edge(*pair)

    def insertNode(self, point, from_, to, signal=False):
        self.dirty = True
        pair = (from_, to) if from_.id < to.id else (to, from_)
        del self.nodes_pairs[pair]
        if to in from_.nbors:
            from_.nbors.remove(to)
        if from_ in to.nbors:
            to.nbors.remove(from_)
        if signal:
            signal = (from_, to) if (from_.x, from_.y) < (to.x, to.y) else (to, from_)
        new_node = self.createNode(point[0], point[1], signal)
        self.connectNodes(from_, new_node)
        self.connectNodes(new_node, to)
        return new_node

    def prune(self, node):
        if node.type is Signal.type:
            if len(node.nbors) == 1:
                loop.graph.deleteNode(node)
        elif not node.nbors:
            loop.graph.deleteNode(node)

    def deleteNode(self, node):
        self.dirty = True
        self.nodes_list.remove(node)
        del self.nodes[node.id]
        if node.type is Signal.type:
            if len(node.nbors) == 2:
                loop.graph.connectNodes(*node.nbors)

        for nbor in node.nbors:
            pair = (node, nbor) if node.id < nbor.id else (nbor, node)
            del self.nodes_pairs[pair]
            if node in nbor.nbors:
                nbor.nbors.remove(node)
                loop.graph.prune(nbor)

    def deleteEdge(self, from_, to):
        self.dirty = True
        from_.nbors.remove(to)
        loop.graph.prune(from_)
        to.nbors.remove(from_)
        loop.graph.prune(to)
        pair = (from_, to) if from_.id < to.id else (to, from_)
        del self.nodes_pairs[pair]

class Wagon(object):
    size = 0.5

    def __init__(self):
        self.x = self.y = 0
        self.edge = None

    def draw(self):
        circle.x, circle.y = self.x * TILE_SIZE, self.y * TILE_SIZE
        circle.color = (0.8, 1, 0, 1)
        circle.render()


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
        self.trail_length = 0
        self.total_length = self.size
        self.addWagon(Wagon())
        self.addWagon(Wagon())
        self.addWagon(Wagon())
        self.addWagon(Wagon())
        self.addWagon(Wagon())

    def addWagon(self, wagon):
        self.total_length += wagon.size
        self.wagons.append(wagon)

    def updateCoords(self, dt):
        if self.start is not self.end:
            self.pos += (self.speed * dt) / self.edge.length
            if self.pos >= 1:
                if not self.path:
                    if self.end is self.destination:
                        self.start = self.end = self.destination
                        self.pos = 0
                        self.destination, self.origin = self.origin, self.destination
                        self.trail = []
                        self.trail_length = 0
                        self.edge.busy.remove(self)
                        self.dirty = True
                    else:
                        self.pos = 1
                else:
                    self.trail.append(self.start)
                    self.start = self.end
                    self.end = self.path[0]
                    del self.path[0]
                    pair = (self.start, self.end) if self.start.id < self.end.id else (self.end, self.start)
                    new_edge = loop.graph.nodes_pairs[pair]
                    self.pos = (self.pos * self.edge.length - self.edge.length) / new_edge.length
                    self.edge.busy.remove(self)
                    self.edge = new_edge
                    self.edge.busy.append(self)

            self.x, self.y = utils.getPointAlongLine((self.start.x, self.start.y), (self.end.x, self.end.y), self.pos)

        if self.start is not self.end:
            offset = 0
            for i, wagon in enumerate(self.wagons):
                offset += wagon.size

                edge, start, end, point = self.getPointAlongPath(list(reversed(self.trail)), self.end, self.start,
                                                                 1 - self.pos, offset)
                if wagon.edge != edge:
                    if wagon.edge:
                        wagon.edge.busy.remove(wagon)
                        if self.trail and i == len(self.wagons) - 1:
                            del self.trail[0]
                    wagon.edge = edge
                    edge.busy.append(wagon)

                if point:
                    wagon.x, wagon.y = point

    def getPointAlongPath(self, path, start, end, pos, distance):
        idx = 0
        edge = loop.graph.nodes_pairs[(start, end) if start.id < end.id else (end, start)]
        pos += distance / edge.length

        while True:
            if pos > 1:
                if idx == len(path):
                    return edge, start, end, None
                new_edge = loop.graph.nodes_pairs[(end, path[idx]) if end.id < path[idx].id else (path[idx], end)]
                pos = (pos * edge.length - edge.length) / new_edge.length

                edge = new_edge
                start = end
                end = path[idx]
                idx += 1

            if pos <= 1:
                return edge, start, end, (utils.getPointAlongLine((start.x, start.y), (end.x, end.y), pos))

    def draw(self):
        circle.x, circle.y = self.x * TILE_SIZE, self.y * TILE_SIZE
        circle.color = (1, 0, 0, 1)
        circle.render()
        [wagon.draw() for wagon in self.wagons]

    def update(self, dt):
        self.updateCoords(dt)

    def newPath(self, path):
        if path:
            if self.start is self.end:
                self.end = path[0]
                pair = (self.start, self.end) if self.start.id < self.end.id else (self.end, self.start)
                self.edge = loop.graph.nodes_pairs[pair]
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

    def draw(self):
        pass


class TrainTool(MouseTool):
    id = "train"
    name = "Train"

    def reset(self):
        self.hover_node = None
        self.last_node = None
        self.hover_path = None
        self.invalid = True

    def click(self, x, y):
        if not self.invalid:
            if self.hover_node and not self.last_node:
                self.last_node = self.hover_node
            elif self.hover_node:
                to = self.last_node.nbors[0]
                pair = (self.last_node, to) if self.last_node.id < to.id else (to, self.last_node)
                train = Train(loop.graph.nodes_pairs[pair], self.last_node, self.hover_node)
                loop.trains.append(train)
                self.last_node = None
                self.hover_path = None

    def update(self, dt):
        self.updateHover()

    def updateHover(self):
        self.hover_pos = None
        self.hover_node = None
        self.hover_path = None
        self.invalid = False
        snap_node = None
        for node in loop.graph.nodes_list:
            if node.type is Signal.type:
                continue
            dist = utils.getDistance((mouse.x, mouse.y), (node.x, node.y))
            if dist < self.snap_distance:
                if snap_node is None:
                    snap_node = (dist, node)
                elif dist < snap_node[0]:
                    snap_node = (dist, node)

        if snap_node:
            self.hover_node = snap_node[1]
            if self.last_node:
                self.hover_path = loop.pathfinder.getPath(Train(None, self.last_node, self.hover_node))

    def rightClick(self, x, y):
        if self.last_node:
            self.last_node = None

    def draw(self):
        if self.last_node:
            circle.x, circle.y = self.last_node.x * TILE_SIZE, self.last_node.y * TILE_SIZE
            circle.color = (0.5, 0.5, 1, 1)
            circle.render()

        if self.hover_node:
            circle.x, circle.y = self.hover_node.x * TILE_SIZE, self.hover_node.y * TILE_SIZE
            if self.invalid:
                circle.color = (1, 0, 0, 1)
            else:
                circle.color = (0.5, 0.5, 1, 1)
            circle.render()

        if self.hover_path:
            last_node = self.last_node
            for node in self.hover_path:
                primitives.Line((last_node.x * TILE_SIZE, last_node.y * TILE_SIZE),
                                (node.x * TILE_SIZE, node.y * TILE_SIZE), stroke=1,
                                color=(0, 0, 1, 1)).render()
                last_node = node


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
                if self.last_node and self.last_node is not self.hover_node:
                    loop.graph.connectNodes(self.last_node, self.hover_node)
                self.last_node = self.hover_node
            elif self.hover_edge:
                new_node = loop.graph.insertNode(self.hover_pos, *self.hover_edge)
                if self.last_node and self.last_node not in self.hover_edge:
                    loop.graph.connectNodes(self.last_node, new_node)
                self.last_node = new_node
            else:
                new_node = loop.graph.createNode(*self.hover_pos)
                if self.last_node:
                    loop.graph.connectNodes(self.last_node, new_node)
                self.last_node = new_node

    def rightClick(self, x, y):
        if self.last_node:
            self.last_node = None
        elif not self.invalid and not self.hover_node and self.hover_edge:
            loop.graph.deleteEdge(*self.hover_edge)

    def updateHover(self):
        self.invalid = False
        self.hover_edge = None
        self.hover_node = None
        self.hover_pos = None

        if self.last_node:
            locked_x, locked_y = utils.getAngleLockedPosition(8, mouse.x - self.last_node.x, mouse.y - self.last_node.y)
            angle_x, angle_y = self.last_node.x + locked_x, self.last_node.y + locked_y
            self.hover_pos = angle_x, angle_y
        else:
            angle_x, angle_y = mouse.x, mouse.y

        snap_node = None
        for node in loop.graph.nodes_list:
            dist = utils.getDistance((angle_x, angle_y), (node.x, node.y))
            if node.type is Signal.type and dist < self.signal_spacing:  # TODO: Signals should only
                self.hover_pos = angle_x, angle_y                        # be invalid along edge
                self.invalid = True
                return

            if dist == 0:
                if snap_node is None:
                    snap_node = (dist, node)
                elif dist < snap_node[0]:
                    snap_node = (dist, node)

        if snap_node:
            self.hover_pos = snap_node[1].x, snap_node[1].y
            self.hover_edge = None
            if self.last_node and snap_node in self.last_node.nbors:
                self.invalid = True
            else:
                self.hover_node = snap_node[1]
        else:
            snap_edge = utils.getPointClosestToEdge(loop.graph.nodes_pairs.keys(), angle_x, angle_y)
            if snap_edge:
                distance, edge, point = snap_edge
                if distance == 0:
                    self.hover_pos = angle_x, angle_y
                    self.hover_edge = edge
                    if loop.graph.nodes_pairs[edge if edge[0].id < edge[1].id else (edge[1], edge[0])].busy:
                        self.invalid = True
                    return
            self.hover_pos = angle_x, angle_y

    def draw(self):
        circle.x, circle.y = self.hover_pos[0] * TILE_SIZE, self.hover_pos[1] * TILE_SIZE
        if self.invalid:
            circle.color = (1, 0, 0, 1)
        else:
            circle.color = (0.5, 0.5, 1, 1)
        circle.render()

        if self.last_node:
            primitives.Line((self.last_node.x * TILE_SIZE, self.last_node.y * TILE_SIZE),
                            (self.hover_pos[0] * TILE_SIZE, self.hover_pos[1] * TILE_SIZE), stroke=1,
                            color=(0.5, 0.5, 0, 1)).render()


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
            if self.hover_edge:
                loop.graph.insertNode(self.hover_pos, *self.hover_edge, signal=True)
            elif self.hover_node:
                self.hover_node.toggleDirection()

    def rightClick(self, x, y):
        if self.hover_node:
            loop.graph.deleteNode(self.hover_node)

    def updateHover(self):
        self.invalid = False
        self.hover_edge = None
        self.hover_node = None
        self.hover_pos = None

        snap_node = None
        for node in loop.graph.nodes_list:
            dist = utils.getDistance((mouse.x, mouse.y), (node.x, node.y))
            if not node.type is Signal.type and dist < self.signal_spacing:
                self.hover_pos = mouse.x, mouse.y
                self.invalid = True
                return

            if dist < self.signal_spacing:
                if snap_node is None:
                    snap_node = (dist, node)
                elif dist < snap_node[0]:
                    snap_node = (dist, node)

        if snap_node is not None:
            self.hover_node = snap_node[1]
            self.hover_pos = snap_node[1].x, snap_node[1].y
        else:
            snap_edge = utils.getPointClosestToEdge(loop.graph.nodes_pairs.keys(), mouse.x, mouse.y)
            if snap_edge:
                distance, edge, point = snap_edge
                if distance < self.snap_distance:
                    self.hover_edge = edge
                    self.hover_pos = point
                    return

    def draw(self):
        if self.hover_pos:
            circle.x, circle.y = self.hover_pos[0] * TILE_SIZE, self.hover_pos[1] * TILE_SIZE
            if self.invalid:
                circle.color = (1, 0, 0, 1)
            else:
                circle.color = (0.5, 0.5, 1, 1)
            circle.render()


class Toolbox:
    keymap = {
        key.Q: RouteTool.id,
        key.W: SignalTool.id,
        key.E: TrainTool.id
    }

    inv_keymap = {id: key for key, id in keymap.items()}
    keynames = {key.Q: "Q", key.W: "W", key.E: "E"}

    def __init__(self):
        self.tools = {
            RouteTool.id: RouteTool(),
            SignalTool.id: SignalTool(),
            TrainTool.id: TrainTool()
        }
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
                          for tool in sorted(self.tools.values())])

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
        self.active_tool.draw()

    def click(self, x, y):
        self.active_tool.click(x, y)

    def rightClick(self, x, y):
        self.active_tool.rightClick(x, y)

    def keyRelease(self, symbol, modifiers):
        if symbol in self.keymap:
            self.activateTool(self.keymap[symbol])

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

    def draw(self):
        [edge.draw() for edge in self.graph.nodes_pairs.values()]
        [node.draw() for node in self.graph.nodes_list]
        self.toolbox.draw()
        [train.draw() for train in self.trains]

    def update(self, dt):
        [train.update(dt) for train in self.trains]
        self.toolbox.update(dt)

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

# Ta bort ordentligt
# Visa signalerna bättre i guit
# Add the mighty pathfinder