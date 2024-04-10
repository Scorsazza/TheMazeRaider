import pyasge
from queue import PriorityQueue


class AStarNode:
    def __init__(self, coord, parent=None, g=0, h=0):
        self.coord = coord
        self.parent = parent
        self.g = g
        self.h = h
        self.f = g + h


    def __lt__(self, other):
        return self.f < other.f


class AStarPathing:
    def __init__(self, gamedata):
        self.data = gamedata
        self.path = []

    def heuristic(self, current: pyasge.Point2D, target: pyasge.Point2D):

        return abs(current.x - target.x) + abs(current.y - target.y)

    def find_path(self, startCoord: pyasge.Point2D, endCoord: pyasge.Point2D):
        self.path = []
        open_list = PriorityQueue()
        open_list.put((0, AStarNode(startCoord, g=0, h=self.heuristic(startCoord, endCoord))))
        closed = []

        while not open_list.empty():
            current_f, current_node = open_list.get()

            if current_node.coord == endCoord:
                self.retrace_path(current_node)
                return

            closed.append(current_node)
            neighbors = self.get_neighbours(current_node.coord)

            for neighbor_coord in neighbors:
                if any(closed_node.coord == neighbor_coord for closed_node in closed):
                    continue

                g_cost = current_node.g + 1  # Assuming uniform cost for moving to a neighbor
                h_cost = self.heuristic(neighbor_coord, endCoord)
                neighbor_node = AStarNode(neighbor_coord, current_node, g_cost, h_cost)

                if not any(open_node[1].coord == neighbor_coord and open_node[1].g <= g_cost for open_node in
                           open_list.queue):
                    open_list.put((neighbor_node.f, neighbor_node))

    def get_neighbours(self, coord: pyasge.Point2D):
        neighbors = []
        directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # Up, Right, Down, Left

        for dx, dy in directions:
            new_x = int(coord.x + dx)
            new_y = int(coord.y + dy)
            if 0 <= new_x < self.data.game_map.width and 0 <= new_y < self.data.game_map.height:
                if self.data.game_map.costs[new_y][new_x] == 0:
                    neighbors.append(pyasge.Point2D(new_x, new_y))

        return neighbors


    def retrace_path(self, endNode):
        currentNode = endNode
        while currentNode is not None:
            self.path.append(currentNode.coord)
            currentNode = currentNode.parent
        self.path.reverse()
