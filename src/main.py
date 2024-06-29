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

class Rotate(NamedTuple):
    district: int
    direction: int

class District(NamedTuple):
    xMin: int
    xMax: int
    yMin: int
    yMax: int

districts = {
    1: District( 1,  6,  1,  6),
    2: District( 6, 11,  1,  6),
    3: District(11, 16,  1,  6),
    4: District( 1,  6,  6, 11),
    5: District( 6, 11,  6, 11),
    6: District(11, 16,  6, 11),
    7: District( 1,  6, 11, 16),
    8: District( 6, 11, 11, 16),
    9: District(11, 16, 11, 16)
}

class Branch(NamedTuple):
    actions: list
    currentPos: Coords

    def score(self):
        score = 0
        for action in self.actions:
            if type(action) is Step:
                score += action.cellNumber
            if type(action) is Rotate:
                score += 5
        return score
                

    def toXml(self):
        actionsRoot = ET.Element("Actions")
        for action in self.actions:
            if type(action) is Step:
                stepElement = ET.SubElement(actionsRoot, "Step")
                ET.SubElement(stepElement, "Direction").text = action.direction.name
                ET.SubElement(stepElement, "CellNumber").text = str(action.cellNumber)

            elif type(action) is Rotate:
                rotateElement = ET.SubElement(actionsRoot, "Rotate")
                ET.SubElement(rotateElement, "District").text = str(action.district)
                ET.SubElement(rotateElement, "Direction").text = str(action.direction)
        
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
    
    def rotate(self, rotate):
        xMin, xMax, yMin, yMax = districts[rotate.district]
        district = [[self.grid[y][x]
                     for x in range(xMin, xMax)]
                    for y in range(yMin, yMax)]

        rotatedDistrict = [['' for x in range(5)] for y in range(5)]
        for y in range(5):
            for x in range(5):
                if rotate.direction == 1: #ccw
                    rotatedDistrict[y][x] = district[x][4-y]
                elif rotate.direction == 2: #cw
                    rotatedDistrict[y][x] = district[4-x][y]
                else:
                    print("Invalid direction")
        
        for y in range(5):
            for x in range(5):
                self.grid[yMin + y][xMin + x] = rotatedDistrict[y][x]

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

    # Benchmarks diffuclty of current maze.
    # 1: Simple, no traps.
    # 2: Traps, but clear path to exit.
    # 3: No clear path to exit.
    def determineLevel(self):
        trapsPresent = False
        mazeWithoutTrap = copy.deepcopy(self)
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                if self.grid[y][x] == 'h':
                    trapsPresent = True
                    mazeWithoutTrap.grid[y][x] = ' '
        
        if mazeWithoutTrap.findShortestPathSimple(None, Branch(actions=[], currentPos=self.startCoords), self.escapeCoords) is None:
            # If it is not solvable, even without traps
            return 3
        else:
            if trapsPresent:
                # it is solvable, but there are traps
                return 2
            else:
                # easy-peasy
                return 1

    # Counts the number of paths leading to a point
    def countPaths(self, coords):
        # Sanity check
        if DEBUG_MODE:
            if not self.isPath(coords):
                raise ValueError("Can't find options from an invalid position.")
        
        return sum([self.isPath(coord) for coord in coords.surrounding()])

    """
    def findSteps(self, coords, includeTraps=True):
        # Sanity check
        if DEBUG_MODE:
            if not self.isPath(coords, includeTraps):
                raise ValueError("Can't find options from an invalid position.")

        options = []

        # Check all directions radially
        for radialDirection in [d.value for d in Directions]:
            # Update virtual position
            step = Step(direction = radialDirection, cellNumber = 1)
            midPoint = coords + step
            if self.isPath(midPoint, includeTraps):
                options.append(step)

        return options
    """

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

    def findShortestPathSimple(self, par, startBranch, endCoords):       
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
                    if branch.score() >= par:
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

    def findShortestPathComplex(self, par, startBranch, endCoords):
        # Only information in the beginning is that start can be reached in 0 steps.
        branches = [startBranch]

        # Try to find a simple solution, to set a par:
        simpleBranch = self.findShortestPathSimple(par, startBranch, endCoords)
        if simpleBranch:
            branches.append(simpleBranch)
            if par:
                par = min(par, simpleBranch.score())
            else:
                par = simpleBranch.score()

        # Flags to indicate status
        anyImprovement = True

        # Update every branch with new moves
        while(anyImprovement):
            # Reset flag every iteration
            anyImprovement = False

            # Update all branches
            for branch in branches[:]:
                # If branch has already finished, no need to update
                if branch.currentPos == endCoords:
                    continue
                
                # If branch is already longer than par, no need to update
                if par:
                    if branch.score() >= par:
                        continue
                if DEBUG_MODE:
                    print("par: %d, current: %d" % (par, branch.score()))
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
                        newBranch = mazeWithoutTrap.findShortestPath(par, startBranch = preBranch, endCoords=endCoords)
                        # If maze without trap is solvable
                        if newBranch:
                            if DEBUG_MODE:
                                print("Good news, alternative maze was solved:")
                                mazeWithoutTrap.print()
                                print("Score: ", str(newBranch.score()))
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
                        newBranch = Branch(newActions, newPos)

                    newScore = newBranch.score()
                    
                    # Try to find new position in positions that are already reached
                    neverBeenVisited=True
                    for existingBranch in branches[:]:
                        # Do not try to improve current branch, as it will lead to skipped steps
                        if branch is existingBranch:
                            continue
                        if existingBranch.currentPos == newPos:
                            neverBeenVisited=False
                            # If new path is shorter, replace the existing one
                            if newScore < existingBranch.score():
                                if False and DEBUG_MODE:
                                    print("Position already reached:")
                                    print("Coords: ", str(newPos))
                                    print("Previously: ", str(existingBranch.score()))
                                    print("Now: ", str(newScore))
                                branches.append(newBranch)
                                branches.remove(existingBranch)
                                anyImprovement = True

                    if neverBeenVisited:
                        if False and DEBUG_MODE:
                            print("New position reached:")
                            print("Coords: ", str(newPos))
                            print("Score: ", str(newScore))
                        branches.append(newBranch)
                        anyImprovement = True
                    
                    # Update par
                    if newPos == endCoords:
                        if par:
                            par = min(par, newScore)
                        else:
                            par = newScore
                       

        for branch in branches:
            if branch.currentPos == endCoords:
                return branch

        if DEBUG_MODE:
            print("Oh no...No branches are reaching the end coordinates under par")

    def findShortestPathVeryComplex(self, par, startBranch, endCoords, rotations=0):
        if rotations>2:
            if DEBUG_MODE:
                print("in too deep")
            return None

        # Try to find a solution without rotation, to set a par:
        solution = self.findShortestPathComplex(par, startBranch, endCoords)

        # Trial and error until time runs out. No idea how to solve this using logic, so we'll just brute force it.
        while time.time() - start_time < TIME_LIMIT:
            for district in range(1,10):
                for direction in (1,2):
                    # Simulate what would happen if we rotated:
                        rotation = Rotate(district, direction)
                        rotatedMaze = copy.deepcopy(self)
                        rotatedMaze.rotate(rotation)
                        preBranch = copy.deepcopy(startBranch)
                        preBranch.actions.append(rotation)
                        # Try to solve it (limit level to 2 to reduce time):
                        newBranch = rotatedMaze.findShortestPath(par, preBranch, endCoords, rotations=rotations+1)
                        if newBranch:
                            if DEBUG_MODE:
                                rotatedMaze.print()
                                print("score: %d" % (newBranch.score()))
                            if solution:
                                if newBranch.score() < solution.score():
                                    solution = newBranch
                            else:
                                solution = newBranch

        return solution

    def findShortestPath(self, par=None, startBranch=None, startCoords=None, endCoords=None, level=None, rotations=0):
        # Use start and escape points of maze as default
        if startBranch is None:
            if startCoords is None:
                startCoords = self.startCoords
            startBranch = Branch(actions=[], currentPos=startCoords)
        if endCoords is None:
            endCoords = self.escapeCoords
        
        if par:
            if startBranch.score() >= par:
                return None
        else:
            if startBranch.score() >= 50:
                return None
        
        # If more difficult than expected level, it's unsolvable
        if level is None:
            level = self.determineLevel()
        if level > self.level:
            if DEBUG_MODE:
                print("Too difficult for this level, unsolvable.")
            return None
        if level==3:
            return self.findShortestPathVeryComplex(par, startBranch, endCoords, rotations=rotations)
        if level==2:
            return self.findShortestPathComplex(par, startBranch, endCoords)
        if level==1:
            return self.findShortestPathSimple(par, startBranch, endCoords)
            

# Init maze from command line argument
maze = Maze(sys.argv[1])
#maze.print()
#maze.rotate(Rotate(7, 1))
#maze.rotate(Rotate(2, 2))
#maze.print()
branch = maze.findShortestPath()
print(branch.toXml())
if DEBUG_MODE:
    print("Score: ", branch.score())
