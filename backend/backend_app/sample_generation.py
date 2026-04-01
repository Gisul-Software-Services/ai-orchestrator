import pymongo, datetime

client = pymongo.MongoClient("mongodb+srv://gisul2102_db_user:5cNJ1DcNCxwaJDaU@cluster0.dwcfp0l.mongodb.net/?appName=Cluster0")

client["organization_db"]["organizations"].insert_one({
    "orgId": "admin",
    "name": "Gisul Admin",
    "status": "active",
    "created_at": datetime.datetime.utcnow()
})
print("Done")