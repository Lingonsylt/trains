# encoding: utf-8
import utils
import pyglet
from pyglet.window import key, mouse
import primitives

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
        circle.x, circle.y = self.x, self.y
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
            tiny_circle.x, tiny_circle.y = utils.getPointRelativeLine((self.x, self.y), (-5, -5),
                                                                      (self.nw_node.x, self.nw_node.y),
                                                                      (self.se_node.x, self.se_node.y))
            if self.nw is True:
                tiny_circle.color = (0, 255, 0, 1)
            else:
                tiny_circle.color = (255, 0, 0, 1)
            tiny_circle.render()

        if self.se is not None:
            tiny_circle.x, tiny_circle.y = utils.getPointRelativeLine((self.x, self.y), (5, 5),
                                                                      (self.nw_node.x, self.nw_node.y),
                                                                      (self.se_node.x, self.se_node.y))
            if self.se is True:
                tiny_circle.color = (0, 255, 0, 1)
            else:
                tiny_circle.color = (255, 0, 0, 1)
            tiny_circle.render()


class Graph:
    def __init__(self):
        self.nodes = {}
        self.nodes_list = []
        self.nodes_pairs = []
        self.node_lines = []
        self.next_node_id = 0

    def createNode(self, x, y, signal=None):
        node = Node(self.next_node_id, x, y) if not signal else Signal(self.next_node_id, x, y, *signal)
        self.next_node_id += 1
        self.nodes[node.id] = node
        self.nodes_list.append(node)
        return node

    def connectNodes(self, from_, to):
        if from_ is to:
            raise Exception("Cannot connect to self!")
        from_.nbors.append(to)
        to.nbors.append(from_)
        pair = (from_, to) if from_.id < to.id else (to, from_)
        if not pair in self.nodes_pairs:
            self.nodes_pairs.append(pair)
            line = primitives.Line((from_.x, from_.y), (to.x, to.y), stroke=1, color=(255, 255, 0, 1))
            line.pair = pair
            self.node_lines.append(line)

    def insertNode(self, point, from_, to, signal=False):
        pair = (from_, to) if from_.id < to.id else (to, from_)
        self.nodes_pairs.remove(pair)
        for node_line in self.node_lines:
            if node_line.pair == pair:
                self.node_lines.remove(node_line)  # Danger danger! List mutation within loop.
                break                              # But it's ok if this is the last iteration.
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

    def deleteNode(self, node):
        for nbor in node.nbors:
            if node in nbor.nbors:
                nbor.nbors.remove(node)
            pair = (node, nbor) if node.id < nbor.id else (nbor, node)
            self.nodes_pairs.remove(pair)
            for node_line in self.node_lines:
                if node_line.pair == pair:
                    self.node_lines.remove(node_line)  # Danger danger! List mutation within loop.
                    break                              # But it's ok if this is the last iteration.
            #if nbor.type is Signal.type:

        self.nodes_list.remove(node)
        del self.nodes[node.id]
        if node.type is Signal.type:
            if len(node.nbors) == 2:
                graph.connectNodes(*node.nbors)

    def deleteEdge(self, from_, to):
        from_.nbors.remove(to)
        to.nbors.remove(from_)
        pair = (from_, to) if from_.id < to.id else (to, from_)
        self.nodes_pairs.remove(pair)
        for node_line in self.node_lines:
            if node_line.pair == pair:
                self.node_lines.remove(node_line)  # Danger danger! List mutation within loop.
                break                              # But it's ok if this is the last iteration.

class MouseTool(object):
    id = "mouse"
    name = "Mouse tool"

    snap_distance = 50
    signal_spacing = 50

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
                    graph.connectNodes(self.last_node, self.hover_node)
                self.last_node = self.hover_node
            elif self.hover_edge:
                new_node = graph.insertNode(self.hover_pos, *self.hover_edge)
                if self.last_node and self.last_node not in self.hover_edge:
                    graph.connectNodes(self.last_node, new_node)
                self.last_node = new_node
            else:
                new_node = graph.createNode(int(x), int(y))  # TODO: Will bring chaos if mouse moved since last updateHover
                if self.last_node:
                    graph.connectNodes(self.last_node, new_node)
                self.last_node = new_node

    def rightClick(self, x, y):
        if self.last_node:
            self.last_node = None
        elif not self.invalid and not self.hover_node and self.hover_edge:
            graph.deleteEdge(*self.hover_edge)

    def updateHover(self):
        self.invalid = False
        self.hover_edge = None
        self.hover_node = None
        self.hover_pos = None

        snap_node = None
        for node in graph.nodes_list:
            dist = utils.getDistance((mouse.x, mouse.y), (node.x, node.y))
            if node.type is Signal.type and dist < self.signal_spacing:  # TODO: Signals should only
                self.hover_pos = mouse.x, mouse.y                        # be invalid along edge
                self.invalid = True
                return

            if dist < self.snap_distance:
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
            snap_edge = utils.getPointClosestToEdge(graph.nodes_pairs, mouse.x, mouse.y)
            if snap_edge:
                distance, edge, point = snap_edge
                if distance < self.snap_distance:
                    self.hover_pos = point
                    self.hover_edge = edge
                    return
            self.hover_pos = mouse.x, mouse.y

    def draw(self):
        circle.x, circle.y = self.hover_pos
        if self.invalid:
            circle.color = (1, 0, 0, 1)
        else:
            circle.color = (0.5, 0.5, 1, 1)
        circle.render()

        if self.last_node:
            primitives.Line((self.last_node.x, self.last_node.y), self.hover_pos, stroke=1,
                            color=(0.5, 0.5, 0, 1)).render()


class SignalTool(MouseTool):
    id = "signal"
    name = "Signal"

    def reset(self):
        self.hover = None
        self.hover_node = None

    def click(self, x, y):
        if not self.invalid:
            if self.hover_edge:
                graph.insertNode(self.hover_pos, *self.hover_edge, signal=True)
            elif self.hover_node:
                self.hover_node.toggleDirection()

    def rightClick(self, x, y):
        if self.hover_node:
            graph.deleteNode(self.hover_node)

    def updateHover(self):
        self.invalid = False
        self.hover_edge = None
        self.hover_node = None
        self.hover_pos = None

        snap_node = None
        for node in graph.nodes_list:
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
            snap_edge = utils.getPointClosestToEdge(graph.nodes_pairs, mouse.x, mouse.y)
            if snap_edge:
                distance, edge, point = snap_edge
                if distance < self.snap_distance:
                    self.hover_edge = edge
                    self.hover_pos = point
                    return

    def draw(self):
        if self.hover_pos:
            circle.x, circle.y = self.hover_pos
            if self.invalid:
                circle.color = (1, 0, 0, 1)
            else:
                circle.color = (0.5, 0.5, 1, 1)
            circle.render()


class Toolbox:
    keymap = {
        key.R: RouteTool.id,
        key.S: SignalTool.id
    }

    inv_keymap = {id: key for key, id in keymap.items()}
    keynames = {key.R: "R", key.S: "S"}

    def __init__(self):
        self.tools = {
            RouteTool.id: RouteTool(),
            SignalTool.id: SignalTool()
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

toolbox = Toolbox()
graph = Graph()

@window.event
def on_draw():
    window.clear()

    [line.render() for line in graph.node_lines]
    [node.draw() for node in graph.nodes_list]

    toolbox.draw()

@window.event
def on_mouse_press(x, y, button, modifiers):
    if button == mouse.LEFT:
        toolbox.click(x, y)
    elif button == mouse.RIGHT:
        toolbox.rightClick(x, y)

@window.event
def on_mouse_motion(x, y, dx, dy):
    mouse.x = x
    mouse.y = y

@window.event
def on_key_press(symbol, modifiers):
    pass

@window.event
def on_key_release(symbol, modifiers):
    toolbox.keyRelease(symbol, modifiers)

def update(dt):
    toolbox.update(dt)

pyglet.clock.schedule_interval(update, 1/120.0)
pyglet.app.run()

# Ta bort ordentligt
# Visa signalerna bättre i guit
# Add the mighty pathfinder