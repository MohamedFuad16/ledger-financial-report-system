"""Canonical English display names and ASCII slugs for corpus companies.

The manifest keeps the exact Japanese legal entity as the company identity
(gold binding depends on it), while files, folders, and the English UI use
these names. The map covers every company the corpus holds; unmapped names
fall back to the Unicode-preserving slug so distinct entities can never
collapse.
"""

from __future__ import annotations

import re
import unicodedata

COMPANY_EN: dict[str, str] = {
    "3M": "3M",
    "AppBank株式会社": "AppBank Inc.",
    "Byside株式会社": "Byside Inc.",
    "JR九州エンジニアリング株式会社": "JR Kyushu Engineering Co., Ltd.",
    "JUKI産機テクノロジー株式会社": "JUKI Industrial Equipment Technology Corp.",
    "note株式会社": "note inc.",
    "キャディ株式会社": "CADDi Inc.",
    "クラスター株式会社": "Cluster, Inc.",
    "ハコベル株式会社": "Hacobell Inc.",
    "ファインディ株式会社": "Findy Inc.",
    "メディフォン株式会社": "MediPhone, Inc.",
    "ラクスル株式会社": "Raksul Inc.",
    "リソルホールディングス株式会社": "RESOL Holdings Co., Ltd.",
    "吉田海運株式会社": "Yoshida Kaiun Co., Ltd.",
    "大西運輸株式会社": "Onishi Transport Co., Ltd.",
    "日本テーマパーク開発株式会社": "Japan Theme Park Development, Inc.",
    "株式会社FLUX": "FLUX Inc.",
    "株式会社iCARE": "iCARE Co., Ltd.",
    "株式会社Morght": "Morght Inc.",
    "株式会社mov": "mov inc.",
    "株式会社PIGNUS（ピグナス）": "PIGNUS Inc.",
    "株式会社SANU": "SANU Inc.",
    "株式会社with": "with Inc.",
    "株式会社アップガレージグループ": "UP GARAGE GROUP Co., Ltd.",
    "株式会社キズキ": "Kizuki Co., Ltd.",
    "株式会社キッズコーポレーション": "Kids Corporation Inc.",
    "株式会社グッドパッチ": "Goodpatch Inc.",
    "株式会社トーエネック": "TOENEC Corporation",
    "株式会社ナレッジワーク": "Knowledge Work Inc.",
    "株式会社ハッピートラベル": "Happy Travel Co., Ltd.",
    "株式会社ベルク": "Belc CO., LTD.",
    "株式会社レスタス": "Lestas Inc.",
    "株式会社伊豆シャボテン公園": "Izu Shaboten Resort Co., Ltd.",
    "株式会社帝国ホテル": "Imperial Hotel, Ltd.",
}

_LEGAL_SUFFIXES = re.compile(r"(?:,?\s+(?:Inc|inc|Corp|Corporation|Co|Ltd|LTD|CO|K\.K)\.?,?)+\s*$")

# Names where a legal-suffix word is part of the brand itself.
_SLUG_OVERRIDES = {
    "株式会社キッズコーポレーション": "Kids_Corporation",
}


def english_name(company: str) -> str | None:
    return COMPANY_EN.get(unicodedata.normalize("NFC", str(company or "").strip()))


def english_slug(company: str) -> str | None:
    """ASCII file/folder slug from the English name; None when unmapped."""
    normalized = unicodedata.normalize("NFC", str(company or "").strip())
    if normalized in _SLUG_OVERRIDES:
        return _SLUG_OVERRIDES[normalized]
    name = english_name(company)
    if not name:
        return None
    base = name
    while True:
        stripped = _LEGAL_SUFFIXES.sub("", base).rstrip(" ,.")
        if stripped == base or not stripped:
            break
        base = stripped
    slug = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_")
    return slug or None
