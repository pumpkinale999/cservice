"""WeCom API errors."""

from __future__ import annotations


class CserviceWecomError(Exception):
    def __init__(self, errcode: int, errmsg: str = "") -> None:
        self.errcode = errcode
        self.errmsg = errmsg
        super().__init__(f"wecom errcode={errcode} errmsg={errmsg}")
