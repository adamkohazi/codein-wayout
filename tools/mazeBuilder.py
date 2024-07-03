import xml.etree.ElementTree as ET
import os

# Project constants
WIDTH = 17
HEIGHT = 17

level = 3
name = "tricky2"

maze = ("xxxxxxxxxxsxxxxxx"
        "xxxxxxxxxx xxxxxx"
        "xx         xxxxxx"
        "xx xxxxxxx xxxxxx"
        "xx xxxxxxx xxxxxx"
        "xx xxxxxxx xxxxxx"
        "xx xxx xxxx xxxxx"
        "xx xxxxxxxx xxxxx"
        "xx xxxxxxxx xxxxx"
        "xx xxxxxxxx xxxxx"
        "xx xxxxxxxx xxxxx"
        "xx xxxxxxx xxxxxx"
        "xx xxxxxxx xxxxxx"
        "xx xxxxxxx xxxxxx"
        "xx         xxxxxx"
        "xxxxxxxxxx xxxxxx"
        "xxxxxxxxxxexxxxxx")


def posToCoords(position):
    return ((position%WIDTH) + 1, int(position/HEIGHT) + 1)


startCoords = posToCoords(maze.find("s"))
escapeCoords = posToCoords(maze.find("e"))

mazeRoot = ET.Element("Maze")
ET.SubElement(mazeRoot, "Level").text = str(level)

startElement = ET.SubElement(mazeRoot, "StartPoint")
ET.SubElement(startElement, "Row").text = str(startCoords[1])
ET.SubElement(startElement, "Column").text = str(startCoords[0])

escapeElement = ET.SubElement(mazeRoot, "EscapePoint")
ET.SubElement(escapeElement, "Row").text = str(escapeCoords[1])
ET.SubElement(escapeElement, "Column").text = str(escapeCoords[0])

insideElement = ET.SubElement(mazeRoot, "InsideItems")
for y in range(1,HEIGHT-1):
    for x in range(1,WIDTH-1):
        if maze[y*WIDTH + x] == 'x':
            wallElement = ET.SubElement(insideElement, "Wall")
            ET.SubElement(wallElement, "Row").text = str(y+1)
            ET.SubElement(wallElement, "Column").text = str(x+1)

for y in range(HEIGHT):
    for x in range(WIDTH):
        if maze[y*WIDTH + x] == 'h':
            trapElement = ET.SubElement(insideElement, "Trap")
            ET.SubElement(trapElement, "Row").text = str(y+1)
            ET.SubElement(trapElement, "Column").text = str(x+1)

mazeTree = ET.ElementTree(mazeRoot)
ET.indent(mazeTree, space="\t")

path = os.path.join(os.path.abspath(os.path.join(os.path.abspath(__file__), os.pardir, os.pardir)), "test", name + ".txt")
mazeTree.write(path)