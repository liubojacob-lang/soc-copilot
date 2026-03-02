# Input 组件库使用指南

已创建完整的表单输入组件库，基于 CVA + tailwind-merge。

## 📦 组件列表

- `Input` - 文本输入框
- `Textarea` - 多行文本输入
- `Select` - 下拉选择框
- `Checkbox` - 复选框
- `Switch` - 开关切换

## 🎨 基础用法

### Input 组件

```tsx
import { Input } from "@/components/common/Input";

// 基础输入框
<Input placeholder="请输入..." />

// 带标签
<Input label="用户名" placeholder="请输入用户名" />

// 带帮助文字
<Input
  label="邮箱"
  placeholder="your@email.com"
  helperText="我们不会分享您的邮箱"
/>

// 错误状态
<Input
  label="密码"
  type="password"
  error="密码至少需要8个字符"
/>

// 带图标
import { Search, Mail } from "lucide-react";

<Input
  label="搜索"
  placeholder="搜索..."
  leftIcon={<Search className="w-4 h-4" />}
/>

<Input
  label="邮箱"
  rightIcon={<Mail className="w-4 h-4" />}
/>

// 尺寸
<Input size="sm" placeholder="小号" />
<Input size="md" placeholder="中号（默认）" />
<Input size="lg" placeholder="大号" />

// 变体
<Input variant="default" placeholder="默认" />
<Input variant="error" placeholder="错误" />
<Input variant="success" placeholder="成功" />
```

### Textarea 组件

```tsx
import { Textarea } from "@/components/common/Input";

<Textarea
  label="描述"
  placeholder="请输入详细描述..."
  rows={4}
/>

<Textarea
  label="备注"
  helperText="最多支持500字"
/>

<Textarea
  label="错误示例"
  error="内容不能为空"
/>
```

### Select 组件

```tsx
import { Select } from "@/components/common/Input";

<Select
  label="状态"
  placeholder="请选择状态"
>
  <option value="active">活跃</option>
  <option value="inactive">禁用</option>
  <option value="pending">待审核</option>
</Select>

<Select
  label="优先级"
  variant="error"
  error="请选择优先级"
>
  <option value="high">高</option>
  <option value="medium">中</option>
  <option value="low">低</option>
</Select>
```

### Checkbox 组件

```tsx
import { Checkbox } from "@/components/common/Input";

<Checkbox
  label="我同意服务条款"
  checked={accepted}
  onChange={(e) => setAccepted(e.target.checked)}
/>

<Checkbox
  label="记住我"
  defaultChecked
/>

<Checkbox
  label="有错误的选项"
  error="必须勾选此项"
/>
```

### Switch 组件

```tsx
import { Switch } from "@/components/common/Input";

<Switch
  label="启用通知"
  checked={enabled}
  onChange={(e) => setEnabled(e.target.checked)}
/>

<Switch
  label="深色模式"
  defaultChecked
/>
```

## 📝 完整表单示例

```tsx
import { useState } from "react";
import { Input, Textarea, Select, Checkbox, Switch, Button } from "@/components/common";

function RegistrationForm() {
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    bio: "",
    role: "",
    acceptTerms: false,
    notifications: true,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.username) newErrors.username = "用户名不能为空";
    if (!formData.email) newErrors.email = "邮箱不能为空";
    if (!formData.acceptTerms) newErrors.acceptTerms = "请同意服务条款";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      // 提交表单
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-lg">
      <Input
        label="用户名"
        placeholder="请输入用户名"
        value={formData.username}
        onChange={(e) => setFormData({ ...formData, username: e.target.value })}
        error={errors.username}
      />

      <Input
        label="邮箱"
        type="email"
        placeholder="your@email.com"
        value={formData.email}
        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
        error={errors.email}
      />

      <Input
        label="密码"
        type="password"
        placeholder="请输入密码"
        value={formData.password}
        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
      />

      <Select
        label="角色"
        placeholder="请选择角色"
        value={formData.role}
        onChange={(e) => setFormData({ ...formData, role: e.target.value })}
      >
        <option value="user">普通用户</option>
        <option value="admin">管理员</option>
        <option value="editor">编辑</option>
      </Select>

      <Textarea
        label="个人简介"
        placeholder="介绍一下你自己..."
        rows={3}
        value={formData.bio}
        onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
      />

      <Checkbox
        label="我同意服务条款和隐私政策"
        checked={formData.acceptTerms}
        onChange={(e) => setFormData({ ...formData, acceptTerms: e.target.checked })}
        error={errors.acceptTerms}
      />

      <Switch
        label="接收邮件通知"
        checked={formData.notifications}
        onChange={(e) => setFormData({ ...formData, notifications: e.target.checked })}
      />

      <Button type="submit" className="w-full">
        注册
      </Button>
    </form>
  );
}
```

## 🎨 样式变体

所有输入组件都支持以下变体：

| 变体 | 说明 |
|------|------|
| `default` | 默认样式，灰色边框 |
| `error` | 错误状态，红色边框 |
| `success` | 成功状态，绿色边框 |

所有输入组件都支持以下尺寸：

| 尺寸 | 说明 |
|------|------|
| `sm` | 小号 |
| `md` | 中号（默认） |
| `lg` | 大号 |

## 🔧 Props

### Input Props

| Prop | 类型 | 默认 | 说明 |
|------|------|------|------|
| `variant` | `default \| error \| success` | `default` | 样式变体 |
| `size` | `sm \| md \| lg` | `md` | 尺寸 |
| `label` | `string` | - | 标签文字 |
| `helperText` | `string` | - | 帮助文字 |
| `error` | `string` | - | 错误信息 |
| `leftIcon` | `ReactNode` | - | 左侧图标 |
| `rightIcon` | `ReactNode` | - | 右侧图标 |
| `className` | `string` | - | 自定义类名 |

### Textarea Props

| Prop | 类型 | 默认 | 说明 |
|------|------|------|------|
| `variant` | `default \| error \| success` | `default` | 样式变体 |
| `size` | `sm \| md \| lg` | `md` | 尺寸 |
| `label` | `string` | - | 标签文字 |
| `helperText` | `string` | - | 帮助文字 |
| `error` | `string` | - | 错误信息 |
| `className` | `string` | - | 自定义类名 |

### Select Props

| Prop | 类型 | 默认 | 说明 |
|------|------|------|------|
| `variant` | `default \| error \| success` | `default` | 样式变体 |
| `size` | `sm \| md \| lg` | `md` | 尺寸 |
| `label` | `string` | - | 标签文字 |
| `helperText` | `string` | - | 帮助文字 |
| `error` | `string` | - | 错误信息 |
| `placeholder` | `string` | - | 占位选项文字 |
| `className` | `string` | - | 自定义类名 |

### Checkbox Props

| Prop | 类型 | 默认 | 说明 |
|------|------|------|------|
| `label` | `string` | - | 标签文字 |
| `error` | `string` | - | 错误信息 |
| `className` | `string` | - | 自定义类名 |

### Switch Props

| Prop | 类型 | 默认 | 说明 |
|------|------|------|------|
| `label` | `string` | - | 标签文字 |
| `className` | `string` | - | 自定义类名 |
