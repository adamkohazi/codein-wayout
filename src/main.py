import sys
import xml.etree.ElementTree as ET
from enum import Enum
from dataclasses import dataclass
from collections import namedtuple
from typing import NamedTuple

DEBUG_MODE = True

class Coords(NamedTuple):
    x: int
    y: int

class Branch(NamedTuple):
    actions: list
    currentPos: Coords

class Direction(NamedTuple):
    name: str
    code: str
    vector: Coords

class Step(NamedTuple):
    direction: Direction
    cellNumber: int

class Directions(Enum):
    LEFT  = Direction(name='left' , code='1', vector=Coords(x=-1,y= 0))
    RIGHT = Direction(name='right', code='2', vector=Coords(x= 1,y= 0))
    UP    = Direction(name='up'   , code='3', vector=Coords(x= 0,y=-1))
    DOWN  = Direction(name='down' , code='4', vector=Coords(x= 0,y= 1))

# Prints the maze to the console
def printMaze(maze):
    for row in maze:
        print(' '.join([row[x] for x in range(17)]))

# Checks if a point in the maze is a path
def isPath(maze, coords):
    if coords.x < 0 or 17<=coords.x or coords.y < 0 or 17<=coords.y:
        return False
    tile = maze[coords.y][coords.x]
    if tile == ' ' or tile == 's' or tile == 'e':
        return True
    return False

# Returns the 4 surrounding points around a given coordinate
def surroundingCoords(coords):
    return [Coords(x = (coords.x + direction.vector.x), y = (coords.y + direction.vector.y)) for direction in Directions]

# Counts the number of paths leading to a point
def countPaths(maze, coords):
    # Sanity check
    if DEBUG_MODE:
        if not isPath(maze, coords):
            raise ValueError("Can't find options from an invalid position.")
    
    return sum([isPath(maze, coord) for coord in surroundingCoords(coords)])


# Move a point with a given step
def move(maze, startPoint, step):
    endPoint = Coords(x = (startPoint.x + step.cellNumber * step.direction.vector.x), y = (startPoint.y + step.cellNumber * step.direction.vector.y))
    
    # Sanity check
    if DEBUG_MODE:
        for i in range(step.cellNumber):
            midPoint = Coords(x = (startPoint.x + i * step.direction.vector.x), y = (startPoint.y + i * step.direction.vector.y))
            if not isPath(maze, midPoint):
                raise ValueError("Can't move throught invalid points.")

    return endPoint

# Returns a list of "good" options for moving
def findOptions(maze, coords):
    # Sanity check
    if DEBUG_MODE:
        if not isPath(maze, coords):
            raise ValueError("Can't find options from an invalid position.")

    options = []

    # Check all directions radially
    for radialDirection in [d.value for d in Directions]:
        # Virtually walk until a wall (or trap) is hit
        distance = 1
        while(True):
            # Update virtual position
            midPoint = Coords(x = (coords.x + distance * radialDirection.vector.x), y = (coords.y + distance * radialDirection.vector.y))
            # Stop if we've hit a wall
            if(not isPath(maze, midPoint)):
                break

            # Check if projected position has paths joining sideways (corner or intersection)
            if any([isPath(maze, Coords(x = (midPoint.x + direction.vector.x), y = (midPoint.y + direction.vector.y)))
                    for direction in [d.value for d in Directions]
                    if direction.vector.x!=radialDirection.vector.x and direction.vector.y!=radialDirection.vector.y]) or maze[midPoint.y][midPoint.x]=='e':
                options.append(Step(radialDirection, distance))

            # Go one further
            distance += 1
    
    return options   

# Parse maze XML
#mazeXml = sys.argv[1]
with open('./test/example_maze_2.txt', 'r') as file:
    mazeXml = file.read().replace('\n', '')

mazeRoot = ET.fromstring(mazeXml)

level = int(mazeRoot.find('./Level').text)

startRow = int(mazeRoot.find('./StartPoint/Row').text)-1
startColumn = int(mazeRoot.find('./StartPoint/Column').text)-1
startCoords = Coords(startColumn, startRow)

escapeRow = int(mazeRoot.find('./EscapePoint/Row').text)-1
escapeColumn = int(mazeRoot.find('./EscapePoint/Column').text)-1
escapeCoords = Coords(escapeColumn, escapeRow)

# Print the row value
print("Level: ", level)
print("Start: ", startCoords)
print("Escape: ", escapeCoords)

# Parse the walls
# Start blank, fixed 17x17
maze = [[' ' for x in range(17)] for y in range(17)]

# Set the outer walls
for n in range(17):
    maze[ 0][ n] = 'x' # Top edge
    maze[16][ n] = 'x' # Bottom edge
    maze[ n][ 0] = 'x' # Left edge
    maze[ n][16] = 'x' # Right edge

# Set start and escape points
maze[startRow][startColumn] = 's'
maze[escapeRow][escapeColumn] = 'e'

# Set inside walls
for wall in mazeRoot.findall('./InsideItems/Wall'):
    x = int(wall.find('Row').text)-1
    y = int(wall.find('Column').text)-1
    maze[y][x] = 'x'

# Set traps
for trap in mazeRoot.findall('./InsideItems/Trap'):
    x = int(trap.find('Row').text)-1
    y = int(trap.find('Column').text)-1
    maze[y][x] = 'h'

printMaze(maze)

print(findOptions(maze, Coords(15,6)))

branches = [Branch(actions=[], currentPos=startCoords)]

# Update every branch with new moves
finished = False
while(not finished):
    for branch in branches[:]:
        for step in findOptions(maze, branch.currentPos):
            newPos = Coords(x = (branch.currentPos.x + step.cellNumber * step.direction.vector.x), y = (branch.currentPos.y + step.cellNumber * step.direction.vector.y))
            newActions = branch.actions.copy()
            newActions.append(step)
            
            moveCount = len(branch.actions) + 1
            # If position was never reached
            if newPos not in [b.currentPos for b in branches[:]]:
                branches.append(Branch(newActions, newPos))
            
            if newPos == escapeCoords:
                finished = True
    
for branch in branches[:]:
    maze[branch.currentPos.y][branch.currentPos.x] = chr(65+len(branch.actions))

printMaze(maze)