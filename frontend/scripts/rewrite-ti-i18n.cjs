#!/usr/bin/env node
/**
 * Rewrite the `threatIntel` namespace in both locale files, preserving
 * the nested `dashboard` sub-object verbatim.
 */
const fs = require("fs");

const en = JSON.parse(fs.readFileSync("messages/en.json", "utf8"));
const zh = JSON.parse(fs.readFileSync("messages/zh-CN.json", "utf8"));

const enNs = {
  title: "Threat Intelligence",
  description: "Look up and enrich Indicators of Compromise (IOCs) across threat intelligence sources",
  providerNotice: "Provider: AlienVault OTX. Results are cached server-side; cached responses are marked in the result panel.",
  tabSingle: "Single Lookup",
  tabBatch: "Batch Query",
  iocType: "IOC type",
  autoDetect: "Auto-detect",
  type_ip: "IP",
  type_domain: "Domain",
  type_url: "URL",
  type_hash: "Hash",
  searchPlaceholder: "Enter an IP, domain, URL or file hash...",
  search: "Look up",
  searching: "Looking up...",
  lookupFailed: "Lookup failed. Please try again later.",
  cannotDetect: "Cannot detect the IOC type. Please pick a type manually.",
  verdict_malicious: "Malicious",
  verdict_suspicious: "Suspicious",
  verdict_unknown: "Unknown",
  verdict_benign: "Benign",
  score: "Score",
  pulseCount: "Pulse reports",
  provider: "Provider",
  cached: "From cache",
  yes: "Yes",
  no: "No",
  tags: "Tags",
  references: "References",
  skippedReason: "Skipped",
  errorReason: "Error",
  rawDetails: "Raw response",
  requestId: "Request ID",
  batchInput: "Batch IOC input",
  batchPlaceholder: "One IOC per line, up to 50. Types are detected automatically:\n203.0.113.7\nexample.com\nhttps://example.com/payload\ne3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  batchHint: "Paste one IOC per line (up to {max}); types are detected automatically.",
  batchQuery: "Batch Query",
  parseSummary: "{count} valid IOCs, {invalid} unrecognized",
  overflow: "{count} lines beyond the limit will be ignored",
  batchSummary: "{total} results",
  batchSkipped: "{count} IOCs skipped due to rate limiting",
  noResults: "No results",
  colIoc: "IOC",
  colVerdict: "Verdict",
  colScore: "Score",
  colPulses: "Pulses",
  colSource: "Source",
  colTags: "Tags / Error",
  // Preserved sub-object
  dashboard: en.threatIntel.dashboard,
};

const zhNs = {
  title: "威胁情报",
  description: "跨威胁情报源查询与富化失陷指标（IOC）",
  providerNotice: "情报源：AlienVault OTX。查询结果在服务端缓存，缓存命中会在结果面板中标注。",
  tabSingle: "单个查询",
  tabBatch: "批量查询",
  iocType: "IOC 类型",
  autoDetect: "自动识别",
  type_ip: "IP",
  type_domain: "域名",
  type_url: "URL",
  type_hash: "哈希",
  searchPlaceholder: "输入 IP、域名、URL 或文件哈希...",
  search: "查询",
  searching: "查询中...",
  lookupFailed: "查询失败，请稍后重试。",
  cannotDetect: "无法识别 IOC 类型，请手动指定类型。",
  verdict_malicious: "恶意",
  verdict_suspicious: "可疑",
  verdict_unknown: "未知",
  verdict_benign: "良性",
  score: "威胁评分",
  pulseCount: "Pulse 报告数",
  provider: "情报源",
  cached: "缓存命中",
  yes: "是",
  no: "否",
  tags: "标签",
  references: "参考链接",
  skippedReason: "已跳过",
  errorReason: "错误",
  rawDetails: "原始响应",
  requestId: "请求 ID",
  batchInput: "批量 IOC 输入",
  batchPlaceholder: "每行一个 IOC，最多 50 条，类型自动识别：\n203.0.113.7\nexample.com\nhttps://example.com/payload\ne3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  batchHint: "每行粘贴一个 IOC（最多 {max} 条），类型自动识别。",
  batchQuery: "批量查询",
  parseSummary: "有效 IOC {count} 条，无法识别 {invalid} 条",
  overflow: "超出上限的 {count} 行将被忽略",
  batchSummary: "共 {total} 条结果",
  batchSkipped: "因频率限制跳过 {count} 条",
  noResults: "暂无结果",
  colIoc: "IOC",
  colVerdict: "判定",
  colScore: "评分",
  colPulses: "Pulse 数",
  colSource: "来源",
  colTags: "标签 / 错误",
  dashboard: zh.threatIntel.dashboard,
};

en.threatIntel = enNs;
zh.threatIntel = zhNs;

fs.writeFileSync("messages/en.json", JSON.stringify(en, null, 2) + "\n");
fs.writeFileSync("messages/zh-CN.json", JSON.stringify(zh, null, 2) + "\n");
console.log("en keys:", Object.keys(enNs).length, "zh keys:", Object.keys(zhNs).length);
