# encoding: utf-8
import pyglet
import primitives
import utils

TILE_SIZE = 20

circle = primitives.Circle(100, 100, stroke=1, width=10, color=(255, 255, 0, 1))
tiny_circle = primitives.Circle(100, 100, stroke=1, width=4, color=(255, 255, 0, 1))


def Trader_draw(resource_types, x, y, produces, consumes):
    circle.x, circle.y = x * TILE_SIZE, y * TILE_SIZE
    circle.color = (0.5, 0.5, 0.5, 1)
    circle.render()
    
    text = ""
    if produces:
        text += "Prod: " + ", ".join(["%s (%s)" % (resource_types[type], amount) for type, amount in produces.items()])
    if consumes:
        if produces: text += "\n"
        text += "Cons: " + ", ".join(["%s" % resource_types[item] for item in consumes])
    if text:
        pyglet.text.Label(text,
                          font_name='Courier',
                          font_size=9,
                          x=x * TILE_SIZE, y=y * TILE_SIZE - 10,
                          anchor_x='center', anchor_y='top', multiline=True,
                          width=150).draw()


def Node_draw(x, y):
    circle.x, circle.y = x * TILE_SIZE, y * TILE_SIZE
    circle.color = (255, 255, 0, 1)
    circle.render()


def Station_draw(resource_types, x, y, resources):
    circle.x, circle.y = x * TILE_SIZE, y * TILE_SIZE
    circle.color = (0, 1, 0, 1)
    circle.render()

    text = "\n".join(["%s->%s" % (source.id if source else "#",
                                  ", ".join(["%s %s" % (resource_types[type], int(amount))
                                             for type, amount in resources.items()]))
                      for source, resources in resources.items()])
    pyglet.text.Label(text,
                      font_name='Courier',
                      font_size=9,
                      x=x * TILE_SIZE, y=y * TILE_SIZE - 10,
                      anchor_x='center', anchor_y='top', multiline=True,
                      width=150).draw()


def Signal_draw(x, y, nw, se, nw_node, se_node):
    if nw is not None:
        sx, sy = utils.getPointRelativeLine((x * TILE_SIZE, y * TILE_SIZE), (-5, -5),
                                            (nw_node.x, nw_node.y),
                                            (se_node.x, se_node.y))
        tiny_circle.x = sx
        tiny_circle.y = sy
        if nw is True:
            tiny_circle.color = (0, 255, 0, 1)
        else:
            tiny_circle.color = (255, 0, 0, 1)
        tiny_circle.render()

    if se is not None:
        sx, sy = utils.getPointRelativeLine((x * TILE_SIZE, y * TILE_SIZE), (5, 5),
                                            (nw_node.x, nw_node.y),
                                            (se_node.x, se_node.y))
        tiny_circle.x = sx
        tiny_circle.y = sy
        if se is True:
            tiny_circle.color = (0, 255, 0, 1)
        else:
            tiny_circle.color = (255, 0, 0, 1)
        tiny_circle.render()


def Edge_draw(lnode, hnode, is_busy):
    line = primitives.Line((lnode.x * TILE_SIZE, lnode.y * TILE_SIZE),
                           (hnode.x * TILE_SIZE, hnode.y * TILE_SIZE), stroke=1, color=(255, 255, 0, 1))
    if is_busy:
        line.color = (1, 0.5, 0, 1)
    else:
        line.color = (1, 1, 0, 1)
    line.render()


def Wagon_draw(x, y):
    circle.x, circle.y = x * TILE_SIZE, y * TILE_SIZE
    circle.color = (0.8, 1, 0, 1)
    circle.render()


def Train_draw(resource_types, x, y, wagons):
    circle.x, circle.y = x * TILE_SIZE, y * TILE_SIZE
    circle.color = (1, 0, 0, 1)
    circle.render()
    [wagon.draw() for wagon in wagons]
    cargo = {}
    for wagon in wagons:
        cargo[wagon.type] = cargo.get(wagon.type, 0) + wagon.cargo
    if cargo:
        text = "\n".join(["%s: %s" % (resource_types[type], int(amount)) for type, amount in cargo.items()])
        pyglet.text.Label(text,
                          font_name='Courier',
                          font_size=9,
                          x=x * TILE_SIZE, y=y * TILE_SIZE + 10,
                          anchor_x='center', anchor_y='bottom', multiline=True,
                          width=60).draw()


def TrainTool_draw(window, gui_anchor, last_node, invalid, hover_node, hover_path, active_train_num, trains):
    if last_node:
        circle.x, circle.y = last_node.x * TILE_SIZE, last_node.y * TILE_SIZE
    circle.color = (0.5, 0.5, 1, 1)
    circle.render()

    if hover_node:
        circle.x, circle.y = hover_node.x * TILE_SIZE, hover_node.y * TILE_SIZE
        if invalid:
            circle.color = (1, 0, 0, 1)
        else:
            circle.color = (0.5, 0.5, 1, 1)
        circle.render()
    
    if hover_path:
        last_node = last_node
        for node in hover_path:
            primitives.Line((last_node.x * TILE_SIZE, last_node.y * TILE_SIZE),
                            (node.x * TILE_SIZE, node.y * TILE_SIZE), stroke=1,
                            color=(0, 0, 1, 1)).render()
            last_node = node
    
    text = "\n".join(["%s New train (0)" % ("*" if active_train_num == 0 else " ")] +
                     ["%s Train %s (%s)" % ("*" if active_train_num == n else " ", n, n)
                      for n in range(1, len(trains[:9]) + 1)])
    text_x, text_y = gui_anchor
    pyglet.text.Label(text,
                      font_name='Courier',
                      font_size=12,
                      x=text_x, y=text_y,
                      anchor_x='left', anchor_y='top', multiline=True,
                      width=window.width).draw()


def RouteTool_draw(hover_pos, invalid, last_node):
    circle.x, circle.y = hover_pos[0] * TILE_SIZE, hover_pos[1] * TILE_SIZE
    if invalid:
        circle.color = (1, 0, 0, 1)
    else:
        circle.color = (0.5, 0.5, 1, 1)
    circle.render()
    
    if last_node:
        primitives.Line((last_node.x * TILE_SIZE, last_node.y * TILE_SIZE),
                        (hover_pos[0] * TILE_SIZE, hover_pos[1] * TILE_SIZE), stroke=1,
                        color=(0.5, 0.5, 0, 1)).render()


def StationTool_draw(hover_pos, invalid):
    circle.x, circle.y = hover_pos[0] * TILE_SIZE, hover_pos[1] * TILE_SIZE
    if invalid:
        circle.color = (1, 0, 0, 1)
    else:
        circle.color = (0.5, 0.5, 1, 1)
    circle.render()


def TraderTool_draw(hover_pos, invalid):
    circle.x, circle.y = hover_pos[0] * TILE_SIZE, hover_pos[1] * TILE_SIZE
    if invalid:
        circle.color = (1, 0, 0, 1)
    else:
        circle.color = (0.5, 0.5, 1, 1)
    circle.render()


def SignalTool_draw(hover_pos, invalid):
    if hover_pos:
        circle.x, circle.y = hover_pos[0] * TILE_SIZE, hover_pos[1] * TILE_SIZE
    if invalid:
        circle.color = (1, 0, 0, 1)
    else:
        circle.color = (0.5, 0.5, 1, 1)
    circle.render()
