This directory contains the required build files, a source code base and a tester Docker file.

Don't change the build files, because during the score calculation these will be used!
You can test the building and the solution code with the Dockerfile, but first you need to install Docker Desktop application!

Usage:
Place every provided file (Dockerfile, test.zip, build files) and the modified src.zip in one directory and open command line.
docker build --tag dt_maze_challenge .
docker run --rm -it dt_maze_challenge [LEVEL] visualize
	LEVEL: The tested level value. Valid values: 1-3
	visualize: Parameter is optional, if not passed then console logs out only the last stage of solving the maze