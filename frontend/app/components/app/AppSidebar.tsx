"use client";

import { CreditCard, FileText, Sparkle, Storefront, Trash, UserCircle } from "@phosphor-icons/react";

import type { ActiveMode, SidePanel } from "../../lib/types";

type AppSidebarProps = {
  activeMode: ActiveMode;
  sidePanel: SidePanel;
  onModeChange: (mode: ActiveMode) => void;
  onPanelChange: (panel: SidePanel) => void;
  onClearChat: () => void;
};

export default function AppSidebar({
  activeMode,
  sidePanel,
  onModeChange,
  onPanelChange,
  onClearChat,
}: AppSidebarProps) {
  const items = [
    activeMode === "market"
      ? {
          key: "nira",
          label: "NiRa AI",
          icon: Sparkle,
          onClick: () => onModeChange("nira"),
          active: false,
        }
      : {
          key: "market",
          label: "Market results",
          icon: Storefront,
          onClick: () => onModeChange("market"),
          active: false,
        },
    {
      key: "reports",
      label: "Reports history",
      icon: FileText,
      onClick: () => onPanelChange("reports"),
      active: sidePanel === "reports",
    },
    {
      key: "subscription",
      label: "Subscription",
      icon: CreditCard,
      onClick: () => onPanelChange("subscription"),
      active: sidePanel === "subscription",
    },
    {
      key: "profile",
      label: "Session",
      icon: UserCircle,
      onClick: () => onPanelChange("profile"),
      active: sidePanel === "profile",
    },
    { key: "clear", label: "Clear chat", icon: Trash, onClick: onClearChat, active: false },
  ];

  return (
    <nav className="more-options-menu sidebar" aria-label="Workspace">
      <div className="sidebar-brand">NiRaConChem AI</div>
      <div className="sidebar-spacer" />
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <button
            aria-current={item.active ? "page" : undefined}
            className={`menu-item${item.active ? " is-active" : ""}`}
            key={item.key}
            onClick={item.onClick}
            type="button"
          >
            <Icon size={17} weight="duotone" aria-hidden="true" />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
