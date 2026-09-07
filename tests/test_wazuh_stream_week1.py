#!/usr/bin/env python3
"""
Week 1 实时告警流测试脚本

测试 Wazuh WebSocket 实时告警流的所有功能
"""

import asyncio
import json
import time
from datetime import datetime
import requests
import websockets
from websockets.exceptions import ConnectionClosedError

# 配置
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/api/v1/wazuh/stream/ws"

# 颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text: str):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def get_auth_token() -> str:
    """获取认证 token"""
    print_info("正在获取认证 token...")

    # 尝试使用默认管理员登录
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "username": "admin",
            "password": "admin123!"  # 根据您的实际情况调整
        }
    )

    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print_success(f"获取 token 成功: {token[:20]}...")
        return token
    else:
        print_error(f"登录失败: {response.status_code} - {response.text}")
        return None


def test_start_stream_service(token: str) -> bool:
    """测试启动流服务"""
    print_header("测试 1: 启动流服务")

    response = requests.post(
        f"{BASE_URL}/api/v1/wazuh/stream/start",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        data = response.json()
        print_success("流服务启动成功")
        print_info(f"  运行状态: {data.get('running')}")
        if data.get('stats'):
            stats = data['stats']
            print_info(f"  总告警数: {stats.get('total_alerts', 0)}")
        return True
    else:
        print_error(f"启动流服务失败: {response.status_code}")
        print_error(f"  {response.text}")
        return False


def test_stream_status(token: str) -> bool:
    """测试流服务状态"""
    print_header("测试 2: 检查流服务状态")

    response = requests.get(
        f"{BASE_URL}/api/v1/wazuh/stream/status",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        data = response.json()
        print_success("状态查询成功")
        print_info(f"  运行中: {data.get('running')}")
        if data.get('config'):
            config = data['config']
            print_info(f"  聚合窗口: {config.get('aggregation_window_seconds')} 秒")
            print_info(f"  最大缓冲: {config.get('max_buffer_size')}")
            print_info(f"  历史缓存: {config.get('max_history_size')}")
        return True
    else:
        print_error(f"状态查询失败: {response.status_code}")
        return False


def test_stream_stats(token: str) -> bool:
    """测试流服务统计"""
    print_header("测试 3: 获取流统计信息")

    response = requests.get(
        f"{BASE_URL}/api/v1/wazuh/stream/stats",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        data = response.json()
        print_success("统计信息获取成功")
        print_info(f"  总告警数: {data.get('total_alerts', 0)}")

        if data.get('alerts_by_severity'):
            print_info("  按严重级别分布:")
            for severity, count in data['alerts_by_severity'].items():
                print_info(f"    {severity}: {count}")

        if data.get('top_agents'):
            print_info("  Top Agent:")
            for agent in data['top_agents'][:3]:
                print_info(f"    {agent['name']}: {agent['count']} 告警")

        return True
    else:
        print_error(f"统计信息获取失败: {response.status_code}")
        return False


async def test_websocket_connection(token: str) -> bool:
    """测试 WebSocket 连接"""
    print_header("测试 4: WebSocket 连接")

    ws_url = f"{WS_URL}?token={token}&channels=wazuh"

    try:
        print_info(f"正在连接到 {ws_url}...")
        async with websockets.connect(ws_url) as websocket:
            print_success("WebSocket 连接成功")

            # 等待欢迎消息
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                print_success(f"收到欢迎消息: {data.get('type')}")

                if data.get('type') == 'system':
                    print_info(f"  消息: {data.get('data', {}).get('message')}")

                return True

            except asyncio.TimeoutError:
                print_warning("未收到欢迎消息（但连接成功）")
                return True

    except ConnectionRefusedError:
        print_error("连接被拒绝 - WebSocket 服务可能未启动")
        return False
    except Exception as e:
        print_error(f"WebSocket 连接失败: {e}")
        return False


async def test_receive_alerts(token: str, duration: int = 10) -> bool:
    """测试接收实时告警"""
    print_header(f"测试 5: 接收实时告警 (等待 {duration} 秒)")

    ws_url = f"{WS_URL}?token={token}&channels=wazuh"

    try:
        async with websockets.connect(ws_url) as websocket:
            print_success("已连接到 WebSocket")

            # 先发送一个测试告警
            print_info("正在发送测试告警...")
            test_response = requests.post(
                f"{BASE_URL}/api/v1/wazuh/stream/test-alert",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "agent_id": "001",
                    "severity": "high",
                    "event_type": "ssh_login",
                    "count": 3
                }
            )

            if test_response.status_code == 200:
                print_success(f"测试告警已发送: {test_response.json().get('message')}")
            else:
                print_warning(f"测试告警发送失败: {test_response.status_code}")

            # 等待接收告警
            print_info(f"等待接收告警（{duration} 秒）...")

            alerts_received = []
            start_time = time.time()

            while time.time() - start_time < duration:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)

                    if data.get('type') in ['alert', 'aggregated_alert']:
                        alert_data = data.get('data', {})
                        alerts_received.append(alert_data)
                        print_success(f"收到告警 #{len(alerts_received)}")
                        print_info(f"  ID: {alert_data.get('id', 'N/A')}")
                        print_info(f"  标题: {alert_data.get('title', 'N/A')}")
                        print_info(f"  严重级别: {alert_data.get('severity', 'N/A')}")
                        print_info(f"  事件类型: {alert_data.get('event_type', 'N/A')}")

                except asyncio.TimeoutError:
                    continue
                except ConnectionClosedError:
                    print_error("WebSocket 连接已关闭")
                    break

            print_success(f"测试完成！共收到 {len(alerts_received)} 个告警")
            return len(alerts_received) > 0

    except Exception as e:
        print_error(f"接收告警测试失败: {e}")
        return False


def test_history_api(token: str) -> bool:
    """测试历史告警 API"""
    print_header("测试 6: 获取历史告警")

    response = requests.get(
        f"{BASE_URL}/api/v1/wazuh/stream/history",
        params={"limit": 10},
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        alerts = response.json()
        print_success(f"获取历史告警成功: {len(alerts)} 条")

        if alerts:
            print_info("  最新告警:")
            for alert in alerts[:3]:
                print_info(f"    - {alert.get('title', 'N/A')} ({alert.get('severity', 'N/A')})")

        return True
    else:
        print_error(f"获取历史告警失败: {response.status_code}")
        return False


def test_send_multiple_test_alerts(token: str) -> bool:
    """测试发送多个不同类型的测试告警"""
    print_header("测试 7: 发送多种类型测试告警")

    test_cases = [
        {"agent_id": "001", "severity": "critical", "event_type": "ransomware", "count": 1},
        {"agent_id": "002", "severity": "high", "event_type": "ssh_bruteforce", "count": 2},
        {"agent_id": "003", "severity": "medium", "event_type": "malware", "count": 3},
        {"agent_id": "004", "severity": "low", "event_type": "web_attack", "count": 1},
    ]

    total_sent = 0
    for i, test_case in enumerate(test_cases, 1):
        print_info(f"发送测试告警 {i}/{len(test_cases)}...")

        response = requests.post(
            f"{BASE_URL}/api/v1/wazuh/stream/test-alert",
            headers={"Authorization": f"Bearer {token}"},
            json=test_case
        )

        if response.status_code == 200:
            result = response.json()
            print_success(f"  {test_case['severity']} - {test_case['event_type']}: {result.get('alerts_sent')} 个告警")
            total_sent += result.get('alerts_sent', 0)
        else:
            print_error(f"  发送失败: {response.status_code}")

    print_success(f"总共发送了 {total_sent} 个测试告警")
    return total_sent > 0


def test_websocket_stats(token: str) -> bool:
    """测试 WebSocket 连接统计"""
    print_header("测试 8: WebSocket 连接统计")

    response = requests.get(
        f"{BASE_URL}/api/v1/ws/stats",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        stats = response.json()
        print_success("获取 WebSocket 统计成功")
        print_info(f"  活跃连接数: {stats.get('active_connections', 0)}")

        if stats.get('channels'):
            print_info("  频道订阅:")
            for channel, count in stats['channels'].items():
                print_info(f"    {channel}: {count} 订阅")

        return True
    else:
        print_error(f"获取统计失败: {response.status_code}")
        return False


async def run_all_tests():
    """运行所有测试"""
    print_header("Wazuh 实时告警流 - Week 1 测试套件")
    print_info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 获取认证 token
    token = get_auth_token()
    if not token:
        print_error("无法获取认证 token，测试中止")
        return

    # 同步测试
    tests = [
        ("启动流服务", lambda: test_start_stream_service(token)),
        ("检查流服务状态", lambda: test_stream_status(token)),
        ("获取流统计信息", lambda: test_stream_stats(token)),
        ("获取历史告警", lambda: test_history_api(token)),
        ("发送多种测试告警", lambda: test_send_multiple_test_alerts(token)),
        ("WebSocket 连接统计", lambda: test_websocket_stats(token)),
    ]

    sync_results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            sync_results.append((test_name, result))
        except Exception as e:
            print_error(f"{test_name} 异常: {e}")
            sync_results.append((test_name, False))
        time.sleep(0.5)

    # 异步测试
    async_tests = [
        ("WebSocket 连接", lambda: test_websocket_connection(token)),
        ("接收实时告警", lambda: test_receive_alerts(token, duration=5)),
    ]

    async_results = []
    for test_name, test_func in async_tests:
        try:
            result = await test_func()
            async_results.append((test_name, result))
        except Exception as e:
            print_error(f"{test_name} 异常: {e}")
            async_results.append((test_name, False))

    # 打印测试总结
    print_header("测试总结")

    all_results = sync_results + async_results
    passed = sum(1 for _, result in all_results if result)
    total = len(all_results)

    for test_name, result in all_results:
        if result:
            print_success(f"{test_name}: 通过")
        else:
            print_error(f"{test_name}: 失败")

    print(f"\n{Colors.BOLD}测试结果: {passed}/{total} 通过{Colors.ENDC}")

    if passed == total:
        print(f"{Colors.OKGREEN}{Colors.BOLD}🎉 所有测试通过！Week 1 功能验证成功！{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}{Colors.BOLD}⚠ 部分测试失败，请检查上述错误信息{Colors.ENDC}")


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print_warning("\n测试被用户中断")
    except Exception as e:
        print_error(f"测试运行异常: {e}")
