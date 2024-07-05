import sys
import xml.etree.ElementTree as ET
from typing import NamedTuple
from dataclasses import dataclass

class Coords(NamedTuple):
    x: int
    y: int

def taxicabDistance(startCoords: Coords, endCoords: Coords) -> int:
    return abs(startCoords.x - endCoords.x) + abs(startCoords.y - endCoords.y)

class Direction(NamedTuple):
    name: str
    code: str
    vector: Coords

Directions = (
    Direction(name='left' , code='1', vector=Coords(x=-1,y= 0)),
    Direction(name='right', code='2', vector=Coords(x= 1,y= 0)),
    Direction(name='up'   , code='3', vector=Coords(x= 0,y=-1)),
    Direction(name='down' , code='4', vector=Coords(x= 0,y= 1)))

class Step(NamedTuple):
    direction: Direction
    cellNumber: int
    endsOnTrap: bool = None

@dataclass
class Branch():
    actions: list
    currentPos: Coords
    new: bool = True
    score: int = 0
                
    def toXml(self):
        actionsRoot = ET.Element("Actions")
        for action in self.actions:
            stepElement = ET.SubElement(actionsRoot, "Step")
            ET.SubElement(stepElement, "Direction").text = action.direction.code
            ET.SubElement(stepElement, "CellNumber").text = str(action.cellNumber)
        
        return ET.tostring(actionsRoot, encoding='unicode')

class Maze(object):
    """Class for keeping track of and interacting with a maze.
    """

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

        # Parse the walls
        # Start blank
        self.grid = [[' ' for x in range(17)] for y in range(17)]

        # Set the top and bottom walls
        for x in range(17):
            self.grid[0][x] = 'x'
            self.grid[17-1][x] = 'x'
        
        # Set the left and right walls
        for y in range(17):
            self.grid[y][0] = 'x'
            self.grid[y][17-1] = 'x'

        # Set start and escape points
        self.grid[startRow][startColumn] = 's'
        self.grid[escapeRow][escapeColumn] = 'e'

        # Set inside walls
        for wall in mazeRoot.findall('./InsideItems/Wall'):
            y = int(wall.find('Row').text)-1
            x = int(wall.find('Column').text)-1
            self.grid[y][x] = 'x'

        # Set traps
        for trap in mazeRoot.findall('./InsideItems/Trap'):
            y = int(trap.find('Row').text)-1
            x = int(trap.find('Column').text)-1
            self.grid[y][x] = 'h'
    
    # Prints the maze to the console
    def print(self):
        for row in  self.grid:
            print(' '.join([row[x] for x in range(17)]))

    # Returns a list of "good" options for moving
    #@profile
    def findSteps(self, coords: Coords, includeTraps=True):
        options = []

        # Check all directions radially
        for radialDirection in Directions:
            # Virtually walk until a wall (or trap) is hit
            distance = 1
            while(True):
                # Update virtual position
                midPointX = coords.x + distance * radialDirection.vector.x
                midPointY = coords.y + distance * radialDirection.vector.y

                if midPointX < 0 or 17<=midPointX or midPointY < 0 or 17<=midPointY:
                    break

                # Check if we end on a trap:
                tile = self.grid[midPointY][midPointX]
                isTrap = tile == 'h'

                # Stop if we've hit a wall (or trap, if set)
                if tile == 'x' or (not includeTraps and isTrap):
                    break
                
                if tile =='e':
                    options.append(Step(direction=radialDirection, cellNumber=distance, endsOnTrap=isTrap))
                    break

                # Check if projected position may lead to new points
                for d in Directions:
                    if (d.vector.x == -radialDirection.vector.x) or (d.vector.y == -radialDirection.vector.y):
                        continue
                    newCoordsX = midPointX + d.vector.x
                    newCoordsY = midPointY + d.vector.y
                    if newCoordsX < 0 or 17<=newCoordsX or newCoordsY < 0 or 17<=newCoordsY:
                        continue
                    tile = self.grid[newCoordsY][newCoordsX]
                    if (tile == ' ' or tile == 's' or tile == 'e') or (includeTraps and tile == 'h'):
                        options.append(Step(direction=radialDirection, cellNumber=distance, endsOnTrap=isTrap))
                        break

                # Stop moving further if we've hit a trap
                if isTrap:
                    nextX = midPointX + radialDirection.vector.x
                    nextY = midPointX + radialDirection.vector.x
                    tile = self.grid[nextY][nextX]
                    if (tile == ' ' or tile == 's' or tile == 'e'):
                        options.append(Step(direction=radialDirection, cellNumber=distance, endsOnTrap=isTrap))
                    break

                # Go one further
                distance += 1

        return options

    #@profile
    def findShortestPath(self, par: int, includeTraps: bool = True):       
        # Only information in the beginning is how to reach the start.
        branches = [Branch([], self.startCoords, True, 0)]

        # Try to find path, until solution is found, or there are no new branches that could finish under par
        while(True):
            # Only check newly created branches (that have not yet been checked)
            for branch in [b for b in branches if b.new]:
                # Set to updated
                branch.new = False

                # Don't bother if it has no chance to finish under par
                if branch.score + taxicabDistance(branch.currentPos, self.escapeCoords) > par:
                    continue

                # Evaluate all valid steps
                for step in self.findSteps(branch.currentPos, includeTraps=includeTraps):

                    # Check if we land on a trap:
                    if step.endsOnTrap:
                        # Find the last time we've hit a trap and repeat movements since
                        newScore = branch.score + step.cellNumber
                        actionsToRepeat = []
                        for action in reversed(branch.actions):
                            if action.endsOnTrap is True:
                                break
                            newScore += action.cellNumber
                            actionsToRepeat.append(action)
                        newScore += step.cellNumber
                        newActions = branch.actions.copy() + [step] + list(reversed(actionsToRepeat)) + [Step(step.direction, step.cellNumber, endsOnTrap=False)]
                    
                    # Just a simple step
                    else:      
                        newActions = branch.actions.copy() + [step]
                        newScore = branch.score + step.cellNumber
                    
                    #newPos = branch.currentPos + step
                    newPos = Coords(x = (branch.currentPos.x + step.cellNumber * step.direction.vector.x), y = (branch.currentPos.y + step.cellNumber * step.direction.vector.y))

                    # Don't bother if it has no chance to finish under par
                    if newScore + taxicabDistance(newPos, self.escapeCoords) > par:
                        continue

                    # Try to find new position in positions that are already reached
                    neverBeenVisited=True
                    for otherBranch in [b for b in branches if b.currentPos == newPos and b is not branch]:
                        neverBeenVisited=False
                        # If new path is shorter, replace the existing one
                        if newScore < otherBranch.score:
                            otherBranch.actions = newActions
                            otherBranch.new = True
                            otherBranch.score = newScore
                            break

                    if neverBeenVisited:
                        branches.append(Branch(newActions, newPos, True, newScore))
                    
                    if newPos == self.escapeCoords and newScore < par:
                        return Branch(newActions, newPos, True, newScore)

#Init maze from file (for testing)
#with open("test/trap_hard.txt","r") as f:
#    arg = f.read()
#maze = Maze(arg)

#Init maze from command line argument
maze = Maze(sys.argv[1])

if maze.level==1:
    print(maze.findShortestPath(67, includeTraps=False).toXml()) #66
if maze.level==2:
    print(maze.findShortestPath(92, includeTraps=True).toXml()) #91
if maze.level==3:
    print(maze.findShortestPath(31, includeTraps=False).toXml()) #30