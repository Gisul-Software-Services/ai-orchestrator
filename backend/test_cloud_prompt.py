#!/usr/bin/env python3
"""Test cloud prompt generation to debug the issue."""
import asyncio
import sys
sys.path.insert(0, '/root/gisul_model')

from backend.model_app.competencies.cloud.generator import _pass1

async def test():
    try:
        result = await _pass1(
            mode="code",
            job_role="Cloud Engineer",
            experience_years=3,
            difficulty="Medium",
            aws_service="s3",
            concepts=["bucket policies"],
            time_limit=30,
            rag_context="S3 | Concept: bucket policy | Core idea: restrict access"
        )
        print("SUCCESS!")
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"Description length: {len(result.get('description', ''))}")
        print(f"Full result keys: {list(result.keys())}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
