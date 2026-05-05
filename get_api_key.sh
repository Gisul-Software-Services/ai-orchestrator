#!/bin/bash
# Retrieve ORG003's API key from MongoDB

mongosh "mongodb+srv://gisul2102_db_user:5cNJ1DcNCxwaJDaU@cluster0.dwcfp0l.mongodb.net/aaptor_model?appName=Cluster0" --quiet --eval "
  db.api_keys.findOne({org_id: 'ORG003'}, {key: 1, _id: 0})
"
