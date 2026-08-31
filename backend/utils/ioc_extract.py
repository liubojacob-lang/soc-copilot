import re
from dataclasses import asdict, dataclass

_IPV4_RE = re.compile(
    r"""
    (?<![\d.])
    (?:
      (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.
      (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.
      (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.
      (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)
    )
    (?![\d.])
    """,
    re.VERBOSE,
)

_DOMAIN_RE = re.compile(
    r"""
    (?<![@\w-])
    (?:
        (?:[a-zA-Z0-9]
            (?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?
        \.)+
        (?:[a-zA-Z]{2,63})
    )
    (?![\w-])
    """,
    re.VERBOSE,
)

_URL_RE = re.compile(
    r"""
    (?:
        https?://
        |
        hxxp://
        |
        hxxps://
    )
    [^\s'"]+
    """,
    re.VERBOSE | re.IGNORECASE,
)

_MD5_RE = re.compile(r"(?<![a-fA-F0-9])[a-fA-F0-9]{32}(?![a-fA-F0-9])")
_SHA1_RE = re.compile(r"(?<![a-fA-F0-9])[a-fA-F0-9]{40}(?![a-fA-F0-9])")
_SHA256_RE = re.compile(r"(?<![a-fA-F0-9])[a-fA-F0-9]{64}(?![a-fA-F0-9])")


def _normalize_obfuscation(text: str) -> str:
    t = text
    t = re.sub(r"\bhxxps://", "https://", t, flags=re.IGNORECASE)
    t = re.sub(r"\bhxxp://", "http://", t, flags=re.IGNORECASE)
    t = re.sub(r"\[\.\]", ".", t)
    t = re.sub(r"\(\.\)", ".", t)
    t = re.sub(r"\{dot\}", ".", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+dot\s+", ".", t, flags=re.IGNORECASE)
    return t


def _unique_sorted(items: list[str]) -> list[str]:
    return sorted(dict.fromkeys(items))


@dataclass
class IOCs:
    ips: list[str]
    domains: list[str]
    urls: list[str]
    hashes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def extract_iocs(text: str) -> IOCs:
    if not text:
        return IOCs(ips=[], domains=[], urls=[], hashes=[])

    normalized = _normalize_obfuscation(text)

    ips = _unique_sorted(_IPV4_RE.findall(normalized))
    urls = _unique_sorted(_URL_RE.findall(normalized))

    domains = _DOMAIN_RE.findall(normalized)
    for u in urls:
        u2 = re.sub(r"^https?://", "", u, flags=re.IGNORECASE)
        u2 = u2.split("/")[0]
        u2 = u2.split(":")[0]
        domains.extend(_DOMAIN_RE.findall(u2))
    domains = _unique_sorted(domains)

    md5s = _MD5_RE.findall(normalized)
    sha1s = _SHA1_RE.findall(normalized)
    sha256s = _SHA256_RE.findall(normalized)
    hashes = _unique_sorted(md5s + sha1s + sha256s)

    domains = [d for d in domains if not _IPV4_RE.fullmatch(d)]

    return IOCs(
        ips=ips,
        domains=domains,
        urls=urls,
        hashes=hashes,
    )


def get_ioc_count(iocs: IOCs) -> dict[str, int]:
    """Get count of each IOC type."""
    return {
        "ips": len(iocs.ips),
        "domains": len(iocs.domains),
        "urls": len(iocs.urls),
        "hashes": len(iocs.hashes),
        "total": len(iocs.ips) + len(iocs.domains) + len(iocs.urls) + len(iocs.hashes),
    }
