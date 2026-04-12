import React from "react";
import { createRoot } from "react-dom/client";
import ReactDOM from "react-dom";
import { AiAssistantWidget } from "../../../ai-assistant-release/ai-assistant-widget/src";

const App = () => (
  <div style={{ padding: 16 }}>
    <h2>AI Assistant Demo</h2>
    {/* 简单示例：指向本地后端 API */}
    <AiAssistantWidget apiBaseUrl="http://localhost:8000" />
  </div>
);

createRoot(document.getElementById("root")).render(<App />);
