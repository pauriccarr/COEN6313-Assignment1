import json
import redis
from redis.commands.search.field import TextField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType

try:
    r = redis.Redis(
        host='river-hypnotic-yarn-78806.db.redis.io',
        port=19665,
        decode_responses=True,
        username="default",
        password="XXXXX",
    )

    with open("nobel_prizes.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0

    for prize in data["prizes"]:
        year = int(prize["year"])

        # Only load 2013 through 2023
        if 2013 <= year <= 2023:
            category = prize["category"]

            key = f"prize:{year}:{category}"

            # Store as native RedisJSON
            r.json().set(key, "$", prize)

            count += 1

    print(f"Loaded {count} prizes into Redis.")

except Exception as e:
    print(f"Error Loading Initial Data to Redis: {e}")

#try:
    # Moved to query_redis function - Pauric
    # schema = (
    #     TextField("$.year", as_name="year"),
    #     TagField("$.category", as_name="category"),
    # )
    #
    #
    # r.ft("prize-index").create_index(
    #     schema,
    #     definition=IndexDefinition(
    #         prefix=["prize:"],
    #         index_type=IndexType.JSON
    #     )
    # )
    # print("Schema Index created Sucessfully !")

# except Exception as e:
#     print(f"Error creating index: {e}")
#
#
#
#
# results = r.ft("prize-index").search("*")
# print(results)