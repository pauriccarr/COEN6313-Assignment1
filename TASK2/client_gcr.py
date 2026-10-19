import os
import socket
import grpc

import category_pb2
import category_pb2_grpc
import laureate_pb2
import laureate_pb2_grpc
import motivation_pb2
import motivation_pb2_grpc

def make_channel(target: str):
    if target.endswith(":443"):
        host = target.rsplit(":", 1)[0]
        # Resolve IPv4 only, so grpc never tries the unreachable IPv6 addresses.
        ip = socket.getaddrinfo(host, 443, socket.AF_INET)[0][4][0]
        return grpc.secure_channel(
            f"ipv4:{ip}:443",
            grpc.ssl_channel_credentials(),
            options=[
                ("grpc.ssl_target_name_override", host),  # TLS name check / SNI
                ("grpc.default_authority", host),         # Host header Cloud Run routes on
            ],
        )
    return grpc.insecure_channel(target)

def search_category(stub):
    categories = stub.ListCategories(category_pb2.ListCategoriesRequest()).categories
    print("\nCategories:")
    for i, name in enumerate(categories, 1):
        print(f"{i}. {name}")

    category = input("\nEnter a category: ").strip()
    if category not in categories:
        print("Category not found.")
        return
    resp = stub.CountLaureates(category_pb2.CategoryRequest(category=category))
    print(f"\nTotal number of laureates in {category}: {resp.total}")


def search_motivation(stub):
    keyword = input("\nEnter a motivation keyword: ").strip()
    if not keyword:
        print("Keyword cannot be empty.")
        return
    resp = stub.CountByKeyword(motivation_pb2.KeywordRequest(keyword=keyword))
    print(f"\nTotal laureates with '{keyword}' in their motivation: {resp.total}")


def search_laureate(stub):
    firstname = input("\nEnter first name: ").strip()
    surname = input("Enter last name: ").strip()
    resp = stub.FindLaureate(
        laureate_pb2.LaureateRequest(firstname=firstname, surname=surname)
    )
    if not resp.found:
        print("\nLaureate not found.")
        return
    for m in resp.matches:
        print("\nLaureate found:")
        print(f"Year: {m.year}")
        print(f"Category: {m.category}")
        print(f"Motivation: {m.motivation}")


def main():
    target = os.environ.get("GRPC_TARGET", "localhost:50051")
    print(f"DEBUG target={target!r} tls={target.endswith(':443')}")
    with make_channel(target) as channel:
    #with grpc.insecure_channel(target) as channel:
        category_stub = category_pb2_grpc.CategoryServiceStub(channel)
        motivation_stub = motivation_pb2_grpc.MotivationServiceStub(channel)
        laureate_stub = laureate_pb2_grpc.LaureateServiceStub(channel)

        while True:
            print("\n==============================")
            print(" Nobel Prize Search")
            print("==============================")
            print("1) Category")
            print("2) Motivation")
            print("3) Laureate Name")
            print("4) Exit")
            choice = input("\nChoose an option: ").strip()

            try:
                if choice == "1":
                    search_category(category_stub)
                elif choice == "2":
                    search_motivation(motivation_stub)
                elif choice == "3":
                    search_laureate(laureate_stub)
                elif choice == "4":
                    print("Goodbye!")
                    break
                else:
                    print("Invalid option. Please choose 1-4.")
            except grpc.RpcError as e:
                print(f"\nRPC error: {e.code().name}: {e.details()}")


if __name__ == "__main__":
    main()