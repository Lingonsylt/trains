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
            closest_point = from_.x, from_.y, from_
        elif distance_from_from > 1:
            closest_point = to.x, to.y, to
        else:
            closest_point = from_.x + from_to_to[0] * distance_from_from, \
                            from_.y + from_to_to[1] * distance_from_from, None

        distance = math.sqrt(float((mouse_x - closest_point[0]) ** 2) + float((mouse_y - closest_point[1]) ** 2))

        if min_dist is None:
            min_dist = (distance, from_, to, closest_point)
        elif distance < min_dist[0]:
            min_dist = (distance, from_, to, closest_point)
    return min_dist