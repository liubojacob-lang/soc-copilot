"use client";

import { ShieldAlert, Activity, Zap, Clock, ArrowUpRight, Bell } from "lucide-react";
import { Card } from "@/components/common/Card";
import { StatCard } from "@/components/dashboard/StatCard";
import { Button } from "@/components/common/Button";
import { FadeInUp } from "@/components/common/FadeIn";

export function DashboardExample() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">安全运营中心</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">实时监控您的系统安全状态</p>
        </div>
        <Button rightIcon={<ArrowUpRight />}>查看报告</Button>
      </div>

      <FadeInUp>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <StatCard
            title="总告警数"
            value="1,234"
            trend="+12%"
            trendDirection="up"
            icon={<Activity className="w-6 h-6" />}
            subtitle="过去 24 小时"
          />
          <StatCard
            title="高严重告警"
            value="42"
            trend="-8%"
            trendDirection="down"
            icon={<ShieldAlert className="w-6 h-6" />}
            subtitle="需要立即处理"
          />
          <StatCard
            title="处理中"
            value="18"
            trend="+3%"
            trendDirection="neutral"
            icon={<Clock className="w-6 h-6" />}
            subtitle="正在调查"
          />
          <StatCard
            title="已解决"
            value="328"
            trend="+24%"
            trendDirection="up"
            icon={<Zap className="w-6 h-6" />}
            subtitle="本周"
          />
        </div>
      </FadeInUp>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card
            title="最新告警"
            subtitle="最近的 10 条告警"
            icon={<Bell className="w-5 h-5 text-soc-600 dark:text-soc-400" />}
            action={
              <Button variant="ghost" size="sm">
                查看全部
              </Button>
            }
          >
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="flex items-start gap-4 p-4 rounded-xl bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                >
                  <div
                    className={`w-3 h-3 rounded-full mt-2 ${
                      i % 3 === 0 ? "bg-danger-500" : i % 2 === 0 ? "bg-warning-500" : "bg-soc-500"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        可疑登录尝试 #{i}
                      </h4>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {10 - i} 分钟前
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      IP 地址 192.168.1.{100 + i} 尝试多次登录失败
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="快速操作" icon={<Zap className="w-5 h-5 text-yellow-500" />}>
            <div className="space-y-3">
              <Button className="w-full justify-start" leftIcon={<ShieldAlert />}>
                发起威胁狩猎
              </Button>
              <Button variant="secondary" className="w-full justify-start" leftIcon={<Activity />}>
                查看系统状态
              </Button>
              <Button variant="ghost" className="w-full justify-start" leftIcon={<Bell />}>
                配置告警规则
              </Button>
            </div>
          </Card>

          <Card title="系统健康状态">
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600 dark:text-gray-400">API 服务</span>
                  <span className="text-success-600 dark:text-success-400 font-medium">健康</span>
                </div>
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full w-4/5 bg-success-500 rounded-full" />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600 dark:text-gray-400">数据库</span>
                  <span className="text-success-600 dark:text-success-400 font-medium">健康</span>
                </div>
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full w-3/4 bg-success-500 rounded-full" />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600 dark:text-gray-400">消息队列</span>
                  <span className="text-warning-600 dark:text-warning-400 font-medium">警告</span>
                </div>
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full w-1/2 bg-warning-500 rounded-full" />
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
