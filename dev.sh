#!/usr/bin/env bash

VOLUME_MAPPINGS=()
PROJECT_DIR=$(dirname $(readlink -f $0))
VOLUME_MAPPINGS+=" -v $PROJECT_DIR:/home/devel/workspace"

if [ -e $HOME/.gitconfig ]; then
    VOLUME_MAPPINGS+=" -v $HOME/.gitconfig:/home/devel/.gitconfig"
fi

if [ -e $HOME/.ssh ]; then
    VOLUME_MAPPINGS+=" -v $HOME/.ssh:/home/devel/.ssh"
fi

if [ -e $HOME/.pypirc ]; then
    VOLUME_MAPPINGS+=" -v $HOME/.pypirc:/home/devel/.pypirc"
fi

docker run -it --rm ${VOLUME_MAPPINGS} $(docker build -q $PROJECT_DIR) $@