"use client";

import Image from "next/image";
import { CreditCard, DownloadSimple, FilePdf, Paperclip, Plus, SignOut } from "@phosphor-icons/react";

type WorkspaceRailProps = {
  onHome: () => void;
  onNewChat: () => void;
  onSubscription: () => void;
  subscriptionActive: boolean;
  canDownloadReport: boolean;
  isDownloading: boolean;
  onDownloadReport: () => void;
  canInstall: boolean;
  onInstall: () => void;
};

/** The narrow column of tools on the left: things you do, not places you go. */
export default function WorkspaceRail({
  onHome,
  onNewChat,
  onSubscription,
  subscriptionActive,
  canDownloadReport,
  isDownloading,
  onDownloadReport,
  canInstall,
  onInstall,
}: WorkspaceRailProps) {
  return (
    <nav aria-label="Tools" className="ws-rail">
      <button aria-label="NiRaConChem AI — back to the home page" className="ws-logo" onClick={onHome} type="button">
        <Image alt="" height={30} src="/icons/brand-mark.png" width={30} />
      </button>

      <div className="ws-rail-tools">
        <button aria-label="New chat" className="ws-rail-btn" onClick={onNewChat} title="New chat" type="button">
          <Plus aria-hidden="true" size={19} weight="bold" />
        </button>
        <label className="ws-rail-btn" htmlFor="ws-file" title="Attach a project file">
          <Paperclip aria-hidden="true" size={19} weight="duotone" />
          <span className="sr-only">Attach a project file</span>
        </label>
        <button
          aria-label={isDownloading ? "Preparing the PDF report" : "Download the PDF report"}
          className="ws-rail-btn"
          disabled={!canDownloadReport || isDownloading}
          onClick={onDownloadReport}
          title={canDownloadReport ? "Download the PDF report" : "A report is offered once NiRa has enough project detail"}
          type="button"
        >
          <FilePdf aria-hidden="true" size={19} weight="duotone" />
        </button>
        <button
          aria-label="Subscription"
          aria-pressed={subscriptionActive}
          className="ws-rail-btn"
          onClick={onSubscription}
          title="Subscription"
          type="button"
        >
          <CreditCard aria-hidden="true" size={19} weight="duotone" />
        </button>
      </div>

      <div className="ws-rail-foot">
        {canInstall ? (
          <button aria-label="Install the app" className="ws-rail-btn" onClick={onInstall} title="Install the app" type="button">
            <DownloadSimple aria-hidden="true" size={19} weight="bold" />
          </button>
        ) : null}
        <button aria-label="Back to the home page" className="ws-rail-btn" onClick={onHome} title="Back to the home page" type="button">
          <SignOut aria-hidden="true" size={19} weight="duotone" />
        </button>
      </div>
    </nav>
  );
}
