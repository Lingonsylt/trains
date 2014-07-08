import math

def getDistance(from_, to):
    return math.sqrt(float((from_[0] - to[0]) ** 2 + float((from_[1] - to[1]) ** 2)))

def getPointClosestToEdge(nodes_pairs, mouse_x, mouse_y):
    min_dist = None
    for from_, to in nodes_pairs:
        from_to_mouse = (mouse_x - from_.x, mouse_y - from_.y)
        from_to_to = (to.x - from_.x, to.y - from_.y)
        from_to_to_magnitude = from_to_to[0]**2 + from_to_to[1]**2
        dot = from_to_mouse[0]*from_to_to[0]+from_to_mouse[1]*from_to_to[1]
        distance_from_from = dot / float(from_to_to_magnitude)

        if distance_from_from <= 0:
            continue
        elif distance_from_from > 1:
            continue

        closest_point = from_.x + from_to_to[0] * distance_from_from, \
                        from_.y + from_to_to[1] * distance_from_from

        distance = math.sqrt(float((mouse_x - closest_point[0]) ** 2) + float((mouse_y - closest_point[1]) ** 2))

        if min_dist is None:
            min_dist = (distance, (from_, to), closest_point)
        elif distance < min_dist[0]:
            min_dist = (distance, (from_, to), closest_point)
    return min_dist

def getPointRelativeLine(start_point, relative_point, line_start, line_end):
    x, y = relative_point
    line_delta = tuple(x - y for x, y in zip(line_start, line_end))
    line_angle = math.atan2(*line_delta) * 180 / math.pi
    offset_x = (x * math.sin(line_angle * (math.pi / 180)) + y * math.sin((line_angle - 90) * (math.pi / 180)))
    offset_y = (y * math.cos(line_angle * (math.pi / 180)) + y * math.cos((line_angle - 90) * (math.pi / 180)))
    return start_point[0] + offset_x, start_point[1] + offset_y


def getPointAlongLine(from_, to, pos):
    from_x, from_y = from_
    to_x, to_y = to
    return from_x + (to_x - from_x) * pos, from_y + (to_y - from_y) * pos