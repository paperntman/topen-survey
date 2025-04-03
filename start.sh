#!/bin/bash

sudo nohup tutorial-env/bin/gunicorn --bind 0:80 main:app &