#!/bin/bash

HOST="https://""github.com"

git remote set-url tigr "$HOST/Tigr6446/TG_Bot.git" 2>/dev/null || git remote add tigr "$HOST/Tigr6446/TG_Bot.git"
git remote set-url mirier "$HOST/mirier1/TG_Bot.git" 2>/dev/null || git remote add mirier "$HOST/mirier1/TG_Bot.git"

git fetch tigr main
git fetch mirier main

TIGR_TIME=$(git log -1 --format=%ct tigr/main)
MIRIER_TIME=$(git log -1 --format=%ct mirier/main)

if [ "$MIRIER_TIME" -gt "$TIGR_TIME" ]; then
    echo "🚀 Выбран свежий форк Mirier"
    git reset --hard mirier/main
else
    echo "🚀 Выбран основной репозиторий Tigr6446"
    git reset --hard tigr/main
fi

pip install -r requirements.txt
