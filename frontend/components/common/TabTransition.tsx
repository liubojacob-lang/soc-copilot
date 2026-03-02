"use client";

import { ReactNode } from "react";

interface TabTransitionProps {
  activeKey: string;
  children: { key: string; content: ReactNode }[];
  className?: string;
}

function TabTransition({ activeKey, children, className = "" }: TabTransitionProps) {
  const activeChild = children.find(child => child.key === activeKey);

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <div
        key={activeKey}
        className="animate-scale-in"
      >
        {activeChild?.content}
      </div>
    </div>
  );
}

export { TabTransition };
