FROM debian:11-slim
RUN mkdir -p "/usr/share/dotnet"
COPY --from=mcr.microsoft.com/dotnet/sdk:6.0 /usr/share/dotnet /usr/share/dotnet
ENV DOTNET_HOME=/usr/share/dotnet
ENV PATH=$DOTNET_HOME:$PATH
ENV SOLUTION_PATH=/usr/dt_maze_challenge/test
ENV LANGUAGE=python

RUN apt-get update && apt-get install -y --no-install-recommends unzip python3 python3-pip

RUN echo Verifying copy in  ... \
    && python3 --version \
    && echo copy Python Complete.

WORKDIR $SOLUTION_PATH

COPY ./src.zip $SOLUTION_PATH/src.zip
RUN unzip $SOLUTION_PATH/src.zip

COPY ./test.zip $SOLUTION_PATH/test.zip
RUN unzip $SOLUTION_PATH/test.zip

WORKDIR $SOLUTION_PATH/test

ENTRYPOINT ["/usr/dt_maze_challenge/test/test/run_example_maze_solution.sh"]