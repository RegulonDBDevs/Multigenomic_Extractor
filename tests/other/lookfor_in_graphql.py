
#!/usr/bin/env python3
"""
Validate RegulonDB identifiers against GraphQL.

Checks genes, operons and their related objects using
local MongoDB identifiers and the prerelease GraphQL API.

Dependencies:
    pip install pymongo requests
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone

import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError


GRAPHQL_URL = "https://regulondb-prerelease.ccg.unam.mx/graphql"

GENE_QUERY = """
query ($search: String!) {
  getGenesBy(advancedSearch: $search) {
    data {
      gene {
        _id
        name
      }
      products {
        _id
        name
      }
    }
  }
}
"""

OPERON_QUERY = """
query ($search: String!) {
  getOperonBy(advancedSearch: $search) {
    data {
      operon {
        _id
        name
      }
      transcriptionUnits {
        _id
        name
      }
    }
  }
}
"""

CONFIG = {
    "genes": {
        "type": "genes",
        "query": GENE_QUERY,
        "root": "getGenesBy",
        "field": "gene",
        "related": "products",
        "search_field": "gene._id",
    },
    "operons": {
        "type": "operons",
        "query": OPERON_QUERY,
        "root": "getOperonBy",
        "field": "operon",
        "related": "transcriptionUnits",
        "search_field": "operon._id",
    },
}


def validate_name(document, expected_name):
    """Check exact name membership in propertiesToMakeId."""
    properties = document.get("propertiesToMakeId", [])

    if not isinstance(properties, list):
        return False, properties

    if not isinstance(expected_name, str):
        return False, properties

    return expected_name in properties, properties


def graphql_request(session, query, identifier, field, url):
    """Execute a GraphQL request using an identifier."""
    response = session.post(
        url,
        json={
            "query": query,
            "variables": {
                "search": f"{identifier}[{field}]"
            },
        },
        timeout=30,
    )

    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, dict):
        raise ValueError("Invalid GraphQL response format")

    if payload.get("errors"):
        raise RuntimeError(
            json.dumps(
                payload["errors"],
                ensure_ascii=False,
            )
        )

    return payload.get("data") or {}


def add_issue(issues, category, identifier, error, **details):
    """Register a validation issue."""
    issues.append({
        "category": category,
        "id": identifier,
        "error": error,
        **details,
    })


def validate_object(
    collection,
    obj,
    issues,
    category,
    expected_type=None,
):
    """Validate an object's ID, source and name."""
    if not isinstance(obj, dict):
        add_issue(
            issues,
            category,
            None,
            "INVALID_GRAPHQL_OBJECT",
            graphql_object=obj,
        )
        return False

    identifier = obj.get("_id")
    expected_name = obj.get("name")

    if not identifier:
        add_issue(
            issues,
            category,
            None,
            "MISSING_GRAPHQL_ID",
            graphql_object=obj,
        )
        return False

    local = collection.find_one({"_id": identifier})

    if local is None:
        add_issue(
            issues,
            category,
            identifier,
            "ID_NOT_FOUND",
            graphql_name=expected_name,
        )
        return False

    valid = True

    if local.get("sourceDBName") != "EcoCyc":
        valid = False
        add_issue(
            issues,
            category,
            identifier,
            "SOURCE_MISMATCH",
            expected_source="EcoCyc",
            local_source=local.get("sourceDBName"),
        )

    if (
        expected_type is not None
        and local.get("type") != expected_type
    ):
        valid = False
        add_issue(
            issues,
            category,
            identifier,
            "TYPE_MISMATCH",
            expected_type=expected_type,
            local_type=local.get("type"),
        )

    name_valid, properties = validate_name(
        local,
        expected_name,
    )

    if not name_valid:
        valid = False
        add_issue(
            issues,
            category,
            identifier,
            "NAME_MISMATCH",
            graphql_name=expected_name,
            propertiesToMakeId=properties,
        )

    return valid


def validate_sample(
    collection,
    session,
    config,
    limit,
    graphql_url,
):
    """Validate a random sample of main and related objects."""
    documents = list(collection.aggregate([
        {
            "$match": {
                "sourceDBName": "EcoCyc",
                "sourceDBVersion":"29.5",
                "type": config["type"],
            }
        },
        {"$sample": {"size": limit}},
    ]))

    issues = []
    stats = Counter()
    stats["sampled"] = len(documents)
    stats["passed"] = 0
    stats["failed"] = 0
    stats["related_checked"] = 0
    stats["related_passed"] = 0
    stats["related_failed"] = 0
    stats["empty_responses"] = 0
    stats["invalid_responses"] = 0
    stats["request_errors"] = 0

    for index, document in enumerate(documents, 1):
        identifier = document["_id"]

        print(
            f"[{index}/{len(documents)}] "
            f"{config['field']}: {identifier}"
        )

        try:
            data = graphql_request(
                session,
                config["query"],
                identifier,
                config["search_field"],
                graphql_url,
            )

            root = data.get(config["root"]) or {}
            rows = root.get("data") or []

            if not isinstance(rows, list):
                stats["invalid_responses"] += 1
                stats["failed"] += 1
                add_issue(
                    issues,
                    config["field"],
                    identifier,
                    "INVALID_GRAPHQL_RESPONSE",
                )
                print("  ERROR: Invalid response")
                continue

            if not rows:
                stats["empty_responses"] += 1
                stats["failed"] += 1
                add_issue(
                    issues,
                    config["field"],
                    identifier,
                    "NO_GRAPHQL_RESULTS",
                )
                print("  NOT FOUND IN GRAPHQL")
                continue

            matching = [
                row
                for row in rows
                if isinstance(row, dict)
                and isinstance(row.get(config["field"]), dict)
                and row[config["field"]].get("_id") == identifier
            ]

            if len(matching) != 1:
                stats["invalid_responses"] += 1
                stats["failed"] += 1
                add_issue(
                    issues,
                    config["field"],
                    identifier,
                    "GRAPHQL_ID_MISMATCH",
                    matching_count=len(matching),
                    returned_ids=[
                        row.get(config["field"], {}).get("_id")
                        for row in rows
                        if isinstance(row, dict)
                        and isinstance(
                            row.get(config["field"]), dict
                        )
                    ],
                )
                print("  ERROR: ID mismatch")
                continue

            row = matching[0]
            main = row[config["field"]]

            main_valid = validate_object(
                collection,
                main,
                issues,
                config["field"],
                expected_type=config["type"],
            )

            related_objects = row.get(config["related"])

            if related_objects is None:
                related_objects = []

            if not isinstance(related_objects, list):
                add_issue(
                    issues,
                    config["related"],
                    identifier,
                    "INVALID_RELATED_OBJECTS",
                )
                main_valid = False
                related_objects = []

            all_related_valid = True

            for related in related_objects:
                stats["related_checked"] += 1

                related_valid = validate_object(
                    collection,
                    related,
                    issues,
                    config["related"],
                )

                if related_valid:
                    stats["related_passed"] += 1
                else:
                    stats["related_failed"] += 1
                    all_related_valid = False

            if main_valid and all_related_valid:
                stats["passed"] += 1
                print(
                    f"  OK ({len(related_objects)} "
                    f"{config['related']} checked)"
                )
            else:
                stats["failed"] += 1
                print("  MISMATCH")

        except (
            requests.RequestException,
            RuntimeError,
            ValueError,
            PyMongoError,
        ) as exc:
            stats["request_errors"] += 1
            stats["failed"] += 1

            add_issue(
                issues,
                config["field"],
                identifier,
                "VALIDATION_ERROR",
                detail=str(exc),
            )

            print(f"  ERROR: {exc}")

    return {
        "stats": dict(stats),
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate RegulonDB MongoDB IDs against GraphQL"
    )

    parser.add_argument(
        "--mongo-uri",
        default="mongodb://localhost:27017",
    )
    parser.add_argument(
        "--database",
        default="reguondbidentifiers_server",
    )
    parser.add_argument(
        "--collection",
        default="identifiers",
    )
    parser.add_argument(
        "--graphql-url",
        default=GRAPHQL_URL,
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=50,
    )
    parser.add_argument(
        "--gene-type",
        default="genes",
    )
    parser.add_argument(
        "--operon-type",
        default="operons",
    )
    parser.add_argument(
        "--output",
        default="validation_report.json",
    )

    args = parser.parse_args()

    if args.sample_size < 1:
        parser.error("--sample-size must be greater than zero")

    CONFIG["genes"]["type"] = args.gene_type
    CONFIG["operons"]["type"] = args.operon_type

    client = MongoClient(
        args.mongo_uri,
        serverSelectionTimeoutMS=5000,
    )

    try:
        client.admin.command("ping")
        collection = client[args.database][args.collection]

        report = {
            "metadata": {
                "database": args.database,
                "collection": args.collection,
                "graphql_url": args.graphql_url,
                "sample_size": args.sample_size,
                "sourceDBName": "EcoCyc",
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            },
            "results": {},
        }

        with requests.Session() as session:
            for category, config in CONFIG.items():
                print(f"\n{'=' * 60}")
                print(f"VALIDATING {category.upper()}")
                print(f"{'=' * 60}")

                report["results"][category] = validate_sample(
                    collection,
                    session,
                    config,
                    args.sample_size,
                    args.graphql_url,
                )

        with open(
            args.output,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                report,
                file,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        print(f"\n{'=' * 60}")
        print("VALIDATION SUMMARY")
        print(f"{'=' * 60}")

        total_failed = 0

        for category, result in report["results"].items():
            stats = result["stats"]
            total_failed += stats["failed"]

            print(f"\n{category.upper()}")
            print(f"  Sampled:         {stats['sampled']}")
            print(f"  Passed:          {stats['passed']}")
            print(f"  Failed:          {stats['failed']}")
            print(f"  Related checked: {stats['related_checked']}")
            print(f"  Related passed:  {stats['related_passed']}")
            print(f"  Related failed:  {stats['related_failed']}")
            print(f"  Empty responses: {stats['empty_responses']}")
            print(f"  Request errors:  {stats['request_errors']}")

        print(f"\nReport saved: {args.output}")

        return 1 if total_failed else 0

    except PyMongoError as exc:
        print(f"MongoDB error: {exc}", file=sys.stderr)
        return 2

    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
