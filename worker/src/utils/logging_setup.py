"""로깅 설정. GitHub Actions 실행 환경이므로 stdout으로만 출력(잡 로그가 유일한 진단 수단)."""

from __future__ import annotations

import logging
import sys


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
