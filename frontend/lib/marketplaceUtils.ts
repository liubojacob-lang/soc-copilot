/**
 * Marketplace Playbook Source & Attribution Utilities
 * Extracts standard references, MITRE ATT&CK techniques, and authority badges.
 */

export interface PlaybookSourceMeta {
  standardName: string;
  standardType: "nist" | "mitre" | "cortex" | "owasp" | "cisa" | "iso" | "cis" | "aws" | "default";
  mitreTechniques: string[];
  author: string;
  badgeClass: string;
  badgeBorderClass: string;
  referenceUrl?: string;
  summaryNote?: string;
}

export function parsePlaybookSource(playbook: {
  tags?: string[] | null;
  author_name?: string | null;
  author?: string | null;
  category?: string | null;
  name?: string | null;
}): PlaybookSourceMeta {
  const tags = playbook.tags || [];
  const author = playbook.author_name || playbook.author || "Community";
  const category = playbook.category || "";
  const name = playbook.name || "";

  // 1. Extract MITRE ATT&CK techniques from tags
  const mitreTechniques: string[] = [];
  const standardTags: string[] = [];

  for (const tag of tags) {
    const lower = tag.toLowerCase();
    if (lower.startsWith("att&ck:") || lower.startsWith("mitre:")) {
      const tech = tag.split(":")[1]?.trim();
      if (tech && !mitreTechniques.includes(tech)) {
        mitreTechniques.push(tech);
      }
    } else if (/^T\d{4}(\.\d{3})?$/i.test(tag)) {
      if (!mitreTechniques.includes(tag.toUpperCase())) {
        mitreTechniques.push(tag.toUpperCase());
      }
    } else if (lower.startsWith("standard:") || lower.startsWith("source:")) {
      standardTags.push(tag.split(":")[1]?.trim());
    }
  }

  // 2. Identify Standard & Type
  let standardName = "";
  let standardType: PlaybookSourceMeta["standardType"] = "default";
  let referenceUrl: string | undefined;

  const rawStandard = standardTags[0] || "";
  const searchStr = `${rawStandard} ${tags.join(" ")} ${author} ${name}`.toLowerCase();

  if (searchStr.includes("nist sp 800-61") || searchStr.includes("nist 800-61")) {
    standardName = "NIST SP 800-61 Rev.2";
    standardType = "nist";
    referenceUrl = "https://csrc.nist.gov/pubs/sp/800/61/r2/final";
  } else if (searchStr.includes("nist sp 800-52") || searchStr.includes("nist 800-52")) {
    standardName = "NIST SP 800-52 Rev.2";
    standardType = "nist";
    referenceUrl = "https://csrc.nist.gov/pubs/sp/800/52/r2/final";
  } else if (searchStr.includes("nist sp 800-207") || searchStr.includes("nist 800-207")) {
    standardName = "NIST SP 800-207 (Zero Trust)";
    standardType = "nist";
    referenceUrl = "https://csrc.nist.gov/pubs/sp/800/207/final";
  } else if (
    searchStr.includes("mitre att&ck") ||
    searchStr.includes("att&ck") ||
    mitreTechniques.length > 0
  ) {
    standardName = "MITRE ATT&CK® Matrix";
    standardType = "mitre";
    referenceUrl = "https://attack.mitre.org/";
  } else if (searchStr.includes("cortex") || searchStr.includes("xsoar")) {
    standardName = "Palo Alto Cortex XSOAR";
    standardType = "cortex";
    referenceUrl = "https://xsoar.pan.dev/";
  } else if (searchStr.includes("owasp")) {
    standardName = "OWASP Top 10 Standard";
    standardType = "owasp";
    referenceUrl = "https://owasp.org/Top10/";
  } else if (searchStr.includes("cisa")) {
    standardName = "CISA Cyber Defense Advisory";
    standardType = "cisa";
    referenceUrl = "https://www.cisa.gov/news-events/cybersecurity-advisories";
  } else if (
    searchStr.includes("cis ") ||
    searchStr.includes("cis-") ||
    searchStr.includes("benchmark")
  ) {
    standardName = "CIS Benchmarks";
    standardType = "cis";
    referenceUrl = "https://www.cisecurity.org/cis-benchmarks";
  } else if (searchStr.includes("pci-dss") || searchStr.includes("pci dss")) {
    standardName = "PCI-DSS 4.0 Standard";
    standardType = "iso";
    referenceUrl = "https://www.pcisecuritystandards.org/";
  } else if (
    searchStr.includes("gdpr") ||
    searchStr.includes("iso 27035") ||
    searchStr.includes("iso 27001")
  ) {
    standardName = "ISO/IEC 27035 & GDPR";
    standardType = "iso";
    referenceUrl = "https://www.iso.org/standard/60803.html";
  } else if (searchStr.includes("aws")) {
    standardName = "AWS Security Best Practices";
    standardType = "aws";
    referenceUrl = "https://aws.amazon.com/security/security-bulletins/";
  } else if (category === "phishing") {
    standardName = "NIST SP 800-61 Rev.2";
    standardType = "nist";
  } else if (category === "ransomware") {
    standardName = "NIST SP 800-61 / CISA";
    standardType = "cisa";
  } else if (category === "malware_response") {
    standardName = "MITRE ATT&CK® Enterprise";
    standardType = "mitre";
  } else {
    standardName = "Industry Standard SOP";
    standardType = "default";
  }

  // Fallback techniques if not explicitly extracted
  if (mitreTechniques.length === 0) {
    if (category === "phishing") mitreTechniques.push("T1566");
    else if (category === "ransomware") mitreTechniques.push("T1486");
    else if (category === "malware_response") mitreTechniques.push("T1059");
    else if (category === "network_intrusion") mitreTechniques.push("T1110");
    else if (category === "insider_threat") mitreTechniques.push("T1078");
    else if (category === "data_breach") mitreTechniques.push("T1048");
  }

  // 3. Styling classes
  let badgeClass = "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300";
  let badgeBorderClass = "border-gray-200 dark:border-gray-600";

  switch (standardType) {
    case "nist":
      badgeClass = "bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300";
      badgeBorderClass = "border-blue-200/80 dark:border-blue-800/60";
      break;
    case "mitre":
      badgeClass = "bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300";
      badgeBorderClass = "border-amber-200/80 dark:border-amber-800/60";
      break;
    case "cortex":
      badgeClass = "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300";
      badgeBorderClass = "border-indigo-200/80 dark:border-indigo-800/60";
      break;
    case "owasp":
      badgeClass = "bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-300";
      badgeBorderClass = "border-purple-200/80 dark:border-purple-800/60";
      break;
    case "cisa":
      badgeClass = "bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300";
      badgeBorderClass = "border-rose-200/80 dark:border-rose-800/60";
      break;
    case "iso":
      badgeClass = "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300";
      badgeBorderClass = "border-emerald-200/80 dark:border-emerald-800/60";
      break;
    case "cis":
      badgeClass = "bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300";
      badgeBorderClass = "border-cyan-200/80 dark:border-cyan-800/60";
      break;
    case "aws":
      badgeClass = "bg-orange-50 text-orange-700 dark:bg-orange-950/50 dark:text-orange-300";
      badgeBorderClass = "border-orange-200/80 dark:border-orange-800/60";
      break;
    default:
      badgeClass = "bg-gray-50 text-gray-700 dark:bg-gray-800 dark:text-gray-300";
      badgeBorderClass = "border-gray-200 dark:border-gray-700";
      break;
  }

  return {
    standardName,
    standardType,
    mitreTechniques,
    author,
    badgeClass,
    badgeBorderClass,
    referenceUrl,
  };
}
