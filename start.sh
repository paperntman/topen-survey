#!/bin/bash

git pull origin master
sudo tutorial-env/bin/gunicorn main:app