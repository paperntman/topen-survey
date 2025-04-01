#!/bin/bash

clear
gunicorn --bind 0.0.0.0:80 main:app