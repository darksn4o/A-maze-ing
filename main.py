from Maze.maze_generator import Maze


def main():
    maze = Maze(width=20, height=20)
    # A centered "42" the corridors route around (omitted if the maze is too small).
    maze.add_42()
    maze.generate()
    print(maze.render())


if __name__ == "__main__":
    main()
