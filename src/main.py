import sys
import xml.etree.ElementTree as ET
from enum import Enum
from typing import NamedTuple
import copy

DEBUG_MODE = False

class Coords(NamedTuple):
    x: int
    y: int

    def __add__(self, step: 'Step'):
        return Coords(x = (self.x + step.cellNumber * step.direction.vector.x), y = (self.y + step.cellNumber * step.direction.vector.y))
    
    def surrounding(self):
        return [Coords(x = (self.x + direction.vector.x), y = (self.y + direction.vector.y)) for direction in Directions]

class Direction(NamedTuple):
    name: str
    code: str
    vector: Coords

class Directions(Enum):
    LEFT  = Direction(name='left' , code='1', vector=Coords(x=-1,y= 0))
    RIGHT = Direction(name='right', code='2', vector=Coords(x= 1,y= 0))
    UP    = Direction(name='up'   , code='3', vector=Coords(x= 0,y=-1))
    DOWN  = Direction(name='down' , code='4', vector=Coords(x= 0,y= 1))

class Step(NamedTuple):
    direction: Direction
    cellNumber: int

class Branch(NamedTuple):
    actions: list
    currentPos: Coords

    def toXml(self):
        actionsRoot = ET.Element("Actions")
        for action in self.actions:
            if type(action) is Step:
                stepElement = ET.SubElement(actionsRoot, "Step")
                ET.SubElement(stepElement, "Direction").text = action.direction.name
                ET.SubElement(stepElement, "CellNumber").text = str(action.cellNumber)
        
        actionsTree = ET.ElementTree(actionsRoot)
        ET.indent(actionsTree, space="\t")
        return ET.tostring(actionsRoot, encoding='unicode')

class Maze(object):
    """Class for keeping track of and interacting with a maze.
    """

    # Project constants
    WIDTH = 17
    HEIGHT = 17

    def __init__(self, mazeXml):
        # Parse maze XML
        mazeRoot = ET.fromstring(mazeXml)

        self.level = int(mazeRoot.find('./Level').text)

        startRow = int(mazeRoot.find('./StartPoint/Row').text)-1
        startColumn = int(mazeRoot.find('./StartPoint/Column').text)-1
        self.startCoords = Coords(startColumn, startRow)

        escapeRow = int(mazeRoot.find('./EscapePoint/Row').text)-1
        escapeColumn = int(mazeRoot.find('./EscapePoint/Column').text)-1
        self.escapeCoords = Coords(escapeColumn, escapeRow)

        # Print the row value
        if DEBUG_MODE:
            print("Level: ", self.level)
            print("Start: ", self.startCoords)
            print("Escape: ", self.escapeCoords)

        # Parse the walls
        # Start blank, fixed 17x17
        self.grid = [[' ' for x in range(17)] for y in range(17)]

        # Set the top and bottom walls
        for n in range(self.WIDTH):
            self.grid[ 0][ n] = 'x'
            self.grid[self.HEIGHT-1][ n] = 'x'
        
        # Set the left and right walls
        for n in range(self.WIDTH):
            self.grid[ n][ 0] = 'x'
            self.grid[ n][self.HEIGHT-1] = 'x'

        # Set start and escape points
        self.grid[startRow][startColumn] = 's'
        self.grid[escapeRow][escapeColumn] = 'e'

        # Set inside walls
        for wall in mazeRoot.findall('./InsideItems/Wall'):
            x = int(wall.find('Row').text)-1
            y = int(wall.find('Column').text)-1
            self.grid[y][x] = 'x'

        # Set traps
        for trap in mazeRoot.findall('./InsideItems/Trap'):
            x = int(trap.find('Row').text)-1
            y = int(trap.find('Column').text)-1
            self.grid[y][x] = 'h'

        # Visualize the result
        if DEBUG_MODE:
            self.print()

    # Prints the maze to the console
    def print(self):
        for row in  self.grid:
            print(' '.join([row[x] for x in range(self.WIDTH)]))

    # Checks if a point in the maze is a path. Traps are considered as path, their effect is handled later.
    def isPath(self, coords):
        if coords.x < 0 or self.WIDTH<=coords.x or coords.y < 0 or self.HEIGHT<=coords.y:
            return False
        tile = self.grid[coords.y][coords.x]
        if tile == ' ' or tile == 's' or tile == 'e' or tile == 'h':
            return True
        return False

    # Checks if a point in the maze is a trap.
    def isTrap(self, coords):
        return self.grid[coords.y][coords.x] == 'h'

    # Counts the number of paths leading to a point
    def countPaths(self, coords):
        # Sanity check
        if DEBUG_MODE:
            if not self.isPath(coords):
                raise ValueError("Can't find options from an invalid position.")
        
        return sum([self.isPath(coord) for coord in coords.surrounding()])

    # Returns a list of "good" options for moving
    def findSteps(self, coords):
        # Sanity check
        if DEBUG_MODE:
            if not self.isPath(coords):
                raise ValueError("Can't find options from an invalid position.")

        options = []

        # Check all directions radially
        for radialDirection in [d.value for d in Directions]:
            # Virtually walk until a wall (or trap) is hit
            distance = 1
            while(True):
                # Update virtual position
                midPoint = coords + Step(direction = radialDirection, cellNumber = distance)
                # Stop if we've hit a wall
                if(not self.isPath(midPoint)):
                    break

                # Check if projected position has paths joining sideways (corner or intersection)
                if any([self.isPath(midPoint + Step(direction=direction, cellNumber=1))
                        for direction in [d.value for d in Directions]
                        if direction.vector.x!=radialDirection.vector.x and direction.vector.y!=radialDirection.vector.y]) or self.grid[midPoint.y][midPoint.x]=='e':
                    options.append(Step(radialDirection, distance))

                # Go one further
                distance += 1
        return options
    
    def deactivateTrap(self, startCoords, step):
        for distance in range(step.cellNumber)+1:
            midPoint = startCoords + Step(direction = step.direction, cellNumber = distance)
            if self.isTrap(midPoint):
                self.grid[midPoint.y][midPoint.x] = ' '
                return True
        return False

    def findShortestPath(self, startCoords=None, endCoords=None, modifyMaze=False):
        # Use start and escape points of maze as default
        if startCoords is None:
            startCoords = self.startCoords
        if endCoords is None:
            endCoords = self.escapeCoords

        # Only information in the beginning is that start can be reached in 0 steps.
        branches = [Branch(actions=[], currentPos=startCoords)]

        # Flags to indicate status
        endCoordReached = False
        anyImprovement = True

        # Update every branch with new moves
        while((not endCoordReached) and anyImprovement):
            # Reset flag every iteration
            anyImprovement = False

            # Update all branches
            for branch in branches[:]:
                # Evaluate all valid steps
                for step in self.findSteps(branch.currentPos):
                    # Check if we cross or land on a trap:
                    if self.deactivateTrap(branch.currentPos, step):
                        newPos = self.startCoords
                    else:
                        newPos = branch.currentPos + step
                    newActions = branch.actions.copy()
                    newActions.append(step)

                    moveCount = len(branch.actions) + 1
                    
                    # If position was never reached
                    if newPos not in [b.currentPos for b in branches[:]]:
                        newBranch = Branch(newActions, newPos)
                        branches.append(newBranch)
                        anyImprovement = True
                    
                        if newPos == endCoords:
                            endCoordReached = True
                    
        
        if DEBUG_MODE:
            for branch in branches:
                self.grid[branch.currentPos.y][branch.currentPos.x] = chr(65+len(branch.actions))
            
            self.print()
        
        for branch in branches:
            if branch.currentPos == endCoords:
                return branch

        print("Oh no...No branches are reaching the end coordinates")

    def findShortestPathTraps(self, startCoords=None, endCoords=None):
        # Make a copy of the grid, we'll need to modify it due to traps.
        currentMaze = copy.copy(self)

        return currentMaze.findShortestPath(startCoords, endCoords, modifyMaze=True)

# Init maze from command line argument
maze = Maze(sys.argv[1])
if(maze.level == 1):
    print(maze.findShortestPath().toXml())
