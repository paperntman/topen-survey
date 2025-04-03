#!/bin/bash

sudo nohup venv/bin/gunicorn --bind 0:80 main:app &