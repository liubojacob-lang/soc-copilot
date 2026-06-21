// 通用组件统一导出

// 无障碍组件
export { SkipToContent } from "./SkipToContent";

// 按钮组件
export { Button, buttonVariants } from "./Button";
export type { ButtonProps, ButtonVariant, ButtonSize } from "./Button";

// 卡片组件
export { Card, cardVariants } from "./Card";
export type { CardProps, CardVariant, CardPadding } from "./Card";
export { StatCard } from "@/components/dashboard/StatCard";
export type { StatCardProps, TrendDirection } from "@/components/dashboard/StatCard";

// 表单输入组件
export { Input, Textarea, Select, Checkbox, Switch, inputVariants } from "./Input";
export type {
  InputProps,
  TextareaProps,
  SelectProps,
  CheckboxProps,
  SwitchProps,
  InputVariant,
  InputSize,
} from "./Input";

// 骨架屏组件
export {
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonAvatar,
  SkeletonTable,
  SkeletonList,
  SkeletonPlaybookRun,
  SkeletonChart,
  SkeletonStatGrid,
  SkeletonPage,
} from "./Skeleton";

// 涟漪按钮组件
export { RippleButton } from "./RippleButton";

// 加载指示器组件
export { LoadingSpinner, FullScreenLoader, SkeletonLoader } from "./LoadingSpinner";

// 标签切换过渡组件
export { TabTransition } from "./TabTransition";
