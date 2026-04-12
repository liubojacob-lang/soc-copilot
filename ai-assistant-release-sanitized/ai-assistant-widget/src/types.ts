export type WidgetProps = {
  apiBaseUrl: string;
  modelId?: string;
  autoScroll?: boolean;
  onError?: (err: string) => void;
  theme?: "light" | "dark" | object;
  onSubmit?: (payload: { message: string; model_id?: string }) => void;
  onResponse?: (response: any) => void;
};
