#!/bin/bash

usage()
{
    echo "Usage:"
    echo "./reload.sh [--disable] [--enable] [--help]"
    exit
}

ENABLE="NO"
DISABLE="NO"
while [ $# -gt 0 ]
do
    key="$1"

    case $key in
        -e|--enable)
        ENABLE="YES"
        ;;
        -d|--disable)
        DISABLE="YES"
        ;;
        -h|--help)
        usage
        ;;
        *)
        echo "Unknown option"
        usage
        ;;
    esac
    shift # past argument or value
done

if [[ "${DISABLE}" == "YES" ]]; then
    echo "disabling reload (release)"
    find . -regex ".*\.py" -exec sed -i -e 's/^importlib.reload/#importlib.reload/g' {} \;
    exit
fi

if [[ "${ENABLE}" == "YES" ]]; then
    echo "enabling reload (during development)"
    find . -regex ".*\.py" -exec sed -i -e 's/^#importlib.reload/importlib.reload/g' {} \;
    exit
fi

echo "WARNING: requires an argument"
usage
