# 样式工具集成指南

已成功集成 `tailwind-merge` + `clsx` + `class-variance-authority (CVA)` 工具链。

## 📦 已安装的依赖

```json
{
  "clsx": "^2.x",
  "tailwind-merge": "^2.x",
  "class-variance-authority": "^0.7.x"
}
```

## 🛠️ 工具说明

### 1. `cn()` - 类名合并工具

位置：`@/lib/utils.ts`

安全地合并 Tailwind CSS 类名，自动处理冲突。

```tsx
import { cn } from "@/lib/utils";

// 基础用法
cn("px-4 py-2", "bg-soc-500");

// 条件类名
cn("px-4 py-2", isActive && "bg-soc-500", !isActive && "bg-gray-200");

// 对象语法
cn("px-4 py-2", {
  "bg-soc-500": isActive,
  "opacity-50": isDisabled,
});

// 数组语法
cn("px-4 py-2", ["bg-soc-500", "rounded-lg"]);
```

### 2. CVA - 组件变体管理

使用 `cva()` 定义类型安全的组件样式变体。

```tsx
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva(
  // 基础样式（所有变体共享）
  "inline-flex items-center justify-center rounded-lg font-medium",
  {
    variants: {
      variant: {
        primary: "bg-soc-600 text-white hover:bg-soc-700",
        secondary: "bg-gray-100 text-gray-900 hover:bg-gray-200",
        ghost: "hover:bg-gray-100",
      },
      size: {
        sm: "px-3 py-1.5 text-sm",
        md: "px-4 py-2.5",
        lg: "px-6 py-3 text-base",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

// 类型可以从变体配置中推断
type ButtonVariant = VariantProps<typeof buttonVariants>["variant"];
```

## 📝 已重构的组件

### Button 组件

位置：`@/components/common/Button.tsx`

```tsx
import { Button, buttonVariants } from "@/components/common";

// 基础用法
<Button variant="primary" size="md">
  Click me
</Button>

// 带加载状态
<Button isLoading>Loading...</Button>

// 带图标
<Button leftIcon={<Icon />} rightIcon={<Icon />}>
  With Icons
</Button>

// 直接使用变体配置（高级用法）
<div className={buttonVariants({ variant: "ghost", size: "sm" })}>
  Custom button
</div>
```

### Card 组件

位置：`@/components/common/Card.tsx`

```tsx
import { Card, StatCard } from "@/components/common";

// 基础用法
<Card variant="elevated" padding="lg" title="Title">
  Card content
</Card>

// 统计卡片
<StatCard
  title="总告警数"
  value={125}
  trend="+12%"
  trendDirection="up"
  colorScheme="soc"
  icon={<AlertTriangle />}
/>
```

### Input 组件库

位置：`@/components/common/Input.tsx`

包含 5 个表单组件：`Input`、`Textarea`、`Select`、`Checkbox`、`Switch`

```tsx
import { Input, Textarea, Select, Checkbox, Switch } from "@/components/common";

// 输入框
<Input label="用户名" placeholder="请输入..." />

// 带错误状态
<Input label="密码" type="password" error="密码不能为空" />

// 带图标
import { Search } from "lucide-react";
<Input label="搜索" leftIcon={<Search className="w-4 h-4" />} />

// 文本域
<Textarea label="描述" placeholder="请输入详细描述..." rows={4} />

// 下拉选择
<Select label="状态" placeholder="请选择">
  <option value="active">活跃</option>
  <option value="inactive">禁用</option>
</Select>

// 复选框
<Checkbox label="我同意服务条款" checked={accepted} />

// 开关
<Switch label="启用通知" checked={enabled} />
```

详细文档请参考：[INPUT_COMPONENTS_GUIDE.md](./INPUT_COMPONENTS_GUIDE.md)

## 🎯 迁移其他组件的步骤

如果你想将其他组件也迁移到 CVA 模式：

```tsx
// 1. 导入依赖
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// 2. 定义变体
const myComponentVariants = cva("base-classes", {
  variants: {
    variant: { ... },
    size: { ... },
  },
  defaultVariants: { ... },
});

// 3. 在组件中使用
function MyComponent({ variant, size, className, ...props }) {
  return (
    <div
      className={cn(myComponentVariants({ variant, size }), className)}
      {...props}
    />
  );
}
```

## 🎨 优势

1. **类型安全**：变体有完整的 TypeScript 类型推断
2. **无冲突**：`tailwind-merge` 自动处理 Tailwind 类冲突
3. **灵活组合**：`clsx` 支持多种条件类名语法
4. **可维护**：样式变体集中管理，易于修改
