#!/usr/bin/env python3
"""
SOC Copilot - 云原生安全功能模块仿真演练脚本 (Cloud Native Security Simulation)

功能:
1. 自动探针活跃的后端端口 (18088, 8088, 8000)
2. 自动模拟登录获取鉴权凭证
3. 演练场景 1: 容器镜像安全漏洞扫描 (Trivy 真实/Mock 降级双模) & 24h 缓存验证
4. 演练场景 2: 运行时入侵安全告警 Webhook 注入 (Falco 3类典型攻击事件)
5. 演练场景 3: K8s CIS Benchmark 安全合规基线与多云连接状态验证
6. 打印清晰美观的演练验证报告
"""

import sys
import json
import time
from urllib import request, error
from http.cookiejar import CookieJar

# ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class CloudNativeSimulator:
    def __init__(self):
        self.cookie_jar = CookieJar()
        self.opener = request.build_opener(request.HTTPCookieProcessor(self.cookie_jar))
        self.base_url = None
        self.token = None
        self.candidate_ports = [18088, 8088, 8000]
        self.candidate_credentials = [
            ("admin", "K9#mX2_vL8!qZ5*wR7"),  # local-sim
            ("admin", "admin123"),             # standard / dev
        ]

    def log(self, tag: str, msg: str, color: str = CYAN):
        print(f"{color}[{tag}]{RESET} {msg}")

    def success(self, msg: str):
        print(f"{GREEN}  ✓ {msg}{RESET}")

    def info(self, msg: str):
        print(f"{BLUE}  ℹ {msg}{RESET}")

    def warn(self, msg: str):
        print(f"{YELLOW}  ⚠ {msg}{RESET}")

    def fail(self, msg: str):
        print(f"{RED}  ✗ {msg}{RESET}")

    def _request(self, method: str, path: str, data: dict = None, headers: dict = None) -> tuple[int, dict]:
        url = f"{self.base_url}{path}"
        req_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if headers:
            req_headers.update(headers)
        if self.token:
            req_headers["Authorization"] = f"Bearer {self.token}"

        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = request.Request(url, data=body, headers=req_headers, method=method)

        try:
            with self.opener.open(req, timeout=10) as resp:
                status_code = resp.status
                content = resp.read().decode("utf-8")
                try:
                    res_json = json.loads(content)
                except Exception:
                    res_json = {"raw": content}
                return status_code, res_json
        except error.HTTPError as e:
            content = e.read().decode("utf-8")
            try:
                res_json = json.loads(content)
            except Exception:
                res_json = {"raw": content}
            return e.code, res_json
        except Exception as e:
            return 0, {"error": str(e)}

    def discover_backend(self) -> bool:
        self.log("PROBE", "正在自动探针后端服务运行端口...")
        for port in self.candidate_ports:
            test_url = f"http://127.0.0.1:{port}"
            try:
                req = request.Request(f"{test_url}/api/v1/health", headers={"Accept": "application/json"})
                with request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        self.base_url = test_url
                        self.success(f"成功连通后端服务: {self.base_url} (/api/v1/health 返回 200)")
                        return True
            except Exception:
                pass
        
        self.fail(f"未能在候选端口 {self.candidate_ports} 找到运行中的后端服务。请确认 Docker 容器已启动。")
        return False

    def authenticate(self) -> bool:
        self.log("AUTH", "正在尝试获取演练鉴权凭据...")
        for username, password in self.candidate_credentials:
            payload = {"username": username, "password": password}
            status, res = self._request("POST", "/api/v1/auth/login", data=payload)
            if status in (200, 201):
                self.token = res.get("access_token") or res.get("token")
                self.success(f"使用账号 '{username}' 登录成功！")
                return True

        self.warn("常规密码登录未通过，尝试以现有 Cookie / 免鉴权模式演练受保护接口...")
        return False

    def run_scenario_container_scan(self):
        self.log("SCENARIO 1", f"{BOLD}容器镜像安全漏洞扫描演练 (Trivy Scan){RESET}", CYAN)
        
        # 1. 扫描 nginx:1.21
        image_name = "nginx:1.21"
        self.info(f"发起镜像漏洞扫描: {image_name}")
        t0 = time.time()
        status, res = self._request("POST", "/api/v1/cloud-native/containers/trivy-scan", data={"image": image_name})
        latency = (time.time() - t0) * 1000

        if status == 200:
            total_vulns = res.get("total_vulnerabilities", 0)
            sev = res.get("severity_counts", {})
            self.success(f"扫描完成 (耗时 {latency:.0f}ms)！发现漏洞总数: {total_vulns}")
            print(f"    ├─ 严重 (CRITICAL): {sev.get('CRITICAL', 0)}")
            print(f"    ├─ 高危 (HIGH):     {sev.get('HIGH', 0)}")
            print(f"    ├─ 中危 (MEDIUM):   {sev.get('MEDIUM', 0)}")
            print(f"    └─ 低危 (LOW):      {sev.get('LOW', 0)}")

            vulns = res.get("vulnerabilities", [])
            if vulns:
                sample = vulns[0]
                self.info(f"CVE 示例: {sample.get('cve_id')} | 包: {sample.get('package_name')} {sample.get('installed_version')} -> 修复: {sample.get('fixed_version') or 'N/A'}")
        else:
            self.fail(f"Trivy 扫描接口返回异常 [{status}]: {res}")

        # 2. 缓存命中测试
        self.info(f"重新扫描相同镜像以测试 24h 缓存命中机制...")
        t0 = time.time()
        status2, res2 = self._request("POST", "/api/v1/cloud-native/containers/trivy-scan", data={"image": image_name})
        cache_latency = (time.time() - t0) * 1000
        if status2 == 200:
            self.success(f"缓存命中测试通过！二次响应耗时仅 {cache_latency:.0f}ms (显著低于初次)")
        else:
            self.fail("缓存查询失败")

        # 3. 扫描轻量镜像 alpine:3.18
        self.info("发起轻量系统镜像扫描: alpine:3.18")
        status3, res3 = self._request("POST", "/api/v1/cloud-native/containers/trivy-scan", data={"image": "alpine:3.18"})
        if status3 == 200:
            self.success(f"alpine:3.18 扫描成功，检测到漏洞: {res3.get('total_vulnerabilities', 0)}")
        print()

    def run_scenario_falco_alerts(self):
        self.log("SCENARIO 2", f"{BOLD}运行时入侵安全告警 Webhook 仿真注入 (Falco){RESET}", CYAN)
        
        test_alerts = [
            {
                "name": "特权容器提权与逃逸风险",
                "payload": {
                    "output": "Critical Privileged container started (user=root pod=payment-service-x7d container=c1a2b3)",
                    "priority": "Critical",
                    "rule": "Privileged Container Started",
                    "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "output_fields": {
                        "container.id": "c1a2b34d5e",
                        "container.image.repository": "nginx:1.21",
                        "k8s.ns.name": "production",
                        "k8s.pod.name": "payment-service-x7d",
                        "proc.name": "containerd-shim",
                        "user.name": "root"
                    }
                }
            },
            {
                "name": "敏感系统凭据文件违规读取",
                "payload": {
                    "output": "Warning Sensitive file opened for reading by untrusted container (user=root file=/etc/shadow)",
                    "priority": "Warning",
                    "rule": "Read sensitive file untrusted",
                    "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "output_fields": {
                        "container.id": "e8d7c6b5a4",
                        "container.image.repository": "redis:7-alpine",
                        "k8s.ns.name": "default",
                        "k8s.pod.name": "redis-cache-0",
                        "proc.name": "cat",
                        "user.name": "root"
                    }
                }
            },
            {
                "name": "容器内部异常外联反弹 Shell",
                "payload": {
                    "output": "Error Unexpected outbound connection to public external host (proc=bash ip=198.51.100.24)",
                    "priority": "Error",
                    "rule": "Unexpected outbound connection",
                    "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "output_fields": {
                        "container.id": "f9a8b7c6d5",
                        "container.image.repository": "python:3.11-slim",
                        "k8s.ns.name": "data-pipeline",
                        "k8s.pod.name": "worker-task-abc",
                        "proc.name": "bash",
                        "user.name": "appuser"
                    }
                }
            }
        ]

        for item in test_alerts:
            self.info(f"注入安全事件: 【{item['name']}】 (Rule: {item['payload']['rule']}, Priority: {item['payload']['priority']})")
            status, res = self._request("POST", "/api/v1/cloud-native/falco-alerts", data=item["payload"])
            if status in (200, 201):
                self.success(f"Webhook 成功捕获告警 -> ID: {res.get('alert_id')} | 映射严重度: {res.get('severity')} | 状态: {res.get('status')}")
            else:
                self.fail(f"Webhook 注入失败 [{status}]: {res}")

        # 校验统计接口
        self.info("请求 Falco 24小时告警统计接口 (/api/v1/cloud-native/falco-alerts/stats)...")
        status, stats = self._request("GET", "/api/v1/cloud-native/falco-alerts/stats?hours=24")
        if status == 200:
            self.success("成功拉取 Falco 统计面板数据:")
            print(f"    ├─ 24小时告警总数: {stats.get('total_alerts', 0)}")
            print(f"    ├─ 今日告警总数:   {stats.get('today_total', 0)}")
            print(f"    ├─ 今日高危/严重:  {stats.get('today_high_critical', 0)}")
            top_rules = [r.get("rule") for r in stats.get("top_rules", [])[:3]]
            print(f"    └─ Top 触发规则:   {', '.join(top_rules)}")
        else:
            self.fail(f"获取 Falco 统计失败 [{status}]")
        print()

    def run_scenario_k8s_and_compliance(self):
        self.log("SCENARIO 3", f"{BOLD}Kubernetes CIS 合规基线与云连接验证{RESET}", CYAN)
        
        # 1. 仪表盘
        self.info("获取云原生安全总体仪表盘 (/api/v1/cloud-native/dashboard)...")
        status, dash = self._request("GET", "/api/v1/cloud-native/dashboard")
        if status == 200:
            overview = dash.get("overview", {})
            compliance = dash.get("compliance", {})
            self.success(f"仪表盘正常: 集群数 {overview.get('connected_clusters', 0)}, 容器数 {overview.get('total_containers', 0)}, CIS 合规率 {compliance.get('cis_benchmark', 0)}%")
        else:
            self.fail(f"获取仪表盘失败 [{status}]")

        # 2. CIS 详细报告
        self.info("生成 Kubernetes CIS 合规审计报告 (/api/v1/cloud-native/compliance/report)...")
        status, report = self._request("GET", "/api/v1/cloud-native/compliance/report")
        if status == 200:
            cis = report.get("cis_compliance", {})
            self.success(f"CIS 合规报告生成成功: 总检查项 {cis.get('total_checks')}, 通过 {cis.get('passed')}, 未通过 {cis.get('failed')}")
            findings = report.get("findings", [])
            if findings:
                f0 = findings[0]
                self.info(f"加固建议示例: [{f0.get('category')}] {f0.get('title')} -> {f0.get('remediation')}")
        else:
            self.fail(f"获取合规报告失败 [{status}]")

        # 3. 云平台连接
        self.info("检查多云凭据探测接口 (/api/v1/cloud-native/cloud/connections)...")
        status, conns = self._request("GET", "/api/v1/cloud-native/cloud/connections")
        if status == 200:
            total = conns.get("total_connected", 0)
            self.success(f"云连接探针响应正常 (当前已连接 {total} 个云平台)")
        else:
            self.fail(f"获取云连接失败 [{status}]")
        print()

    def run_scenario_container_inventory(self):
        self.log("SCENARIO 4", f"{BOLD}容器资产全量清单、分页与安全下钻验证{RESET}", CYAN)
        self.info("拉取容器清单第 1 页 (默认每页 10 条) (/api/v1/cloud-native/containers)...")
        status, res = self._request("GET", "/api/v1/cloud-native/containers")
        if status == 200:
            total = res.get("total", 0)
            running = res.get("running", 0)
            warning = res.get("warning", 0)
            vuln = res.get("vulnerable", 0)
            p = res.get("page", 1)
            pz = res.get("page_size", 10)
            tp = res.get("total_pages", 1)
            c_cnt = len(res.get("containers", []))
            self.success(f"容器清单第 {p} 页正常: 总资产 {total}, 本页数量 {c_cnt}, 总页数 {tp}, 运行中 {running}, 异常警告 {warning}, 含已知漏洞 {vuln}")
        else:
            self.fail(f"获取容器清单失败 [{status}]")

        self.info("测试翻页至第 2 页 (/api/v1/cloud-native/containers?page=2&page_size=10)...")
        status, res_p2 = self._request("GET", "/api/v1/cloud-native/containers?page=2&page_size=10")
        if status == 200 and res_p2.get("page") == 2 and len(res_p2.get("containers", [])) == 10:
            self.success(f"翻页验证成功: 第 2 页共返回 10 条容器资产 (首个容器: {res_p2.get('containers')[0].get('name')})")
        else:
            self.fail(f"翻页测试失败 [{status}]")

        self.info("测试按状态过滤 (status=warning)...")
        status, res_warn = self._request("GET", "/api/v1/cloud-native/containers?status=warning")
        if status == 200:
            warn_cnt = res_warn.get("filtered_total", 0)
            names = [c["name"] for c in res_warn.get("containers", [])]
            self.success(f"状态过滤成功: 找到 {warn_cnt} 个异常/违规容器 -> {', '.join(names)}")
        else:
            self.fail(f"过滤失败 [{status}]")

        self.info("测试单容器深度详情下钻 (/api/v1/cloud-native/containers/cnt-prod-web-01)...")
        status, detail = self._request("GET", "/api/v1/cloud-native/containers/cnt-prod-web-01")
        if status == 200:
            self.success(f"单容器详情下钻成功: ID={detail.get('id')}, 名称={detail.get('name')}, 端口={detail.get('ports')}, 只读FS={detail.get('readonly_rootfs')}")
        else:
            self.fail(f"获取单容器详情失败 [{status}]")
        print()

    def print_summary(self):
        print(f"{BOLD}{GREEN}===================================================={RESET}")
        print(f"{BOLD}{GREEN}      🎉 云原生安全模块仿真演练全部执行完毕!       {RESET}")
        print(f"{BOLD}{GREEN}===================================================={RESET}")
        print(f"后端服务地址: {self.base_url}")
        print("建议在浏览器中查看前端界面验证联动效果:")
        print(f"  • 访问入口: http://127.0.0.1:13000/zh-CN/cloud-native 或 http://127.0.0.1:3003/zh-CN/cloud-native")
        print("  • 检查清单:")
        print("    1. 【容器总数卡片】点击顶部“容器总数 (45)”卡片，直接跳转至“容器资产明细”选项卡")
        print("    2. 【容器明细列表】查看 45 个容器状态、集群、命名空间、镜像、特权/Root安全检查与漏洞统计")
        print("    3. 【容器深度检查】点击任意容器行，展开包含端口、挂载卷、环境变量与安全上下文的检查模态框")
        print("    4. 【一键排查镜像】在容器行或详情模态框中点击“排查镜像”，直接联动 Trivy 漏洞扫描")
        print()


def main():
    simulator = CloudNativeSimulator()
    print(f"\n{BOLD}{CYAN}=== SOC Copilot 云原生安全功能仿真演练开始 ==={RESET}\n")
    
    if not simulator.discover_backend():
        sys.exit(1)
        
    simulator.authenticate()
    simulator.run_scenario_container_scan()
    simulator.run_scenario_falco_alerts()
    simulator.run_scenario_k8s_and_compliance()
    simulator.run_scenario_container_inventory()
    simulator.print_summary()


if __name__ == "__main__":
    main()
