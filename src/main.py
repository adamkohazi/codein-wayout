import sys
import xml.etree.ElementTree as ET
from enum import Enum
from typing import NamedTuple
import copy
import time

DEBUG_MODE = False
TIME_LIMIT = 55

start_time = time.time()

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
    def isPath(self, coords, includeTraps=True):
        if coords.x < 0 or self.WIDTH<=coords.x or coords.y < 0 or self.HEIGHT<=coords.y:
            return False
        tile = self.grid[coords.y][coords.x]
        if includeTraps:
            return tile == ' ' or tile == 's' or tile == 'e' or tile == 'h'
        else:
            return tile == ' ' or tile == 's' or tile == 'e'

    # Checks if a point in the maze is a trap.
    def isTrap(self, coords):
        return self.grid[coords.y][coords.x] == 'h'

    # Checks if maze is simple. (No traps)
    def isSimple(self):
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                if self.grid[y][x] == 'h':
                    return False
        return True

    # Counts the number of paths leading to a point
    def countPaths(self, coords):
        # Sanity check
        if DEBUG_MODE:
            if not self.isPath(coords):
                raise ValueError("Can't find options from an invalid position.")
        
        return sum([self.isPath(coord) for coord in coords.surrounding()])

    # Returns a list of "good" options for moving
    def findSteps(self, coords, includeTraps=True):
        # Sanity check
        if DEBUG_MODE:
            if not self.isPath(coords, includeTraps):
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
                if(not self.isPath(midPoint, includeTraps)):
                    break

                # Check if projected position has paths joining sideways (corner or intersection)
                if any([self.isPath(midPoint + Step(direction=direction, cellNumber=1), includeTraps)
                        for direction in [d.value for d in Directions]
                        if direction.vector.x!=radialDirection.vector.x and direction.vector.y!=radialDirection.vector.y]) or self.grid[midPoint.y][midPoint.x]=='e':
                    options.append(Step(radialDirection, distance))

                # Go one further
                distance += 1
        return options
    
    def detectTrap(self, startCoords, step):
        for distance in range(1,1+step.cellNumber):
            midPoint = startCoords + Step(direction = step.direction, cellNumber = distance)
            if self.isTrap(midPoint):
                return midPoint
        return None

    def findShortestPathSimple(self, par=None, startBranch=None, startCoords=None, endCoords=None):
        # Use start and escape points of maze as default
        if startBranch is None:
            if startCoords is None:
                startCoords = self.startCoords
            startBranch = Branch(actions=[], currentPos=startCoords)
        if endCoords is None:
            endCoords = self.escapeCoords
        
        # Only information in the beginning is how to reach the start.
        branches = [startBranch]

        anyImprovement = True
        # Update every branch with new moves
        while(anyImprovement):
            # Simple solver doesn't check time, there's no faster way

            # Reset flag every iteration
            anyImprovement = False

            # Update all branches
            for branch in branches[:]:
                # If branch is already longer than par, no need to update
                if par:
                    if len(branch.actions) >= par:
                        continue
                # Evaluate all valid steps
                for step in self.findSteps(branch.currentPos, includeTraps=False):
                    newPos = branch.currentPos + step
                    newActions = branch.actions.copy()
                    newActions.append(step)
                    
                    # Try to find new position in positions that are already reached
                    neverBeenVisited=True
                    for existingBranch in branches[:]:
                        # Do not try to improve current branch, as it will lead to skipped steps
                        if branch is existingBranch:
                            continue
                        if existingBranch.currentPos == newPos:
                            neverBeenVisited=False
                            # BFS, existing paths are always shorter
                            """
                            if len(newActions) < len(existingBranch.actions):
                                if DEBUG_MODE:
                                    print("Position already reached:")
                                    print("Coords: ", str(newPos))
                                    print("Previously: ", str(len(existingBranch.actions)))
                                    print("Now: ", str(len(newActions)))
                                branches.append(Branch(newActions, newPos))
                                branches.remove(existingBranch)
                                anyImprovement = True
                            """
                    if neverBeenVisited:
                        if DEBUG_MODE:
                            print("New position reached:")
                            print("Coords: ", str(newPos))
                            print("Steps: ", str(len(newActions)))
                        if newPos==endCoords:
                            return Branch(newActions, newPos)
                        branches.append(Branch(newActions, newPos))
                        anyImprovement = True
        if DEBUG_MODE:
            print("Oh no...No branches are reaching the end coordinates")

    def findShortestPathComplex(self, par=None, startBranch=None, startCoords=None, endCoords=None):
        # Use start and escape points of maze as default
        if startBranch is None:
            if startCoords is None:
                startCoords = self.startCoords
            startBranch = Branch(actions=[], currentPos=startCoords)
        if endCoords is None:
            endCoords = self.escapeCoords

        # Only information in the beginning is that start can be reached in 0 steps.
        branches = [startBranch]

        # Try to find a simple solution, so we have something if complex fails:
        simpleBranch = self.findShortestPathSimple(par, startBranch, startCoords, endCoords)
        if simpleBranch:
            if self.isSimple():
                return simpleBranch
            branches.append(simpleBranch)
            if par:
                par = min(par, len(simpleBranch.actions))
            else:
                par = len(simpleBranch.actions)

        # Flags to indicate status
        anyImprovement = True

        # Update every branch with new moves
        while(anyImprovement):
            # If time limit is reached, return best so far:
            if time.time() - start_time > TIME_LIMIT:
                if DEBUG_MODE:
                    print("Time's up, here's the best so far:")
                return min([branch for branch in branches if branch.currentPos==endCoords], key=lambda x: len(x.actions))

            # Reset flag every iteration
            anyImprovement = False

            # Update all branches
            for branch in branches[:]:
                # If branch has already finished, no need to update
                if branch.currentPos == endCoords:
                    continue
                
                # If branch is already longer than par, no need to update
                if par:
                    if len(branch.actions) >= par:
                        continue
                if DEBUG_MODE:
                    print("par: %d, current: %d" % (par, len(branch.actions)))
                # Evaluate all valid steps
                for step in self.findSteps(branch.currentPos):

                    # Check if we cross or land on a trap:
                    trapCoords = self.detectTrap(branch.currentPos, step)
                    if trapCoords:
                        # Simulate what would happen if we walked into it:
                        mazeWithoutTrap = copy.deepcopy(self)
                        mazeWithoutTrap.grid[trapCoords.y][trapCoords.x] = ' '
                        if DEBUG_MODE:
                            print("Branching, alternative maze looks like this:")
                            mazeWithoutTrap.print()
                        preActions = branch.actions.copy()
                        preActions.append(step)
                        preBranch = Branch(actions=preActions, currentPos=mazeWithoutTrap.startCoords)
                        newBranch = mazeWithoutTrap.findShortestPathComplex(par, startBranch = preBranch)
                        # If maze without trap is solvable
                        if newBranch:
                            if DEBUG_MODE:
                                print("Good news, alternative maze was solved:")
                                mazeWithoutTrap.print()
                                print("Steps: ", str(len(newBranch.actions)))
                                print("Here's the solution:")
                                print(newBranch.toXml())
                            newPos = newBranch.currentPos
                            newActions = newBranch.actions.copy()
                        else:
                            if DEBUG_MODE:
                                print("Oh no, solving the alternative maze was not possible, not sure what to do now")
                            continue
                    else:
                        newPos = branch.currentPos + step
                        newActions = branch.actions.copy()
                        newActions.append(step)
                    
                    # Try to find new position in positions that are already reached
                    neverBeenVisited=True
                    for existingBranch in branches[:]:
                        # Do not try to improve current branch, as it will lead to skipped steps
                        if branch is existingBranch:
                            continue
                        if existingBranch.currentPos == newPos:
                            neverBeenVisited=False
                            # If new path is shorter, replace the existing one
                            if len(newActions) < len(existingBranch.actions):
                                if False and DEBUG_MODE:
                                    print("Position already reached:")
                                    print("Coords: ", str(newPos))
                                    print("Previously: ", str(len(existingBranch.actions)))
                                    print("Now: ", str(len(newActions)))
                                branches.append(Branch(newActions, newPos))
                                branches.remove(existingBranch)
                                anyImprovement = True

                    if neverBeenVisited:
                        if False and DEBUG_MODE:
                            print("New position reached:")
                            print("Coords: ", str(newPos))
                            print("Steps: ", str(len(newActions)))
                        branches.append(Branch(newActions, newPos))
                        anyImprovement = True
                    
                    # Update par
                    if newPos == endCoords:
                        if par:
                            par = min(par, len(newActions))
                        else:
                            par = len(newActions)
                       

        for branch in branches:
            if branch.currentPos == endCoords:
                return branch

        if DEBUG_MODE:
            print("Oh no...No branches are reaching the end coordinates under par")

# Init maze from command line argument
maze = Maze(sys.argv[1])
print(maze.findShortestPathComplex().toXml())
