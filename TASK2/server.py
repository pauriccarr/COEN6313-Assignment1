import os
import re
from concurrent import futures

import grpc
import redis
from redis.commands.search.field import TagField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

import category_pb2
import category_pb2_grpc
import laureate_pb2
import laureate_pb2_grpc
import motivation_pb2
import motivation_pb2_grpc

INDEX_NAME = "prize-index"

# Credentials come from the environment, never from source code.
r = redis.Redis(
    host="river-hypnotic-yarn-78806.db.redis.io",
    port="19665",
    username="default",
    password="XXX",
    decode_responses=True,
)


def ensure_index():
    """Create the search index only if it doesn't exist yet."""
    try:
        r.ft(INDEX_NAME).info()
        return
    except Exception:
        pass

    schema = (
        TextField("$.year", as_name="year"),
        TagField("$.category", as_name="category"),
        TextField("$.laureates[*].firstname", as_name="firstname"),
        TextField("$.laureates[*].surname", as_name="surname"),
        TextField("$.laureates[*].motivation", as_name="motivation"),
    )
    r.ft(INDEX_NAME).create_index(
        schema,
        definition=IndexDefinition(prefix=["prize:"], index_type=IndexType.JSON),
    )


def escape(value: str) -> str:
    """Escape RediSearch special characters (spaces, apostrophes, hyphens...)."""
    return re.sub(r"([^\w])", r"\\\1", value)


class CategoryService(category_pb2_grpc.CategoryServiceServicer):
    def ListCategories(self, request, context):
        query = Query("*").return_fields("category").paging(0, 1000)
        results = r.ft(INDEX_NAME).search(query)
        categories = sorted({doc.category for doc in results.docs})
        return category_pb2.ListCategoriesResponse(categories=categories)

    def CountLaureates(self, request, context):
        category = request.category.strip()
        if not category:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "category is required")

        query = Query(f"@category:{{{escape(category)}}}").paging(0, 1000)
        results = r.ft(INDEX_NAME).search(query)

        total = 0
        for doc in results.docs:
            data = r.json().get(doc.id)
            if data and "laureates" in data:
                total += len(data["laureates"])
        return category_pb2.CountResponse(total=total)


class MotivationService(motivation_pb2_grpc.MotivationServiceServicer):
    def CountByKeyword(self, request, context):
        keyword = request.keyword.strip()
        if not keyword:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "keyword is required")

        query = Query(f"@motivation:{escape(keyword)}").paging(0, 1000)
        results = r.ft(INDEX_NAME).search(query)

        total = 0
        for doc in results.docs:
            data = r.json().get(doc.id)
            if not data:
                continue
            for laureate in data.get("laureates", []):
                if keyword.lower() in laureate.get("motivation", "").lower():
                    total += 1
        return motivation_pb2.KeywordCountResponse(total=total)


class LaureateService(laureate_pb2_grpc.LaureateServiceServicer):
    def FindLaureate(self, request, context):
        firstname = request.firstname.strip()
        surname = request.surname.strip()
        if not firstname or not surname:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "firstname and surname are required"
            )

        query = Query(
            f"@firstname:{escape(firstname)} @surname:{escape(surname)}"
        ).paging(0, 100)
        results = r.ft(INDEX_NAME).search(query)

        matches = []
        for doc in results.docs:
            data = r.json().get(doc.id)
            if not data:
                continue
            for laureate in data.get("laureates", []):
                if (
                    laureate.get("firstname", "").lower() == firstname.lower()
                    and laureate.get("surname", "").lower() == surname.lower()
                ):
                    matches.append(
                        laureate_pb2.LaureateMatch(
                            year=str(data.get("year", "")),
                            category=data.get("category", ""),
                            motivation=laureate.get("motivation", "N/A"),
                        )
                    )
        return laureate_pb2.LaureateResponse(found=bool(matches), matches=matches)


def serve():
    ensure_index()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    category_pb2_grpc.add_CategoryServiceServicer_to_server(CategoryService(), server)
    motivation_pb2_grpc.add_MotivationServiceServicer_to_server(MotivationService(), server)
    laureate_pb2_grpc.add_LaureateServiceServicer_to_server(LaureateService(), server)

    port = os.environ.get("GRPC_PORT", "443")
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"gRPC server listening on port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
