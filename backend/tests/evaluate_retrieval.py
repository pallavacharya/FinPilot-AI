
import json
import sys
from pathlib import Path

import joblib

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from modules.documents import _get_collection, MIN_SIMILARITY

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data" / "rag"
EVAL_FILE = Path(__file__).with_name("rag_eval_set.json")
VECTORIZER_FILE = DATA_DIR / "tfidf_vectorizer.joblib"

with EVAL_FILE.open("r", encoding="utf-8") as file:
    evaluation_set = json.load(file)

vectorizer = joblib.load(VECTORIZER_FILE)
collection = _get_collection()


def evaluate_question(item):
    question = item["question"]
    expected_sources = set(item["expected_sources"])

    query_vector = vectorizer.transform([question])

    # An all-zero vector means none of the question's terms
    # were represented in the fitted TF-IDF vocabulary.
    if query_vector.nnz == 0:
        retrieved_sources = set()
        best_similarity = 0.0
    else:
        results = collection.query(
            query_embeddings=query_vector.toarray().tolist(),
            n_results=4,
            include=["metadatas", "distances"]
        )

        retrieved_sources = set()
        similarities = []

        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        for metadata, distance in zip(metadatas, distances):
            if not metadata or distance is None:
                continue

            similarity = 1.0 - float(distance)
            similarities.append(similarity)

        best_similarity = max(similarities, default=0.0)

        for metadata, distance in zip(metadatas, distances):
            if not metadata or distance is None:
                continue

            similarity = 1.0 - float(distance)

            if (
                similarity >= MIN_SIMILARITY
                and similarity >= best_similarity - 0.08
            ):
                filename = metadata.get("filename")
                if filename:
                    retrieved_sources.add(filename)

    passed = expected_sources.issubset(retrieved_sources)

    # For unanswerable questions, passing means no source
    # was selected as relevant evidence.
    if not expected_sources:
        passed = len(retrieved_sources) == 0

    return {
        "id": item["id"],
        "question": question,
        "expected_sources": sorted(expected_sources),
        "retrieved_sources": sorted(retrieved_sources),
        "best_similarity": round(best_similarity, 3),
        "pass": passed,
    }


results = [evaluate_question(item) for item in evaluation_set]
passed_count = sum(result["pass"] for result in results)
total = len(results)
accuracy = (passed_count / total * 100) if total else 0.0

print("\n===== FINPILOT AI RAG RETRIEVAL EVALUATION =====\n")

for result in results:
    status = "PASS" if result["pass"] else "FAIL"
    print(f"[{status}] Question {result['id']}: {result['question']}")
    print(f"       Expected:  {result['expected_sources']}")
    print(f"       Retrieved: {result['retrieved_sources']}")
    print(f"       Similarity: {result['best_similarity']:.3f}\n")

print("=" * 48)
print(f"Passed: {passed_count}/{total}")
print(f"Retrieval evaluation score: {accuracy:.2f}%")

output_file = Path(__file__).with_name("retrieval_eval_results.json")
with output_file.open("w", encoding="utf-8") as file:
    json.dump(results, file, indent=2, ensure_ascii=False)

print(f"Results saved to: {output_file}")
print("\nNote: This measures source retrieval, not answer correctness.")
