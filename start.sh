#!/bin/bash

sudo tutorial-env/bin/gunicorn --bind 0:80 main:app