"""
================================================================================
 data_collector/export_for_ai.py - AI Icin Veri Disa Aktarma Araci
================================================================================
 Tum oturum klasorlerini tarar, hatalari kategorilere ayirir, en sik karsilasilan
 sorunlari ozetler ve yapay zekaya (veya gelistiriciye) verilecek hazir bir
 prompt olusturur.

 Kullanim (konsoldan):
   python data_collector/export_for_ai.py

 Kullanim (kod icinden):
   from data_collector.export_for_ai import export_summary
   sonuc = export_summary()
   print(sonuc["output_path"])

 Uretilen dosya: data/ai_export_summary.json
================================================================================
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Dosya dogrudan calistirildiginda proje kokunu bul
if __package__ in (None, ""):  # pragma: no cover - script modu
    CURRENT = Path(__file__).resolve()
    for parent in CURRENT.parents:
        if (parent / "config.py").exists():
            sys.path.insert(0, str(parent))
            break

import config  # noqa: E402

from modules.error_handler import ErrorHandler  # noqa: E402

# Hata kategorisi -> Turkce cozum onerisi (ErrorHandler ile ayni sozluk)
SUGGESTIONS: Dict[str, str] = ErrorHandler.SUGGESTIONS


# ==============================================================================
# OTURUM TARAMA
# ==============================================================================
def find_session_dirs(base_dir: Optional[str] = None) -> List[Path]:
    """
    Verilen klasor altindaki tum oturum klasorlerini bulur.

    Args:
        base_dir (Optional[str]): Oturumlarin kok klasoru. None ise config.SESSIONS_DIR.

    Returns:
        List[Path]: Oturum klasorlerinin yollari (eskiden yeniye sirali).
    """
    sessions: List[Path] = []
    try:
        root = Path(base_dir) if base_dir else Path(config.SESSIONS_DIR)
        if not root.exists():
            print(f"[!] Oturum klasoru bulunamadi: {root}")
            return sessions
        for item in sorted(root.iterdir()):
            if item.is_dir():
                sessions.append(item)
    except Exception as error:
        print(f"[!] Oturum tarama hatasi: {error}")
    return sessions


def load_session_data(session_dir: Path) -> Dict[str, Any]:
    """
    Tek bir oturum klasorundeki tum JSON dosyalarini okur.

    Args:
        session_dir (Path): Oturum klasoru.

    Returns:
        Dict[str, Any]: {"name", "path", "actions", "loot_checks", "battles",
                         "errors", "session", "corrupt"}
    """
    data: Dict[str, Any] = {
        "name": session_dir.name,
        "path": str(session_dir),
        "actions": [],
        "loot_checks": [],
        "battles": [],
        "errors": [],
        "session": {},
        "corrupt": [],
    }
    try:
        for key, file_name in (
            ("actions", "actions.json"),
            ("loot_checks", "loot_checks.json"),
            ("battles", "battles.json"),
            ("errors", "errors.json"),
            ("session", "session.json"),
        ):
            file_path = session_dir / file_name
            if not file_path.exists():
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                data[key] = payload if not isinstance(payload, list) else payload
            except json.JSONDecodeError:
                data["corrupt"].append(file_name)
                print(f"[!] Bozuk JSON atlandi: {file_path}")

        # ai_export.json varsa onu da birlestir
        export_path = session_dir / "ai_export.json"
        if export_path.exists():
            try:
                with open(export_path, "r", encoding="utf-8") as handle:
                    merged = json.load(handle)
                if isinstance(merged, dict):
                    for key in ("actions", "loot_checks", "battles", "errors"):
                        if not data[key] and merged.get(key):
                            data[key] = merged[key]
            except json.JSONDecodeError:
                data["corrupt"].append("ai_export.json")
    except Exception as error:
        print(f"[!] Oturum verisi okuma hatasi ({session_dir.name}): {error}")
    return data


def scan_all_sessions(max_sessions: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Tum oturumlari tarar ve verilerini dondurur.

    Args:
        max_sessions (Optional[int]): En fazla kac oturum taranacak.
                                      None ise config.EXPORT_MAX_SESSIONS.

    Returns:
        List[Dict[str, Any]]: Oturum verileri listesi.
    """
    sessions: List[Dict[str, Any]] = []
    try:
        limit = config.EXPORT_MAX_SESSIONS if max_sessions is None else int(max_sessions)
        dirs = find_session_dirs()
        if limit and limit > 0:
            dirs = dirs[-limit:]
        for session_dir in dirs:
            sessions.append(load_session_data(session_dir))
        print(f"[EXPORT] {len(sessions)} oturum tarandi.")
    except Exception as error:
        print(f"[!] Oturum tarama hatasi: {error}")
    return sessions


# ==============================================================================
# HATA KATEGORIZASYONU
# ==============================================================================
def categorize_errors(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tum oturumlardaki hatalari kategori/kod bazinda gruplar.

    Args:
        sessions (List[Dict[str, Any]]): scan_all_sessions() ciktisi.

    Returns:
        Dict[str, Any]: {"by_category", "by_type", "total", "examples"}
    """
    result: Dict[str, Any] = {
        "by_category": {},
        "by_type": Counter(),
        "total": 0,
        "examples": defaultdict(list),
    }
    try:
        categories: Counter = Counter()
        for session in sessions:
            for error in session.get("errors", []):
                if not isinstance(error, dict):
                    continue
                result["total"] += 1
                error_type = str(error.get("error_type", "UNKNOWN"))
                result["by_type"][error_type] += 1

                category = str(error.get("category", "")).strip()
                if not category or category == "UNKNOWN":
                    category = ErrorHandler().classify(
                        error_type, str(error.get("description", ""))
                    )
                categories[category] += 1
                if len(result["examples"][category]) < 3:
                    result["examples"][category].append(
                        {
                            "time": error.get("time", ""),
                            "description": error.get("description", ""),
                            "session": session.get("name", ""),
                        }
                    )

        result["by_category"] = dict(categories)
        result["by_type"] = dict(result["by_type"])
        result["examples"] = {key: value for key, value in result["examples"].items()}
        print(f"[EXPORT] {result['total']} hata kategorize edildi.")
    except Exception as error:
        print(f"[!] Hata kategorizasyon hatasi: {error}")
    return result


def summarize_common_issues(
    categorized: Dict[str, Any],
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    En sik karsilasilan sorunlari cozum onerileriyle ozetler.

    Args:
        categorized (Dict[str, Any]): categorize_errors() ciktisi.
        top_n (int): Listelenecek maksimum sorun sayisi.

    Returns:
        List[Dict[str, Any]]: [{"category", "count", "suggestion", "examples"}]
    """
    issues: List[Dict[str, Any]] = []
    try:
        by_category = categorized.get("by_category", {})
        examples = categorized.get("examples", {})
        ordered = sorted(by_category.items(), key=lambda item: item[1], reverse=True)
        for category, count in ordered[: max(1, int(top_n))]:
            issues.append(
                {
                    "category": category,
                    "count": int(count),
                    "suggestion": SUGGESTIONS.get(category, SUGGESTIONS.get("UNKNOWN", "")),
                    "examples": examples.get(category, []),
                }
            )
        print(f"[EXPORT] {len(issues)} ortak sorun ozetlendi.")
    except Exception as error:
        print(f"[!] Sorun ozetleme hatasi: {error}")
    return issues


def aggregate_stats(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tum oturumlarin sayisal istatistiklerini tek sozlukte toplar.

    Args:
        sessions (List[Dict[str, Any]]): scan_all_sessions() ciktisi.

    Returns:
        Dict[str, Any]: Toplam istatistikler.
    """
    stats: Dict[str, Any] = {
        "session_count": len(sessions),
        "actions": 0,
        "loot_checks": 0,
        "loot_accepted": 0,
        "loot_rejected": 0,
        "battles": 0,
        "battles_success": 0,
        "errors": 0,
        "total_loot": 0,
        "accept_rate": 0.0,
    }
    try:
        for session in sessions:
            stats["actions"] += len(session.get("actions", []))
            checks = session.get("loot_checks", [])
            stats["loot_checks"] += len(checks)
            stats["loot_accepted"] += sum(1 for item in checks if item.get("accepted"))
            stats["loot_rejected"] += sum(1 for item in checks if not item.get("accepted"))
            battles = session.get("battles", [])
            stats["battles"] += len(battles)
            stats["battles_success"] += sum(1 for item in battles if item.get("success"))
            stats["errors"] += len(session.get("errors", []))
            stats["total_loot"] += sum(
                int(item.get("loot", {}).get("total", 0) or 0) for item in battles
            )
        if stats["loot_checks"] > 0:
            stats["accept_rate"] = round(
                stats["loot_accepted"] / stats["loot_checks"] * 100.0, 2
            )
    except Exception as error:
        print(f"[!] Istatistik toplama hatasi: {error}")
    return stats


# ==============================================================================
# AI PROMPT OLUSTURMA
# ==============================================================================
def build_ai_prompt(
    stats: Dict[str, Any],
    issues: List[Dict[str, Any]],
    categorized: Dict[str, Any],
) -> str:
    """
    Yapay zekaya verilecek hazir prompt metnini olusturur.

    Args:
        stats (Dict[str, Any]): aggregate_stats() ciktisi.
        issues (List[Dict[str, Any]]): summarize_common_issues() ciktisi.
        categorized (Dict[str, Any]): categorize_errors() ciktisi.

    Returns:
        str: Turkce prompt metni.
    """
    lines: List[str] = []
    try:
        lines.append(
            "Merhaba, asagida Clash of Clans yerel AI botumun topladigi oturum "
            "verileri var. Lutfen hatalari analiz et ve oncelikli duzeltmeleri "
            "Turkce olarak madde madde oner."
        )
        lines.append("")
        lines.append("== GENEL ISTATISTIKLER ==")
        lines.append(f"- Oturum sayisi        : {stats.get('session_count', 0)}")
        lines.append(f"- Toplam eylem         : {stats.get('actions', 0)}")
        lines.append(f"- Loot kontrolu        : {stats.get('loot_checks', 0)}")
        lines.append(f"- Kabul edilen rakip   : {stats.get('loot_accepted', 0)}")
        lines.append(f"- Atlanan rakip        : {stats.get('loot_rejected', 0)}")
        lines.append(f"- Kabul orani          : %{stats.get('accept_rate', 0.0)}")
        lines.append(f"- Savas sayisi         : {stats.get('battles', 0)}")
        lines.append(f"- Basarili savas       : {stats.get('battles_success', 0)}")
        lines.append(f"- Toplam loot          : {stats.get('total_loot', 0):,}")
        lines.append(f"- Hata sayisi          : {stats.get('errors', 0)}")
        lines.append("")
        lines.append("== HATA KATEGORILERI ==")
        by_category = categorized.get("by_category", {})
        if by_category:
            for category, count in sorted(
                by_category.items(), key=lambda item: item[1], reverse=True
            ):
                lines.append(f"- {category}: {count}")
        else:
            lines.append("- (hata kaydi yok)")
        lines.append("")
        lines.append("== EN SIK KARSILASILAN SORUNLAR ==")
        if issues:
            for index, issue in enumerate(issues, start=1):
                lines.append(
                    f"{index}. {issue.get('category')} (x{issue.get('count')}) -> "
                    f"onerilen cozum: {issue.get('suggestion')}"
                )
                for example in issue.get("examples", []):
                    lines.append(f"   ornek: {example.get('description', '')}")
        else:
            lines.append("(sorun bulunamadi)")
        lines.append("")
        lines.append(
            "Lutfen: 1) Hangi hatalar en kritik? 2) Hangi config.py degeri "
            "degistirilmeli? 3) Template veya OCR ayarlari icin somut oneriler. "
            "Kisa ve uygulanabilir cevap ver."
        )
    except Exception as error:
        print(f"[!] Prompt olusturma hatasi: {error}")
        lines.append(f"Prompt olusturulurken hata olustu: {error}")
    return "\n".join(lines)


# ==============================================================================
# ANA FONKSIYON
# ==============================================================================
def export_summary(
    output_path: Optional[str] = None,
    max_sessions: Optional[int] = None,
    include_prompt: bool = True,
) -> Dict[str, Any]:
    """
    Tek cagri ile tum oturum verisini toplar, ozetler ve disa aktarir.

    Args:
        output_path (Optional[str]): Hedef JSON dosyasi.
                                     None ise data/ai_export_summary.json.
        max_sessions (Optional[int]): Taranacak maksimum oturum sayisi.
        include_prompt (bool): Prompt metni ciktiya eklensin mi.

    Returns:
        Dict[str, Any]: {"output_path", "stats", "issues", "prompt", "success"}
    """
    result: Dict[str, Any] = {
        "output_path": "",
        "stats": {},
        "issues": [],
        "prompt": "",
        "success": False,
    }
    try:
        print("=" * 78)
        print(" AI ICIN VERI DISA AKTARMA")
        print("=" * 78)

        sessions = scan_all_sessions(max_sessions=max_sessions)
        stats = aggregate_stats(sessions)
        categorized = categorize_errors(sessions)
        issues = summarize_common_issues(categorized)
        prompt = build_ai_prompt(stats, issues, categorized) if include_prompt else ""

        payload: Dict[str, Any] = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "config": {
                "min_total_loot": config.MIN_TOTAL_LOOT,
                "min_gold": config.MIN_GOLD,
                "min_elixir": config.MIN_ELIXIR,
                "min_dark": config.MIN_DARK,
                "template_threshold": config.TEMPLATE_THRESHOLD,
                "active_plan": config.ACTIVE_PLAN,
                "battle_timeout": config.BATTLE_TIMEOUT,
                "use_local_ai": config.USE_LOCAL_AI,
                "ollama_model": config.OLLAMA_MODEL,
            },
            "stats": stats,
            "error_categories": categorized.get("by_category", {}),
            "error_types": categorized.get("by_type", {}),
            "common_issues": issues,
            "sessions": [
                {
                    "name": session.get("name"),
                    "actions": len(session.get("actions", [])),
                    "loot_checks": len(session.get("loot_checks", [])),
                    "battles": len(session.get("battles", [])),
                    "errors": len(session.get("errors", [])),
                    "session": session.get("session", {}),
                    "corrupt_files": session.get("corrupt", []),
                }
                for session in sessions
            ],
            "ai_prompt": prompt,
        }

        target = (
            Path(output_path)
            if output_path
            else (Path(config.DATA_DIR) / "ai_export_summary.json")
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, default=str)

        result["output_path"] = str(target)
        result["stats"] = stats
        result["issues"] = issues
        result["prompt"] = prompt
        result["success"] = True

        print("-" * 78)
        print(f" Oturum sayisi : {stats.get('session_count')}")
        print(f" Toplam eylem  : {stats.get('actions')}")
        print(f" Toplam hata   : {stats.get('errors')}")
        print(f" Cikti dosyasi : {target}")
        print("=" * 78)
        return result
    except Exception as error:
        print(f"[!] Disa aktarma hatasi: {error}")
        return result


def export_prompt_only(output_path: Optional[str] = None) -> Optional[str]:
    """
    Sadece prompt metnini ayri bir .txt dosyasina kaydeder.

    Args:
        output_path (Optional[str]): Hedef dosya. None ise data/ai_prompt.txt.

    Returns:
        Optional[str]: Kaydedilen dosya yolu veya None.
    """
    try:
        result = export_summary(include_prompt=True)
        prompt = str(result.get("prompt", ""))
        target = Path(output_path) if output_path else (Path(config.DATA_DIR) / "ai_prompt.txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(prompt)
        print(f"[EXPORT] Prompt kaydedildi -> {target}")
        return str(target)
    except Exception as error:
        print(f"[!] Prompt kaydetme hatasi: {error}")
        return None


if __name__ == "__main__":  # pragma: no cover - script modu
    outcome = export_summary()
    if outcome.get("success"):
        print("\n--- AI PROMPT ONIZLEME ---\n")
        print(outcome.get("prompt", "")[:1500])
