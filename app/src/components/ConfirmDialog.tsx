// Confirm dialog — wraps native <dialog> with showModal()/close().
// Spec §1: must use <dialog>, NOT <div role="dialog">.

import { useEffect, useRef } from "react";
import styles from "./ConfirmDialog.module.css";

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  body: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Variant for the confirm button (warn for mainnet boundary, etc.) */
  variant?: "default" | "warn";
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  // Native ESC closes the dialog; treat as cancel.
  const handleClose = () => {
    if (open) onCancel();
  };

  return (
    <dialog ref={dialogRef} className={styles.dialog} onClose={handleClose}>
      <h2 className={styles.title}>{title}</h2>
      <div className={styles.body}>{body}</div>
      <div className={styles.actions}>
        <button type="button" onClick={onCancel}>
          {cancelLabel}
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className={variant === "warn" ? styles.warn : styles.confirm}
        >
          {confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
