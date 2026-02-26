'use client';

/**
 * Threat Intelligence Dashboard Page
 * 威胁情报仪表盘
 */

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { RefreshCw, Download, Calendar, Filter } from 'lucide-react';
import Navigation from '@/components/Navigation';

// Components
import { TrendsChart, SimpleTrendChart } from '@/components/monitor/TrendsChart';
import { SeverityDistribution, SeverityCards, SeverityBars } from '@/components/monitor/SeverityDistribution';
import { TopSources, SimpleTopSources } from '@/components/monitor/TopSources';
import { MITREHeatmap, SimpleMITRETactics } from '@/components/monitor/MITREHeatmap';
import { IOCStats } from '@/components/monitor/IOCStats';
import { AlertWebSocket } from '@/components/AlertWebSocket';

// Mock Data - TODO: Replace with API calls
const mockTrendData = [
  { timestamp: '2026-02-19T00:00:00Z', date: '2026-02-19', total: 45, critical: 2, high: 8, medium: 15, low: 20 },
  { timestamp: '2026-02-20T00:00:00Z', date: '2026-02-20', total: 52, critical: 3, high: 10, medium: 18, low: 21 },
  { timestamp: '2026-02-21T00:00:00Z', date: '2026-02-21', total: 38, critical: 1, high: 7, medium: 12, low: 18 },
  { timestamp: '2026-02-22T00:00:00Z', date: '2026-02-22', total: 65, critical: 5, high: 15, medium: 20, low: 25 },
  { timestamp: '2026-02-23T00:00:00Z', date: '2026-02-23', total: 48, critical: 2, high: 9, medium: 16, low: 21 },
  { timestamp: '2026-02-24T00:00:00Z', date: '2026-02-24', total: 55, critical: 4, high: 12, medium: 18, low: 21 },
  { timestamp: '2026-02-25T00:00:00Z', date: '2026-02-25', total: 62, critical: 3, high: 14, medium: 22, low: 23 },
];

const mockSeverityData = {
  critical: 20,
  high: 75,
  medium: 121,
  low: 149,
  info: 45,
};

const mockTopSources = [
  { type: 'ip' as const, value: '192.168.1.100', count: 45, severity: 'critical' as const, country: 'CN', first_seen: '2026-02-20', last_seen: '2026-02-25' },
  { type: 'ip' as const, value: '203.0.113.50', count: 32, severity: 'high' as const, country: 'RU', first_seen: '2026-02-19', last_seen: '2026-02-25' },
  { type: 'domain' as const, value: 'malicious-example.com', count: 28, severity: 'critical' as const, country: 'US', first_seen: '2026-02-21', last_seen: '2026-02-25' },
  { type: 'ip' as const, value: '10.0.0.55', count: 25, severity: 'medium' as const, country: 'DE', first_seen: '2026-02-22', last_seen: '2026-02-25' },
  { type: 'domain' as const, value: 'suspicious-site.net', count: 22, severity: 'high' as const, country: 'UK', first_seen: '2026-02-23', last_seen: '2026-02-25' },
];

const mockMITREData = [
  {
    tactic: 'Initial Access',
    tactic_id: 'TA0001',
    techniques: [
      { technique: 'Spearphishing Link', technique_id: 'T1566', count: 25 },
      { technique: 'Exploit Public-Facing Application', technique_id: 'T1190', count: 18 },
      { technique: 'Valid Accounts', technique_id: 'T1078', count: 12 },
    ],
  },
  {
    tactic: 'Execution',
    tactic_id: 'TA0002',
    techniques: [
      { technique: 'Command and Scripting Interpreter', technique_id: 'T1059', count: 35 },
      { technique: 'User Execution', technique_id: 'T1204', count: 22 },
    ],
  },
  {
    tactic: 'Persistence',
    tactic_id: 'TA0003',
    techniques: [
      { technique: 'Scheduled Task/Job', technique_id: 'T1053', count: 15 },
      { technique: 'Create Account', technique_id: 'T1136', count: 8 },
    ],
  },
  {
    tactic: 'Defense Evasion',
    tactic_id: 'TA0005',
    techniques: [
      { technique: 'Obfuscated Files or Information', technique_id: 'T1027', count: 20 },
      { technique: 'Process Injection', technique_id: 'T1055', count: 14 },
    ],
  },
];

const mockIOCStats = {
  total: 410,
  malicious: 45,
  suspicious: 82,
  benign: 156,
  unknown: 127,
};

const mockIOCBreakdown = [
  { type: 'ip' as const, total: 125, malicious: 20, suspicious: 30, trend: 'up' as const },
  { type: 'domain' as const, total: 85, malicious: 15, suspicious: 18, trend: 'stable' as const },
  { type: 'url' as const, total: 92, malicious: 8, suspicious: 20, trend: 'down' as const },
  { type: 'hash' as const, total: 108, malicious: 2, suspicious: 14, trend: 'stable' as const },
];

export default function ThreatIntelDashboardPage() {
  const t = useTranslations();
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<'7d' | '30d' | '90d'>('7d');

  // 获取仪表盘数据
  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // TODO: 替换为实际 API 调用
      // const response = await fetch(`/api/v1/alerts/statistics/trends?range=${dateRange}`);
      // const data = await response.json();

      // 模拟加载延迟
      await new Promise(resolve => setTimeout(resolve, 500));
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  // 导出报告
  const handleExport = async () => {
    try {
      // TODO: 实现导出功能
      console.log('Exporting dashboard...');
    } catch (error) {
      console.error('Failed to export:', error);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [dateRange]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <AlertWebSocket />
      <Navigation
        title="Threat Intelligence Dashboard"
        subtitle="Security threat overview and analysis"
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Threat Intelligence Overview
            </h1>

            {/* Date Range Selector */}
            <div className="flex items-center gap-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-1">
              {(['7d', '30d', '90d'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setDateRange(range)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    dateRange === range
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  {range === '7d' ? '7 Days' : range === '30d' ? '30 Days' : '90 Days'}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchDashboardData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={handleExport}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <KPICard
            label="Total Alerts"
            value={410}
            change="+12%"
            trend="up"
            color="blue"
          />
          <KPICard
            label="Critical Threats"
            value={20}
            change="+5%"
            trend="up"
            color="red"
          />
          <KPICard
            label="Malicious IOCs"
            value={45}
            change="-8%"
            trend="down"
            color="orange"
          />
          <KPICard
            label="Active Campaigns"
            value={8}
            change="+2"
            trend="up"
            color="purple"
          />
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Trends Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Alert Trends (Last 7 Days)
            </h3>
            <TrendsChart data={mockTrendData} type="area" height={250} />
          </div>

          {/* Severity Distribution */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Severity Distribution
            </h3>
            <SeverityDistribution data={mockSeverityData} type="donut" height={250} />
          </div>
        </div>

        {/* Middle Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Top Threat Sources */}
          <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Top Threat Sources
            </h3>
            <TopSources sources={mockTopSources} limit={8} />
          </div>

          {/* Severity Breakdown */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Severity Breakdown
            </h3>
            <SeverityBars data={mockSeverityData} limit={5} />
          </div>
        </div>

        {/* Bottom Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* MITRE ATT&CK Heatmap */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              MITRE ATT&CK Coverage
            </h3>
            <MITREHeatmap data={mockMITREData} />
          </div>

          {/* IOC Statistics */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              IOC Statistics
            </h3>
            <IOCStats stats={mockIOCStats} breakdown={mockIOCBreakdown} />
          </div>
        </div>
      </main>
    </div>
  );
}

// KPI Card Component
interface KPICardProps {
  label: string;
  value: number;
  change: string;
  trend: 'up' | 'down';
  color: 'blue' | 'red' | 'orange' | 'purple';
}

function KPICard({ label, value, change, trend, color }: KPICardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    red: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    orange: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
    purple: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800',
  };

  const trendColor = trend === 'up' && (color === 'red' || color === 'orange')
    ? 'text-red-600'
    : trend === 'up'
    ? 'text-green-600'
    : 'text-green-600';

  return (
    <div className={`${colorClasses[color]} rounded-lg border p-4`}>
      <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
        {label}
      </div>
      <div className="flex items-end justify-between">
        <div className="text-3xl font-bold text-gray-900 dark:text-white">{value}</div>
        <div className={`text-sm font-medium ${trendColor}`}>
          {change}
        </div>
      </div>
    </div>
  );
}
