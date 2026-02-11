"use client";



import { useState, useEffect, useCallback } from "react";

import { useRouter } from "next/navigation";

import ReactMarkdown from "react-markdown";

import { api, AlertAnalysisResponse, ReportGenerationResponse, TimelineResponse, HistoryRecord, IOCsLocal, IOCsLLM, IOCCount } from "@/lib/api";

import { loadAuthState, logout, isAdmin, type User } from "@/lib/auth";

import { HistoryPanel } from "@/components/HistoryPanel";

import { ImpactPanel } from "@/components/impact/ImpactPanel";

import { ThreatIntelSection } from "@/components/threat_intel/ThreatIntelSection";

import { PlaybookPanel } from "@/components/playbook/PlaybookPanel";

import Navigation from "@/components/Navigation";



type Tab = "alert" | "report" | "timeline" | "assets";



type Severity = "high" | "medium" | "low";



const SEVERITY_COLORS: Record<Severity, string> = {

  high: "bg-red-100 text-red-800 border-red-300",

  medium: "bg-amber-100 text-amber-800 border-amber-300",

  low: "bg-green-100 text-green-800 border-green-300",

};



function Loading() {

  return (

    <div className="flex items-center justify-center p-8">

      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-soc-600"></div>

    </div>

  );

}



function Error({ message }: { message: string }) {

  return (

    <div className="p-4 bg-red-50 border border-red-200 rounded-lg">

      <p className="text-red-800">{message}</p>

    </div>

  );

}



function DegradedWarning({ reason }: { reason?: string }) {

  return (

    <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">

      <p className="text-amber-800 text-sm">

        <span className="font-semibold">⚠️ Degraded mode:</span> The AI response failed validation. Some fields may be missing.

        {reason && <span className="ml-2">Reason: {reason}</span>}

      </p>

    </div>

  );

}



function CopyButton({ content }: { content: string }) {

  const [copied, setCopied] = useState(false);



  const handleCopy = async () => {

    await navigator.clipboard.writeText(content);

    setCopied(true);

    setTimeout(() => setCopied(false), 2000);

  };



  return (

    <button

      onClick={handleCopy}

      className="px-3 py-1.5 text-sm bg-white border border-slate-300 rounded hover:bg-slate-50 transition-colors"

    >

      {copied ? "Copied!" : "Copy"}

    </button>

  );

}



// v0.2: IOC Summary Card Component

function IOCSummaryCard({

  iocs_local,

  iocs_llm,

  ioc_count,

  threat_intel,

}: {

  iocs_local: IOCsLocal;

  iocs_llm: IOCsLLM;

  ioc_count: IOCCount;

  threat_intel?: any;

}) {

  const [expanded, setExpanded] = useState(false);



  const hasIOCs = ioc_count.total > 0;



  if (!hasIOCs) {

    return (

      <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">

        <p className="text-sm text-slate-500">No IOCs detected</p>

      </div>

    );

  }



  return (

    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">

      <div className="flex items-center justify-between mb-3">

        <h4 className="text-sm font-semibold text-slate-700">IOC Summary</h4>

        <button

          onClick={() => setExpanded(!expanded)}

          className="text-xs text-soc-600 hover:text-soc-700"

        >

          {expanded ? "▼ Collapse" : "▲ Expand"}

        </button>

      </div>



      {/* Counts */}

      <div className="grid grid-cols-4 gap-3 mb-3">

        <div className="text-center">

          <div className="text-2xl font-bold text-soc-600">{ioc_count.ips}</div>

          <div className="text-xs text-slate-500">IPs</div>

        </div>

        <div className="text-center">

          <div className="text-2xl font-bold text-soc-600">{ioc_count.domains}</div>

          <div className="text-xs text-slate-500">Domains</div>

        </div>

        <div className="text-center">

          <div className="text-2xl font-bold text-soc-600">{ioc_count.urls}</div>

          <div className="text-xs text-slate-500">URLs</div>

        </div>

        <div className="text-center">

          <div className="text-2xl font-bold text-soc-600">{ioc_count.hashes}</div>

          <div className="text-xs text-slate-500">Hashes</div>

        </div>

      </div>



      {/* ▲ Expanded: Source breakdown */}

      {expanded && (

        <div className="space-y-3 border-t border-slate-200 pt-3">

          {/* Local IOCs */}

          {(iocs_local.ips.length || iocs_local.domains.length || iocs_local.urls.length || iocs_local.hashes.length) && (

            <div>

              <h5 className="text-xs font-semibold text-slate-600 mb-1">Local (Regex)</h5>

              <div className="grid grid-cols-4 gap-2 text-xs">

                {iocs_local.ips.length > 0 && <div className="p-1 bg-blue-50 rounded">IPs: {iocs_local.ips.length}</div>}

                {iocs_local.domains.length > 0 && <div className="p-1 bg-blue-50 rounded">Domains: {iocs_local.domains.length}</div>}

                {iocs_local.urls.length > 0 && <div className="p-1 bg-blue-50 rounded">URLs: {iocs_local.urls.length}</div>}

                {iocs_local.hashes.length > 0 && <div className="p-1 bg-blue-50 rounded">Hashes: {iocs_local.hashes.length}</div>}

              </div>

            </div>

          )}



          {/* LLM IOCs */}

          {(iocs_llm.ips.length || iocs_llm.domains.length || iocs_llm.urls.length || iocs_llm.hashes.length) && (

            <div>

              <h5 className="text-xs font-semibold text-slate-600 mb-1">AI Supplement</h5>

              <div className="grid grid-cols-4 gap-2 text-xs">

                {iocs_llm.ips.length > 0 && <div className="p-1 bg-purple-50 rounded">IPs: {iocs_llm.ips.length}</div>}

                {iocs_llm.domains.length > 0 && <div className="p-1 bg-purple-50 rounded">Domains: {iocs_llm.domains.length}</div>}

                {iocs_llm.urls.length > 0 && <div className="p-1 bg-purple-50 rounded">URLs: {iocs_llm.urls.length}</div>}

                {iocs_llm.hashes.length > 0 && <div className="p-1 bg-purple-50 rounded">Hashes: {iocs_llm.hashes.length}</div>}

              </div>

            </div>

          )}



          {/* Detailed Lists */}

          <div className="text-xs text-slate-600">

            {iocs_local.ips.length > 0 && (

              <div className="mb-1"><strong>IPs:</strong> {iocs_local.ips.join(", ")}</div>

            )}

            {iocs_local.domains.length > 0 && (

              <div className="mb-1"><strong>Domains:</strong> {iocs_local.domains.join(", ")}</div>

            )}

            {iocs_local.urls.length > 0 && (

              <div className="mb-1"><strong>URLs:</strong> {iocs_local.urls.slice(0, 5).join(", ")}{iocs_local.urls.length > 5 && "..."}</div>

            )}

            {iocs_local.hashes.length > 0 && (

              <div className="mb-1"><strong>Hashes:</strong> {iocs_local.hashes.slice(0, 3).join(", ")}{iocs_local.hashes.length > 3 && "..."}</div>

            )}

          </div>

        </div>

      )}



      {/* v0.4: Threat Intel Section */}

      {threat_intel && <ThreatIntelSection threatIntel={threat_intel} />}

    </div>

  );

}



function AlertAnalyzerTab({ onHistoryToggle }: { onHistoryToggle: () => void }) {

  const [input, setInput] = useState("");

  const [result, setResult] = useState<AlertAnalysisResponse | null>(null);

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [currentHistoryId, setCurrentHistoryId] = useState<string | undefined>();



  const handleAnalyze = async () => {

    if (!input.trim()) return;



    setLoading(true);

    setError(null);

    setResult(null);

    setCurrentHistoryId(undefined);  // Reset history ID



    try {

      const response = await api.analyzeAlert({ raw_log: input });

      setResult(response);



      // Fetch the latest history record to get the ID

      const historyList = await api.listHistory({ module: "analyzer", limit: 1 });

      if (historyList.items.length > 0) {

        setCurrentHistoryId(historyList.items[0].id);

      }

    } catch (e: unknown) {
      const errorMsg = (e as Error)?.message ?? "Analysis failed";
      setError(errorMsg);
    } finally {

      setLoading(false);

    }

  };



  const loadFromHistory = (record: HistoryRecord) => {

    setInput(record.input_text);

    setResult(record.output_json as AlertAnalysisResponse);

    setCurrentHistoryId(record.id);

  };



  return (

    <div className="flex">

      <div className="flex-1 grid grid-cols-2 gap-6">

        <div className="space-y-4">

          <div className="flex items-center justify-between">

            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">

              Input: Raw Alert / Log

            </h3>

            <button

              onClick={onHistoryToggle}

              className="px-3 py-1 text-sm bg-slate-100 hover:bg-slate-200 rounded transition-colors"

            >

              History

            </button>

          </div>

          <textarea

            value={input}

            onChange={(e) => setInput(e.target.value)}

            placeholder="Paste your security alert or log here...

Example:

2025-02-05 10:23:45 WARNING login failed for user admin from 192.168.1.100

2025-02-05 10:23:46 WARNING login failed for user admin from 192.168.1.100

2025-02-05 10:23:47 WARNING login failed for user admin from 192.168.1.100"

            className="w-full h-64 p-3 font-mono text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500 focus:border-soc-500 resize-none"

          />

          <button

            onClick={handleAnalyze}

            disabled={loading || !input.trim()}

            className="w-full py-2.5 bg-soc-600 text-white font-medium rounded-lg hover:bg-soc-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"

          >

            {loading ? "Analyzing..." : "Analyze Alert"}

          </button>

        </div>



        <div className="space-y-4">

          <div className="flex items-center justify-between">

            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Output</h3>

            {result && <CopyButton content={JSON.stringify(result, null, 2)} />}

          </div>



          {loading && <Loading />}

          {error && <Error message={error} />}

          {result && (

            <div className="space-y-4">

              {result.degraded && <DegradedWarning reason={result.error_reason} />}



              {/* v0.2: IOC Summary Card */}

              <IOCSummaryCard

                iocs_local={result.iocs_local}

                iocs_llm={result.iocs_llm}

                ioc_count={result.ioc_count}

                threat_intel={result.threat_intel}

              />



              <div className="flex gap-4 flex-wrap">

                <span className={`px-3 py-1 rounded-full text-sm font-medium border ${SEVERITY_COLORS[result.severity as Severity]}`}>

                  {result.severity.toUpperCase()}

                </span>

                <span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-sm font-medium">

                  {result.event_type.replace("_", " ").toUpperCase()}

                </span>

                <span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-sm font-medium">

                  Confidence: {result.confidence}%

                </span>

                {result.escalation_needed && (

                  <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium">

                    ESCALATE

                  </span>

                )}

                {result.request_id && (

                  <span className="px-3 py-1 bg-slate-100 text-slate-500 rounded-full text-xs font-medium">

                    ID: {result.request_id}

                  </span>

                )}

              </div>



              <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">

                <div>

                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Summary</h4>

                  <p className="text-slate-800 mt-1">{result.summary}</p>

                </div>



                {result.entities.users.length || result.entities.hosts.length || result.entities.processes.length ? (

                  <div>

                    <h4 className="text-xs font-semibold text-slate-500 uppercase">Entities</h4>

                    <div className="mt-1 grid grid-cols-3 gap-2 text-sm">

                      {result.entities.users.length && <div><span className="text-slate-500">Users:</span> {result.entities.users.join(", ")}</div>}

                      {result.entities.hosts.length && <div><span className="text-slate-500">Hosts:</span> {result.entities.hosts.join(", ")}</div>}

                      {result.entities.processes.length && <div><span className="text-slate-500">Processes:</span> {result.entities.processes.join(", ")}</div>}

                    </div>

                  </div>

                ) : null}



                <div>

                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Evidence Points</h4>

                  <ul className="mt-1 space-y-1">

                    {result.evidence_points.map((point, i) => (

                      <li key={i} className="text-sm text-slate-700 flex items-start">

                        <span className="text-soc-500 mr-2">•</span>

                        {point}

                      </li>

                    ))}

                  </ul>

                </div>



                <div>

                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Recommended Actions</h4>

                  <ul className="mt-1 space-y-2">

                    {result.recommended_actions.map((action, i) => (

                      <li key={i} className="text-sm text-slate-700 p-2 bg-slate-50 rounded border border-slate-200">

                        <div className="font-medium text-green-700">•{action.action}</div>

                        <div className="text-xs text-slate-600 mt-1">{action.details}</div>

                        <div className="text-xs text-slate-500 mt-1"><em>Verify: {action.verification}</em></div>

                      </li>

                    ))}

                  </ul>

                </div>

              </div>



              {/* v0.3: Impact Analysis */}

              <ImpactPanel impact={result.impact_analysis} />



              {/* v0.5: Playbook Panel */}

              <PlaybookPanel

                historyId={currentHistoryId}

                iocs={result.iocs}

                module="analyzer"

              />

            </div>

          )}

        </div>

      </div>

    </div>

  );

}



function ReportWriterTab({ onHistoryToggle }: { onHistoryToggle: () => void }) {

  const [input, setInput] = useState("");

  const [notes, setNotes] = useState("");

  const [result, setReportResult] = useState<ReportGenerationResponse | null>(null);

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [reportView, setReportView] = useState<"ticket" | "daily" | "postmortem">("ticket");



  const handleGenerate = async () => {

    if (!input.trim()) return;



    setLoading(true);

    setError(null);

    setReportResult(null);



    try {

      const response = await api.generateReport({

        alert_json: input,

        additional_notes: notes || undefined,

      });

      setReportResult(response);

    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Report generation failed");
    } finally {

      setLoading(false);

    }

  };



  const loadFromHistory = (record: HistoryRecord) => {

    setInput(record.input_text);

    if (record.tags?.has_notes) {

      setNotes("See history record");

    }

    setReportResult(record.output_json as ReportGenerationResponse);

  };



  return (

    <div className="flex">

      <div className="flex-1 grid grid-cols-2 gap-6">

        <div className="space-y-4">

          <div className="flex items-center justify-between">

            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">

              Input: Alert JSON + Notes

            </h3>

            <button

              onClick={onHistoryToggle}

              className="px-3 py-1 text-sm bg-slate-100 hover:bg-slate-200 rounded transition-colors"

            >

              History

            </button>

          </div>

          <textarea

            value={input}

            onChange={(e) => setInput(e.target.value)}

            placeholder="Paste Tab1 output JSON here..."

            className="w-full h-40 p-3 font-mono text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500 focus:border-soc-500 resize-none"

          />

          <textarea

            value={notes}

            onChange={(e) => setNotes(e.target.value)}

            placeholder="Additional notes (optional)..."

            className="w-full h-20 p-3 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500 focus:border-soc-500 resize-none"

          />

          <button

            onClick={handleGenerate}

            disabled={loading || !input.trim()}

            className="w-full py-2.5 bg-soc-600 text-white font-medium rounded-lg hover:bg-soc-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"

          >

            {loading ? "Generating..." : "Generate Reports"}

          </button>

        </div>



        <div className="space-y-4">

          <div className="flex items-center justify-between">

            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Output</h3>

            {result && <CopyButton content={String(result[`${reportView}_template` as keyof typeof result] || "")} />}

          </div>



          {loading && <Loading />}

          {error && <Error message={error} />}

          {result && (

            <div className="space-y-3">

              {result.degraded && <DegradedWarning reason={result.error_reason} />}



              <div className="flex gap-2">

                {[

                  { key: "ticket" as const, label: "Ticket" },

                  { key: "daily" as const, label: "Daily Report" },

                  { key: "postmortem" as const, label: "Postmortem" },

                ].map(({ key, label }) => (

                  <button

                    key={key}

                    onClick={() => setReportView(key)}

                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${

                      reportView === key

                        ? "bg-soc-600 text-white"

                        : "bg-white border border-slate-300 text-slate-700 hover:bg-slate-50"

                    }`}

                  >

                    {label}

                  </button>

                ))}

              </div>

              <div className="bg-white border border-slate-200 rounded-lg p-4 max-h-96 overflow-y-auto">

                <ReactMarkdown className="prose prose-slate max-w-none">

                  {(result[`${reportView}_template` as keyof typeof result] as any) || null}

                </ReactMarkdown>

              </div>

              {result.request_id && (

                <div className="text-xs text-slate-500">Request ID: {result.request_id}</div>

              )}

            </div>

          )}

        </div>

      </div>

    </div>

  );

}



function TimelineBuilderTab({ onHistoryToggle }: { onHistoryToggle: () => void }) {

  const [input, setInput] = useState("");

  const [logType, setLogType] = useState<string>("");

  const [result, setTimelineResult] = useState<TimelineResponse | null>(null);

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [currentHistoryId, setCurrentHistoryId] = useState<string | undefined>();



  const handleBuild = async () => {

    if (!input.trim()) return;



    setLoading(true);

    setError(null);

    setTimelineResult(null);

    setCurrentHistoryId(undefined);  // Reset history ID



    try {

      const response = await api.buildTimeline({

        raw_log: input,

        log_type: logType || undefined,

      });

      setTimelineResult(response);



      // Fetch the latest history record to get the ID

      const historyList = await api.listHistory({ module: "timeline", limit: 1 });

      if (historyList.items.length > 0) {

        setCurrentHistoryId(historyList.items[0].id);

      }

    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Timeline build failed");
    } finally {

      setLoading(false);

    }

  };



  const loadFromHistory = (record: HistoryRecord) => {

    setInput(record.input_text);

    if (record.tags?.log_type) {

      setLogType(record.tags.log_type);

    }

    setTimelineResult(record.output_json as TimelineResponse);

    setCurrentHistoryId(record.id);

  };



  return (

    <div className="flex">

      <div className="flex-1 grid grid-cols-2 gap-6">

        <div className="space-y-4">

          <div className="flex items-center justify-between">

            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">

              Input: Raw Log (Sysmon / Windows / Linux / Nginx)

            </h3>

            <button

              onClick={onHistoryToggle}

              className="px-3 py-1 text-sm bg-slate-100 hover:bg-slate-200 rounded transition-colors"

            >

              History

            </button>

          </div>

          <select

            value={logType}

            onChange={(e) => setLogType(e.target.value)}

            className="w-full p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500 focus:border-soc-500"

          >

            <option value="">Auto-detect</option>

            <option value="sysmon">Sysmon</option>

            <option value="windows">Windows Event Log</option>

            <option value="linux">Linux auth.log</option>

            <option value="nginx">Nginx access.log</option>

          </select>

          <textarea

            value={input}

            onChange={(e) => setInput(e.target.value)}

            placeholder="Paste your log here...

Example (Linux auth.log):

Feb  5 10:23:45 server01 sshd[1234]: Failed password for root from 192.168.1.100 port 22 ssh2

Feb  5 10:23:46 server01 sshd[1234]: Failed password for root from 192.168.1.100 port 22 ssh2"

            className="w-full h-64 p-3 font-mono text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-soc-500 focus:border-soc-500 resize-none"

          />

          <button

            onClick={handleBuild}

            disabled={loading || !input.trim()}

            className="w-full py-2.5 bg-soc-600 text-white font-medium rounded-lg hover:bg-soc-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"

          >

            {loading ? "Building..." : "Build Timeline"}

          </button>

        </div>



        <div className="space-y-4">

          <div className="flex items-center justify-between">

            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Output</h3>

            {result && <CopyButton content={JSON.stringify(result, null, 2)} />}

          </div>



          {loading && <Loading />}

          {error && <Error message={error} />}

          {result && (

            <div className="space-y-4">

              {result.degraded && <DegradedWarning reason={result.error_reason} />}



              {/* v0.2: IOC Summary Card */}

              <IOCSummaryCard

                iocs_local={result.iocs_local}

                iocs_llm={result.iocs_llm}

                ioc_count={result.ioc_count}

                threat_intel={result.threat_intel}

              />



              <div className="bg-white border border-slate-200 rounded-lg p-4">

                <h4 className="text-xs font-semibold text-slate-500 uppercase mb-3">

                  Timeline ({result.timeline.length} events)

                </h4>

                <div className="space-y-2 max-h-64 overflow-y-auto">

                  {result.timeline.map((event, i) => (

                    <div key={i} className="text-sm p-2 bg-slate-50 rounded border border-slate-200">

                      <div className="flex items-center gap-2 mb-1">

                        <span className="font-mono text-xs text-slate-500">{event.timestamp}</span>

                        <span className="px-2 py-0.5 bg-soc-100 text-soc-700 rounded text-xs font-medium">

                          {event.type}

                        </span>

                      </div>

                      <p className="text-slate-700">{event.description}</p>

                    </div>

                  ))}

                </div>

              </div>



              {result.suspicious_top5?.length > 0 && (

                <div className="bg-red-50 border border-red-200 rounded-lg p-4">

                  <h4 className="text-xs font-semibold text-red-700 uppercase mb-3">

                    Suspicious Events (Top 5)

                  </h4>

                  <div className="space-y-2">

                    {result.suspicious_top5.map((item, i) => (

                      <div key={i} className="text-sm">

                        <p className="font-medium text-red-800">

                          {i + 1}. {item.description}

                        </p>

                        <p className="text-red-600 text-xs mt-1">{item.reasoning}</p>

                      </div>

                    ))}

                  </div>

                </div>

              )}



              {result.next_steps?.length > 0 && (

                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">

                  <h4 className="text-xs font-semibold text-amber-700 uppercase mb-3">Next Steps</h4>

                  <ul className="space-y-1">

                    {result.next_steps.map((step, i) => (

                      <li key={i} className="text-sm text-amber-800 flex items-start">

                        <span className="mr-2">{i + 1}.</span>

                        {step}

                      </li>

                    ))}

                  </ul>

                </div>

              )}

              {result.request_id && (

                <div className="text-xs text-slate-500">Request ID: {result.request_id}</div>

              )}



              {/* v0.3: Impact Analysis */}

              <ImpactPanel impact={result.impact_analysis} />



              {/* v0.5: Playbook Panel */}

              <PlaybookPanel

                historyId={currentHistoryId}

                iocs={result.iocs}

                module="timeline"

              />

            </div>

          )}

        </div>

      </div>

    </div>

  );

}



function AssetsTab() {

  return (

    <div className="flex">

      <div className="flex-1">

        <iframe

          src="/assets"

          className="w-full h-[calc(100vh-120px)] border-0"

          title="Assets Management"

        />

      </div>

    </div>

  );

}



export default function HomePage() {

  const router = useRouter();

  const [activeTab, setActiveTab] = useState<Tab>("alert");

  const [apiStatus, setApiStatus] = useState<"checking" | "healthy" | "unhealthy">("checking");

  const [mounted, setMounted] = useState(false);

  const [historyOpen, setHistoryOpen] = useState(false);

  const [user, setUser] = useState<User | null>(null);



  useEffect(() => {

    setMounted(true);



    // Check authentication

    const authState = loadAuthState();

    if (!authState?.isAuthenticated) {

      router.push("/login");

      return;

    }

    setUser(authState.user);



    // Health check

    api.healthCheck()

      .then(() => setApiStatus("healthy"))

      .catch(() => setApiStatus("unhealthy"));

  }, [router]);



  const handleLogout = () => {

    logout();

    router.push("/login");

  };



  // Move early return AFTER all hooks are called

  // We still check mounted but don't return early before hooks are done



  const handleLoadFromHistory = (record: HistoryRecord) => {

    setHistoryOpen(false);

  };



  // Use useCallback to prevent infinite re-renders

  const handleHistoryToggle = useCallback(() => {

    setHistoryOpen(prev => !prev);

  }, []);



  const tabDefs: { key: Tab; label: string }[] = [

    { key: "alert", label: "Alert Analyzer" },

    { key: "timeline", label: "Timeline Builder" },

    { key: "report", label: "Report Writer" },

    { key: "assets", label: "Assets" },

  ];



  // Early return AFTER all hooks are called (React Hooks rule)

  if (!mounted) return null;



  return (

    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">

      {/* Navigation */}

      <Navigation

        title="Security Operations Console"

        subtitle="Alert analysis, timeline, reports & assets"

        apiStatus={apiStatus === "unhealthy" ? "error" : apiStatus as "checking" | "healthy" | undefined}

      />



      {/* Main Content */}

      <main className="flex relative">

        <div className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">

            <div className="border-b border-slate-200">

              <nav className="flex">

                {tabDefs.map((tab) => (

                  <button

                    key={tab.key}

                    onClick={() => {

                      setActiveTab(tab.key);

                      setHistoryOpen(false);

                    }}

                    className={`px-6 py-4 text-sm font-medium transition-colors ${

                      activeTab === tab.key

                        ? "bg-soc-50 text-soc-700 border-b-2 border-soc-600"

                        : "text-slate-500 hover:text-slate-700 hover:bg-slate-50"

                    }`}

                  >

                    {tab.label}

                  </button>

                ))}

              </nav>

            </div>



            <div className="p-6">

              {activeTab === "alert" && <AlertAnalyzerTab onHistoryToggle={handleHistoryToggle} />}

              {activeTab === "report" && <ReportWriterTab onHistoryToggle={handleHistoryToggle} />}

              {activeTab === "timeline" && <TimelineBuilderTab onHistoryToggle={handleHistoryToggle} />}

            </div>

          </div>

        </div>



        {historyOpen && (

          <div className="absolute right-0 top-0 bottom-0 z-10">

            <HistoryPanel

              module={activeTab === "alert" ? "analyzer" : activeTab === "assets" ? "analyzer" : activeTab as "report" | "timeline" | "analyzer"}

              onSelect={() => setHistoryOpen(false)}

              onClose={() => setHistoryOpen(false)}

            />

          </div>

        )}

      </main>

    </div>

  );

}

