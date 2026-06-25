class Cell:
    """A single grid cell. Knows which of its 4 walls are still standing."""

    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.walls = {"N": True, "S": True, "E": True, "W": True}
        self.visited = False
        self.blocked = False  # part of the solid 42 room -> never carved

    def __repr__(self):
        return f"Cell({self.row}, {self.col})"
