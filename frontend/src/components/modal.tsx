"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";

import { Icon } from "@/components/icon";

export function Modal({ title, children, onClose, busy = false, variant = "default" }: {
  title: string; children: ReactNode; onClose: () => void; busy?: boolean; variant?: "default" | "form";
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    element?.querySelector<HTMLElement>("[data-autofocus]")?.focus();
    return () => element?.close();
  }, []);

  return (
    <dialog ref={dialog} className={`modal${variant === "form" ? " modal-form" : ""}`} aria-labelledby={titleId} onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }} onClick={(event) => { if (event.target === event.currentTarget && !busy) { const rect = event.currentTarget.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose(); } }}>
      <div className="modal-heading"><h2 id={titleId}>{title}</h2><button className="icon-button" onClick={onClose} disabled={busy} aria-label="Fechar modal"><Icon name="close" /></button></div>
      <div className="modal-content">{children}</div>
    </dialog>
  );
}
