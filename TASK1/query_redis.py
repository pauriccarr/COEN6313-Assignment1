import redis
from redis.commands.search.field import TextField, TagField, NumericField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

r = redis.Redis(
    host='river-hypnotic-yarn-78806.db.redis.io',
    port=19665,
    decode_responses=True,
    username="default",
    password="XXX",
)

INDEX_NAME = "prize-index"


def create_index():
    """Create the Redis Search index if it doesn't already exist."""

    try:
        r.ft(INDEX_NAME).dropindex()
        print(f"Dropped index '{INDEX_NAME}'.")
    except Exception as e:
        print(f"Could not drop index: {e}")

    schema = (
        TextField("$.year", as_name="year"),
        TagField("$.category", as_name="category"),
        TextField("$.laureates[*].firstname", as_name="firstname"),
        TextField("$.laureates[*].surname", as_name="surname"),
        TextField("$.laureates[*].motivation", as_name="motivation"),
    )

    r.ft(INDEX_NAME).create_index(
        schema,
        definition=IndexDefinition(
            prefix=["prize:"],
            index_type=IndexType.JSON,
        ),
    )

    print(f"Index '{INDEX_NAME}' created successfully.")


def list_categories():
    """Display all categories."""

    query = Query("*").return_fields("category").paging(0, 1000)

    results = r.ft(INDEX_NAME).search(query)

    categories = set()

    for doc in results.docs:
        categories.add(doc.category)

    categories = sorted(categories)

    print("\nCategories:")

    for i, category in enumerate(categories, 1):
        print(f"{i}. {category}")

    return categories


def search_category():
    """Ask the user for a category and return the number of laureates."""

    categories = list_categories()

    category = input("\nEnter a category: ").strip()

    if category not in categories:
        print("Category not found.")
        return

    query = Query(
        f"@category:{{{category}}}"
    ).paging(0, 1000)

    results = r.ft(INDEX_NAME).search(query)

    # Each document represents a prize/year/category record.
    # Count the laureates inside those documents.
    total_laureates = 0

    for doc in results.docs:
        # Get the original JSON document
        key = doc.id
        data = r.json().get(key)

        if data and "laureates" in data:
            total_laureates += len(data["laureates"])

    print(
        f"\nSearching by Category: "
        f"\nTotal number of laureates in {category}: "
        f"{total_laureates}"
    )


def search_motivation():
    """Search motivations containing a keyword."""
    #print(r.ft("prize-index").info())
    keyword = input(
        "\nEnter a motivation keyword: "
    ).strip()

    if not keyword:
        print("Keyword cannot be empty.")
        return

    query = Query(
        f"@motivation:{keyword}"
    ).paging(0, 1000)

    results = r.ft(INDEX_NAME).search(query)

    total_laureates = 0

    for doc in results.docs:
        key = doc.id
        data = r.json().get(key)

        if data and "laureates" in data:
            # Count only laureates whose motivation contains
            # the keyword.
            for laureate in data["laureates"]:
                motivation = laureate.get("motivation", "")

                if keyword.lower() in motivation.lower():
                    total_laureates += 1

    print(
        f"\nTotal laureates with '{keyword}' "
        f"in their motivation: {total_laureates}"
    )


def search_laureate():
    """Find a laureate by first and last name."""

    firstname = input("\nEnter first name: ").strip()
    surname = input("Enter last name: ").strip()

    # Example Data to use in test
    # firstname = "John"
    # surname = "O'Keefe"
    query = Query(
        f"@firstname:{firstname} @surname:{surname}"
    ).paging(0, 100)



    results = r.ft(INDEX_NAME).search(query)

    if results.total == 0:
        print("\nLaureate not found.")
        return

    for doc in results.docs:

        data = r.json().get(doc.id)

        if not data:
            continue

        for laureate in data.get("laureates", []):
            #print(laureate)
            if (
                laureate.get("firstname", "").lower()
                == firstname.lower()
                and
                laureate.get("surname", "").lower()
                == surname.lower()
            ):
                print("\nLaureate found:")
                print(f"Year: {data.get('year')}")
                print(f"Category: {data.get('category')}")
                print(
                    f"Motivation: "
                    f"{laureate.get('motivation', 'N/A')}"
                )


def main():

    create_index()

    while True:

        print("\n==============================")
        print(" Nobel Prize Search")
        print("==============================")
        print("1) Category")
        print("2) Motivation")
        print("3) Laureate Name")
        print("4) Exit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            search_category()

        elif choice == "2":
            search_motivation()

        elif choice == "3":
            search_laureate()

        elif choice == "4":
            print("Goodbye!")
            break

        else:
            print("Invalid option. Please choose 1-4.")


if __name__ == "__main__":
    main()