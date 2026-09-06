#!/bin/bash
echo "Backing up Redis cache..."
docker exec redis redis-cli SAVE
