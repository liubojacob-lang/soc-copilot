"""
输入验证和清理工具模块
用于防止SQL注入、XSS等安全攻击
"""

import re

from fastapi import HTTPException, status


class ValidationError(Exception):
    """验证错误"""

    pass


def validate_username(username: str) -> str:
    """
    验证用户名格式和安全性
    - 长度：3-50字符
    - 只允许字母、数字、下划线
    - 不允许特殊字符（除了下划线）
    """
    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is required")

    if len(username) < 3 or len(username) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be between 3 and 50 characters",
        )

    # 检查用户名只包含允许的字符
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username can only contain letters, numbers, and underscores",
        )

    return username.strip()


def validate_password(password: str) -> str:
    """
    验证密码强度
    - 最小长度：8字符
    - 必须包含大小写字母、数字
    """
    if not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required")

    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    # 检查密码复杂度
    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_digit = bool(re.search(r"[0-9]", password))

    if not (has_upper and has_lower and has_digit):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain uppercase, lowercase, and digits",
        )

    return password


def validate_email(email: str) -> str:
    """
    验证邮箱格式
    """
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")

    # 基本邮箱格式验证
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")

    return email.strip().lower()


def validate_sql_input(value: str, field_name: str = "input") -> str:
    """
    检测并阻止潜在的SQL注入攻击
    v0.8.4: 优化关键字检测，避免误判正常业务数据

    - 检测SQL注入模式（精确匹配）
    - 检测危险字符组合
    - 不再简单拒绝包含常见单词的输入
    """
    if not value:
        return value

    # v0.8.4: 精确的SQL注入模式检测（而非简单关键字检测）
    # 这些模式检测真正的SQL注入尝试，而不是正常文本中的单词
    sql_injection_patterns = [
        # 经典注入模式
        r"['\"]\s*or\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+",  # ' or '1'='1
        r"['\"]\s*or\s+['\"]?[a-z]+['\"]?\s*=\s*['\"]?[a-z]+",  # ' or 'a'='a
        r"['\"]\s*and\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+",  # ' and '1'='1
        r"1\s*=\s*1",  # 1=1 注入
        r"'\s*;\s*--",  # '; -- 注入
        r"'\s*;\s*(drop|delete|insert|update|select|create|alter|truncate)\s+",  # 语句终止注入
        r";\s*(drop|delete|insert|update|select|create|alter|truncate)\s+",  # 多语句注入
        r"--\s*$",  # SQL注释结尾
        r"/\*.*\*/",  # SQL块注释
        # UNION注入
        r"union\s+(all\s+)?select\s+",  # UNION SELECT
        r"union\s+(all\s+)?select\s+[^;]+from\s+",  # UNION SELECT FROM
        # 堆叠查询
        r";\s*exec(\s+|\()",  # ; exec
        r";\s*execute(\s+|\()",  # ; execute
        # 危险存储过程
        r"xp_(cmdshell|regread|regwrite|dirtree|filelist)",
        r"sp_(oacreate|oamethod|oadestroy|executesql)",
        # 时间盲注
        r"waitfor\s+delay\s+",  # WAITFOR DELAY
        r"benchmark\s*\(",  # MySQL BENCHMARK
        r"sleep\s*\(",  # MySQL SLEEP
        # 布尔盲注特征
        r"'\s*or\s+.*\s*>\s*",  # 比较操作注入
        r"'\s*or\s+.*\s*<\s*",
        # 命令执行
        r"(cmd|shell|exec)\s*\(\s*['\"]",  # 命令执行函数
        # 十六进制编码绕过
        r"0x[0-9a-f]+\s*\|\|",  # 十六进制拼接
        r"char\s*\(\s*\d+\s*\)",  # CHAR()编码
        # 信息泄露
        r"@@(version|hostname|datadir|basedir)",  # MySQL变量
        r"information_schema",  # 系统表
        r"sys\.(objects|tables|columns)",  # SQL Server系统表
    ]

    # 检测SQL注入模式
    for pattern in sql_injection_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {field_name}: potential SQL injection detected",
            )

    # 检测危险字符组合（更精确）
    dangerous_patterns = [
        (r";\s*--", "SQL comment after semicolon"),
        (r"'\s*;\s*--", "SQL injection pattern"),
        (r"'\s*or\s*'", "OR-based injection"),
        (r"'\s*and\s*'", "AND-based injection"),
    ]

    for pattern, desc in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {field_name}: {desc} detected",
            )

    return value


def sanitize_string(value: str, max_length: int | None = None) -> str:
    """
    清理字符串输入，移除潜在危险内容
    - 移除HTML标签
    - 移除危险字符
    - 限制长度
    """
    if not value:
        return ""

    # 移除HTML标签
    clean_value = re.sub(r"<[^>]*>([^<]*)<[^>]*>", "", value)

    # 移除危险字符（保留安全的）
    dangerous_patterns = [
        r"<script[^>]*>.*?</script>",  # Script标签
        r"onerror\s*=",  # 事件处理器注入
        r"onload\s*=",  # 加载事件注入
    ]
    for pattern in dangerous_patterns:
        clean_value = re.sub(pattern, "", clean_value, flags=re.IGNORECASE)

    # 转义单引号（防止注入）
    clean_value = clean_value.replace("'", "''")

    # 应用长度限制
    if max_length and len(clean_value) > max_length:
        clean_value = clean_value[:max_length]

    return clean_value.strip()


def validate_limit(
    value: int, min_val: int = 0, max_val: int = 100, field_name: str = "value"
) -> int:
    """
    验证数值限制
    """
    if value < min_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be at least {min_val}",
        )
    if value > max_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be at most {max_val}",
        )
    return value


def validate_pagination_params(
    offset: int | None = None, limit: int | None = None
) -> tuple[int, int]:
    """
    验证分页参数
    """
    # 默认值
    new_offset = offset if offset is not None else 0
    new_limit = limit if limit is not None else 50

    # 验证范围
    if new_offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offset must be non-negative",
        )

    if new_limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Limit must be at least 1"
        )

    if new_limit > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Limit cannot exceed 500"
        )

    return new_offset, new_limit


def validate_id_format(id_value: str, field_name: str = "id") -> str:
    """
    验证ID格式（UUID或数字或混合格式）
    接受多种常见格式：UUID、纯数字、带前缀的ID等
    标准UUID格式：xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (5组，8-4-4-4-12)
    """
    if not id_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name} is required"
        )

    # 检查是否为标准UUID格式（5组：8-4-4-4-12，共36字符）
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    # 检查是否为UUID格式（无连字符，32个hex字符）
    uuid_pattern_nodash = r"^[0-9a-f]{32}$"

    # 允许的格式：标准UUID、无连字符UUID、数字ID
    if (
        re.match(uuid_pattern, id_value, re.IGNORECASE)
        or re.match(uuid_pattern_nodash, id_value.lower())
        or id_value.isdigit()
    ):
        return id_value

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field_name} format"
    )
