"""Supabase 서비스 클라이언트. 워커는 RLS를 우회하는 service_role 키로 접근한다."""

from __future__ import annotations

import os

from supabase import Client, create_client


def get_supabase_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)
