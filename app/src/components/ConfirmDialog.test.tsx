import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDialog } from "./ConfirmDialog";

describe("ConfirmDialog", () => {
  it("renders title and body", () => {
    render(
      <ConfirmDialog
        open={true}
        title="Confirm switch"
        body="Are you sure?"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(screen.getByText("Confirm switch")).toBeTruthy();
    expect(screen.getByText("Are you sure?")).toBeTruthy();
  });

  it("uses native <dialog> element (spec §1)", () => {
    const { container } = render(
      <ConfirmDialog open={true} title="t" body="b" onConfirm={() => {}} onCancel={() => {}} />,
    );
    const dialog = container.querySelector("dialog");
    expect(dialog).not.toBeNull();
  });

  it("invokes onConfirm when confirm button clicked", () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        open={true}
        title="t"
        body="b"
        confirmLabel="Yes"
        onConfirm={onConfirm}
        onCancel={() => {}}
      />,
    );
    fireEvent.click(screen.getByText("Yes"));
    expect(onConfirm).toHaveBeenCalled();
  });

  it("invokes onCancel when cancel button clicked", () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        open={true}
        title="t"
        body="b"
        cancelLabel="No"
        onConfirm={() => {}}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByText("No"));
    expect(onCancel).toHaveBeenCalled();
  });
});
