#!/usr/bin/env python3
"""Protocol smoke wrapper; deliberately always-safe, NOT a model integration.

Replace only predict() with your own authenticated model/agent call. The API key
belongs in an explicitly passed environment variable, never command arguments.
"""
import json
import sys


def predict(request):
    return {"case_id": request["case"]["case_id"], "decision": "safe",
            "categories": [], "evidence": [], "note": "Example protocol control, not an LLM."}


if __name__ == "__main__":
    print(json.dumps(predict(json.load(sys.stdin))))
